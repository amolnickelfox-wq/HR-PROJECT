import threading
from datetime import datetime, timezone

from backend.app.state import interview_store, _scheduler, _SCHEDULER_OK
from backend.app.database import _save_interview, _sync_candidate_interview
from backend.services.interviewer import start_twilio_call


def _trigger_callback_call(interview_id: str):
    data = interview_store.get(interview_id)
    if not data:
        print(f"[Callback] interview_id {interview_id} not found in store — skipping")
        return
    is_callback_pending = (
        data.get("status") == "callback_scheduled"
        or (data.get("status") == "calling" and data.get("callback_time_raw"))
    )
    if not is_callback_pending:
        print(f"[Callback] {interview_id} already handled (status={data.get('status')}) — skipping auto-dial")
        return

    # Re-integrate into pipeline active map so _on_pipeline_call_ended can handle the outcome
    pipeline_id = data.get("pipeline_id")
    if pipeline_id:
        try:
            from backend.app.state import pipeline_store
            from backend.api.routes.pipeline import _get_lock
            from backend.app.database import _save_pipeline
            p = pipeline_store.get(pipeline_id)
            if p:
                lock = _get_lock(pipeline_id)
                with lock:
                    candidate_name = data.get("candidate_name", "")
                    for i, c in enumerate(p.get("skipped", [])):
                        if c.get("skip_reason") == "callback" and c.get("name") == candidate_name:
                            candidate = p["skipped"].pop(i)
                            p["active"][interview_id] = candidate
                            if p["status"] == "completed":
                                p["status"] = "running"
                            _save_pipeline(pipeline_id, p)
                            print(f"[Callback] Re-activated {candidate_name} in pipeline {pipeline_id}")
                            break
        except Exception as e:
            print(f"[Callback] Pipeline re-integration failed for {interview_id}: {e}")

    existing_log = data.get("call_log", [])
    data.update({
        "status":                "calling",
        "consent_status":        "pending",
        "consent_raw":           None,
        "consent_re_asked":      False,
        "callback_time_raw":     None,
        "callback_scheduled_at": None,
        "recordings":            {},
        "transcriptions":        {},
        "repeat_counts":         {},
        "transcript":            None,
        "score_result":          None,
        "fail_reason":           None,
        "_processing_started":   False,
        "call_log":              existing_log + [{
            "attempt":    len(existing_log) + 1,
            "started_at": datetime.now().isoformat(),
            "status":     "calling",
            "is_callback": True,
        }],
    })
    _save_interview(interview_id, data)
    _sync_candidate_interview(interview_id, data)
    try:
        start_twilio_call(data["phone"], interview_id)
        print(f"[Callback] Re-calling {data['phone']} for {interview_id}")
    except Exception as e:
        data["status"] = "failed"
        _save_interview(interview_id, data)
        print(f"[Callback] Failed to re-call: {e}")


def _reschedule_pending_callbacks():
    if not _SCHEDULER_OK:
        return
    count = 0
    for iid, iv in interview_store.items():
        if iv.get("status") != "callback_scheduled":
            continue
        scheduled = iv.get("callback_scheduled_at")
        if not scheduled:
            continue
        try:
            run_at = datetime.fromisoformat(scheduled)
        except Exception:
            continue
        now = datetime.now(timezone.utc) if run_at.tzinfo else datetime.now()
        if run_at <= now:
            # Pre-update to 'calling' in DB before the thread starts — prevents re-fire
            # if the server restarts before the thread gets to run _trigger_callback_call.
            iv["status"] = "calling"
            iv["callback_scheduled_at"] = None
            _save_interview(iid, iv)
            _sync_candidate_interview(iid, iv)
            threading.Thread(target=_trigger_callback_call, args=(iid,), daemon=True).start()
        else:
            _scheduler.add_job(
                _trigger_callback_call, "date",
                run_date=run_at, args=[iid],
                id=f"callback_{iid}", replace_existing=True,
                misfire_grace_time=3600,
            )
            count += 1
    if count:
        print(f"[DB] Re-scheduled {count} pending callback(s) from DB")
