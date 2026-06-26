import backend.app.config  # noqa: F401 — loads .env before anything else

import os
from contextlib import asynccontextmanager

import httpx as _httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response as _Response

from backend.app.state import _scheduler, _SCHEDULER_OK
from backend.app.database import _init_db, load_stores, _load_pipelines, _save_pipeline, _get_interview_status_from_db, _save_interview, _sync_candidate_interview
from backend.app.state import interview_store, batch_store, opening_store, pipeline_store, opening_pipeline
from backend.app.callbacks import _reschedule_pending_callbacks

from backend.api.routes.health    import router as health_router
from backend.api.routes.resume    import router as resume_router
from backend.api.routes.interview import router as interview_router
from backend.api.routes.batch     import router as batch_router
from backend.api.routes.openings  import router as openings_router
from backend.api.routes.auth      import router as auth_router
from backend.api.routes.pipeline  import router as pipeline_router


def _cleanup_stuck_calls():
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(hours=2)
    count = 0
    pipeline_to_notify = []
    for iid, iv in list(interview_store.items()):
        if iv.get("status") not in ("calling", "in_progress", "processing"):
            continue
        call_log = iv.get("call_log", [])
        started  = call_log[0].get("started_at") if call_log else None
        try:
            if started and datetime.fromisoformat(started) < cutoff:
                iv["status"]      = "abandoned"
                iv["fail_reason"] = "Auto-resolved: call never completed (server was unreachable)"
                _save_interview(iid, iv)
                _sync_candidate_interview(iid, iv)
                if iv.get("pipeline_id"):
                    pipeline_to_notify.append(iid)
                count += 1
        except Exception:
            pass
    if pipeline_to_notify:
        try:
            from backend.api.routes.pipeline import _on_pipeline_call_ended
            for iid in pipeline_to_notify:
                _on_pipeline_call_ended(iid, "no_answer")
        except Exception as e:
            print(f"[Startup] Pipeline notification after stuck-call cleanup failed: {e}")
    if count:
        print(f"[Startup] Auto-resolved {count} stuck call(s) older than 2 hours")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if _SCHEDULER_OK:
        _scheduler.start()
        print("[Startup] APScheduler started — callback scheduling enabled")
    _init_db()
    from backend.app.database import _seed_super_admin
    sa_user = os.getenv("SUPER_ADMIN_USERNAME", "director")
    sa_pass = os.getenv("SUPER_ADMIN_PASSWORD", "changeme")
    _seed_super_admin(sa_user, sa_pass)
    print(f"[Startup] Super admin '{sa_user}' ready (seeded only if first run)")
    loaded_ivs, loaded_batches, loaded_openings = load_stores()
    interview_store.update(loaded_ivs)
    batch_store.update(loaded_batches)
    opening_store.update(loaded_openings)
    loaded_pipelines = _load_pipelines()
    pipeline_store.update(loaded_pipelines)
    for pid, p in loaded_pipelines.items():
        opening_pipeline[p["opening_id"]] = pid
        # Purge active entries whose Twilio calls ended during the downtime
        stale = []
        for iid, candidate in list(p["active"].items()):
            iv = interview_store.get(iid)
            status = iv.get("status") if iv else _get_interview_status_from_db(iid)
            if status in ("completed", "failed", "abandoned", "callback_scheduled",
                          "calling", "in_progress", "processing"):
                stale.append((iid, candidate, status))
        for iid, candidate, status in stale:
            p["active"].pop(iid, None)
            if status == "completed":
                p["completed"].append(candidate)
            elif status == "callback_scheduled":
                p["skipped"].append({**candidate, "skip_reason": "callback"})
            elif status in ("calling", "in_progress", "processing"):
                # Mark old interview failed so batch_candidates.interview_status is cleared
                # immediately — prevents permanent 'calling' if the next call also fails
                if iv:
                    iv["status"]      = "failed"
                    iv["fail_reason"] = "Auto-resolved on restart: server restarted mid-call"
                    _save_interview(iid, iv)
                    _sync_candidate_interview(iid, iv)
                # Server crashed mid-call — re-queue once (1 retry max, consistent with pipeline logic)
                if candidate.get("no_answer_count", 0) < 1:
                    candidate["no_answer_count"] = candidate.get("no_answer_count", 0) + 1
                    p["queue"].append(candidate)
                    print(f"[Startup] Re-queued {candidate.get('name')} after crash (no_answer #{candidate['no_answer_count']})")
                else:
                    p["skipped"].append({**candidate, "skip_reason": "no_answer_twice"})
            else:
                p["skipped"].append({**candidate, "skip_reason": status})
        if stale:
            _save_pipeline(pid, p)
            print(f"[Startup] Cleared {len(stale)} stale active entries from pipeline {pid}")
    if loaded_pipelines:
        print(f"[Startup] Restored {len(loaded_pipelines)} active pipeline(s) from DB")

    # Clear stale calling/in_progress records directly in DB.
    # pipeline_id is not persisted to the interviews table, so we can't filter by it.
    # Instead: any interview stuck as 'calling'/'in_progress' for > 5 minutes is definitively
    # stale (Twilio ring timeout is ~20s; full interview never exceeds 30 min).
    # Interviews legitimately active in a pipeline's active dict are excluded.
    _active_in_pipeline = {
        iid
        for p in pipeline_store.values()
        for iid in p.get("active", {})
    }
    try:
        from backend.app.database import _db_engine, _sql
        if _db_engine:
            with _db_engine.connect() as _conn:
                stale_rows = _conn.execute(_sql("""
                    SELECT id FROM interviews
                    WHERE status IN ('calling', 'in_progress')
                      AND updated_at < NOW() - INTERVAL '5 minutes'
                """)).mappings().all()
                stale_iids = [str(r["id"]) for r in stale_rows
                              if str(r["id"]) not in _active_in_pipeline]
                if stale_iids:
                    _conn.execute(_sql("""
                        UPDATE interviews
                        SET status     = 'failed',
                            fail_reason = 'Auto-resolved on startup: stale call',
                            updated_at  = NOW()
                        WHERE id = ANY(:ids)
                    """), {"ids": stale_iids})
                    _conn.execute(_sql("""
                        UPDATE batch_candidates
                        SET interview_status = 'failed',
                            updated_at       = NOW()
                        WHERE interview_id = ANY(:ids)
                    """), {"ids": stale_iids})
                    _conn.commit()
                    for iid in stale_iids:
                        if iid in interview_store:
                            interview_store[iid]["status"]      = "failed"
                            interview_store[iid]["fail_reason"] = "Auto-resolved on startup: stale call"
                    print(f"[Startup] Cleared {len(stale_iids)} stale calling/in_progress interview(s)")
    except Exception as _e:
        print(f"[Startup] Stale call DB cleanup failed: {_e}")

    _cleanup_stuck_calls()
    _reschedule_pending_callbacks()
    try:
        r = _httpx.get("http://localhost:4040/api/tunnels", timeout=2)
        tunnels = r.json().get("tunnels", [])
        https_url = next(
            (t["public_url"] for t in tunnels if t["public_url"].startswith("https")), None
        )
        if https_url:
            os.environ["BASE_URL"] = https_url
            print(f"[Startup] ngrok auto-detected → BASE_URL={https_url}")
        else:
            print(f"[Startup] ngrok running but no HTTPS tunnel. BASE_URL={os.getenv('BASE_URL', 'NOT SET')}")
    except Exception:
        print(f"[Startup] ngrok not detected. BASE_URL={os.getenv('BASE_URL', 'NOT SET')}")
    yield
    if _SCHEDULER_OK:
        _scheduler.shutdown(wait=False)


app = FastAPI(title="AI Recruitment Assistant", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_TWILIO_ERROR_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Response>'
    '<Say voice="Google.en-IN-Neural2-A">'
    "We're having a technical issue. We'll call you back shortly. Goodbye!"
    '</Say>'
    '<Hangup/>'
    '</Response>'
)

@app.exception_handler(Exception)
async def twilio_fallback_handler(request: Request, exc: Exception):
    """Return graceful TwiML on any unhandled exception in Twilio webhook routes."""
    if "/twilio/" in str(request.url.path):
        print(f"[TwiML] Unhandled error on {request.url.path}: {exc}")
        return _Response(content=_TWILIO_ERROR_XML, media_type="text/xml", status_code=200)
    raise exc

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(resume_router)
app.include_router(interview_router)
app.include_router(batch_router)
app.include_router(openings_router)
app.include_router(pipeline_router)
