import re
from backend.app.database import _db_engine, _sql


def _get_old_recordings() -> list[dict]:
    if not _db_engine:
        return []
    with _db_engine.connect() as conn:
        rows = conn.execute(_sql("""
            SELECT id, twilio_call_sid, recordings
            FROM interviews
            WHERE created_at < NOW() - INTERVAL '89 days'
              AND recordings IS NOT NULL
              AND recordings::text != '{}'
        """)).mappings().all()
    return [dict(r) for r in rows]


def _detect_provider(url: str) -> str:
    if not url:
        return "unknown"
    if "twilio" in url:
        return "twilio"
    if "plivo" in url:
        return "plivo"
    return "unknown"


def _extract_twilio_sid(url: str) -> str | None:
    match = re.search(r'/Recordings/([A-Z0-9]{34})', url)
    return match.group(1) if match else url.rstrip('/').split('/')[-1] or None


def _extract_plivo_uuid(url: str) -> str | None:
    match = re.search(r'/Recording/([^/.]+)', url)
    return match.group(1) if match else None


def _delete_recording(url: str) -> bool:
    from backend.services.interviewer import twilio_client, plivo_client
    provider = _detect_provider(url)
    try:
        if provider == "twilio" and twilio_client:
            sid = _extract_twilio_sid(url)
            if sid:
                twilio_client.recordings(sid).delete()
                return True
        elif provider == "plivo" and plivo_client:
            uuid = _extract_plivo_uuid(url)
            if uuid:
                plivo_client.recordings.delete(uuid)
                return True
    except Exception as e:
        err = str(e).lower()
        if "404" not in err and "not found" not in err:
            print(f"[Cleanup] Warning: could not delete recording {url}: {e}")
    return False


def cleanup_old_recordings():
    if not _db_engine:
        return

    interviews = _get_old_recordings()
    if not interviews:
        print("[Cleanup] No recordings older than 90 days found")
        return

    deleted_count = 0
    cleaned_ids = []

    for iv in interviews:
        iid = str(iv["id"])
        call_sid = iv.get("twilio_call_sid")
        recordings = iv.get("recordings") or {}

        # Track whether every per-question recording actually got deleted. If any deletion
        # fails (provider unconfigured, non-404 API error), we must NOT clear the DB pointer,
        # or the recording is orphaned at the provider forever with no reference to retry.
        all_deleted = True
        for url in recordings.values():
            if not url:
                continue
            if _delete_recording(url):
                deleted_count += 1
            else:
                all_deleted = False

        # Delete full call recording stored by call_sid/call_uuid (Twilio record=True,
        # Plivo calls.record() started from /plivo/start). Interviews don't record which
        # provider placed the call, so try both lookups — the wrong one just returns nothing.
        if call_sid:
            try:
                from backend.services.interviewer import twilio_client
                if twilio_client:
                    for rec in twilio_client.recordings.list(call_sid=call_sid):
                        try:
                            rec.delete()
                            deleted_count += 1
                        except Exception:
                            pass
            except Exception as e:
                print(f"[Cleanup] Twilio full call recording lookup failed for {iid}: {e}")
            try:
                from backend.services.interviewer import plivo_client
                if plivo_client:
                    for rec in plivo_client.recordings.list(call_uuid=call_sid):
                        try:
                            plivo_client.recordings.delete(rec.recording_id)
                            deleted_count += 1
                        except Exception:
                            pass
            except Exception as e:
                print(f"[Cleanup] Plivo full call recording lookup failed for {iid}: {e}")

        # Only clear the DB pointers if every per-question recording deletion succeeded.
        if all_deleted:
            cleaned_ids.append(iid)
        else:
            print(f"[Cleanup] Kept DB recording refs for {iid} — some deletions failed, will retry next run")

    if cleaned_ids:
        try:
            with _db_engine.connect() as conn:
                conn.execute(_sql("""
                    UPDATE interviews
                    SET recordings = '{}', updated_at = NOW()
                    WHERE id = ANY(:ids)
                """), {"ids": cleaned_ids})
                conn.execute(_sql("""
                    UPDATE transcript_entries
                    SET recording_url = NULL
                    WHERE interview_id = ANY(:ids)
                """), {"ids": cleaned_ids})
                conn.commit()
        except Exception as e:
            print(f"[Cleanup] DB clear failed: {e}")
            return

    print(f"[Cleanup] Deleted {deleted_count} recording(s) from {len(cleaned_ids)} interview(s)")
