import threading
from datetime import datetime

from backend.app.state import interview_store, _scheduler, _SCHEDULER_OK
from backend.app.database import _save_interview
from backend.services.interviewer import start_twilio_call


def _trigger_callback_call(interview_id: str):
    data = interview_store.get(interview_id)
    if not data:
        print(f"[Callback] interview_id {interview_id} not found in store — skipping")
        return
    if data.get("status") != "callback_scheduled":
        print(f"[Callback] {interview_id} already handled (status={data.get('status')}) — skipping auto-dial")
        return
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
        "call_log":              existing_log + [{
            "attempt":    len(existing_log) + 1,
            "started_at": datetime.now().isoformat(),
            "status":     "calling",
            "is_callback": True,
        }],
    })
    _save_interview(interview_id, data)
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
        if run_at <= datetime.now():
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
