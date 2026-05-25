import os
import json
from datetime import datetime
from sqlalchemy import create_engine, text as _sql

_db_engine = None


def _init_db():
    global _db_engine
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("[DB] DATABASE_URL not set — running without persistence")
        return
    for old, new in [("postgresql://", "postgresql+psycopg://"), ("postgres://", "postgresql+psycopg://")]:
        if db_url.startswith(old):
            db_url = new + db_url[len(old):]
            break
    try:
        _db_engine = create_engine(db_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
        with _db_engine.connect() as conn:
            conn.execute(_sql("""
                CREATE TABLE IF NOT EXISTS job_openings (
                    id         TEXT        PRIMARY KEY,
                    title      TEXT        NOT NULL,
                    jd_text    TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            conn.execute(_sql("""
                CREATE TABLE IF NOT EXISTS interviews (
                    id                    TEXT        PRIMARY KEY,
                    opening_id            TEXT        REFERENCES job_openings(id) ON DELETE SET NULL,
                    status                TEXT        NOT NULL DEFAULT 'calling',
                    consent_status        TEXT        NOT NULL DEFAULT 'pending',
                    consent_raw           TEXT,
                    consent_re_asked      BOOLEAN     NOT NULL DEFAULT FALSE,
                    candidate_name        TEXT,
                    phone                 TEXT,
                    job_title             TEXT,
                    jd_text               TEXT,
                    twilio_call_sid       TEXT,
                    transcript            TEXT,
                    fail_reason           TEXT,
                    processing_step       TEXT,
                    callback_time_raw     TEXT,
                    callback_scheduled_at TIMESTAMPTZ,
                    questions             JSONB       NOT NULL DEFAULT '[]',
                    recordings            JSONB       NOT NULL DEFAULT '{}',
                    transcriptions        JSONB       NOT NULL DEFAULT '{}',
                    repeat_counts         JSONB       NOT NULL DEFAULT '{}',
                    score_result          JSONB,
                    call_log              JSONB       NOT NULL DEFAULT '[]',
                    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            # Add opening_id to existing DBs that predate this column
            conn.execute(_sql("ALTER TABLE interviews ADD COLUMN IF NOT EXISTS opening_id TEXT REFERENCES job_openings(id) ON DELETE SET NULL"))
            conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_iv_status    ON interviews(status)"))
            conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_iv_phone     ON interviews(phone)"))
            conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_iv_opening   ON interviews(opening_id)"))
            conn.execute(_sql("""
                CREATE INDEX IF NOT EXISTS idx_iv_callback
                ON interviews(callback_scheduled_at) WHERE status = 'callback_scheduled'
            """))
            conn.execute(_sql("""
                CREATE TABLE IF NOT EXISTS transcript_entries (
                    id             SERIAL      PRIMARY KEY,
                    interview_id   TEXT        NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
                    question_index INTEGER     NOT NULL,
                    question_text  TEXT        NOT NULL,
                    answer_text    TEXT,
                    recording_url  TEXT,
                    repeat_count   INTEGER     NOT NULL DEFAULT 0,
                    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (interview_id, question_index)
                )
            """))
            conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_te_iv ON transcript_entries(interview_id)"))
            conn.execute(_sql("""
                CREATE TABLE IF NOT EXISTS batches (
                    id         TEXT        PRIMARY KEY,
                    opening_id TEXT        REFERENCES job_openings(id) ON DELETE SET NULL,
                    status     TEXT        NOT NULL DEFAULT 'processing',
                    jd_text    TEXT,
                    job_title  TEXT,
                    total      INTEGER     NOT NULL DEFAULT 0,
                    completed  INTEGER     NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            # Add opening_id to existing DBs that predate this column
            conn.execute(_sql("ALTER TABLE batches ADD COLUMN IF NOT EXISTS opening_id TEXT REFERENCES job_openings(id) ON DELETE SET NULL"))
            conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_batches_status  ON batches(status)"))
            conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_batches_opening ON batches(opening_id)"))
            conn.execute(_sql("""
                CREATE TABLE IF NOT EXISTS batch_candidates (
                    id                    SERIAL      PRIMARY KEY,
                    batch_id              TEXT        NOT NULL REFERENCES batches(id)    ON DELETE CASCADE,
                    interview_id          TEXT                 REFERENCES interviews(id) ON DELETE SET NULL,
                    file_name             TEXT        NOT NULL,
                    name                  TEXT,
                    email                 TEXT,
                    phone                 TEXT,
                    resume_score          SMALLINT,
                    filter_status         TEXT        NOT NULL DEFAULT 'pending',
                    interview_status      TEXT        NOT NULL DEFAULT 'pending',
                    interview_score       SMALLINT,
                    combined_score        SMALLINT,
                    callback_scheduled_at TIMESTAMPTZ,
                    resume_text           TEXT,
                    analyze_result        JSONB,
                    score_result          JSONB,
                    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (batch_id, file_name)
                )
            """))
            conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_bc_batch      ON batch_candidates(batch_id)"))
            conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_bc_interview  ON batch_candidates(interview_id)"))
            conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_bc_filter     ON batch_candidates(filter_status)"))
            conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_bc_iv_status  ON batch_candidates(interview_status)"))
            conn.commit()
        print("[DB] PostgreSQL connected — 5 tables ready")
    except Exception as e:
        print(f"[DB] Connection failed: {e} — running without persistence")
        _db_engine = None


def _cb_ts(iso_str):
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str)
    except Exception:
        return None


def _save_opening(oid: str, data: dict):
    if not _db_engine:
        return
    try:
        with _db_engine.connect() as conn:
            conn.execute(_sql("""
                INSERT INTO job_openings (id, title, jd_text, created_at)
                VALUES (:id, :title, :jd_text, COALESCE(:created_at, NOW()))
                ON CONFLICT (id) DO UPDATE SET
                    title   = EXCLUDED.title,
                    jd_text = EXCLUDED.jd_text
            """), {
                "id":         oid,
                "title":      data.get("title", ""),
                "jd_text":    data.get("jd", ""),
                "created_at": _cb_ts(data.get("createdAt")),
            })
            conn.commit()
    except Exception as e:
        print(f"[DB] _save_opening failed for {oid}: {e}")


def _delete_opening(oid: str):
    if not _db_engine:
        return
    try:
        with _db_engine.connect() as conn:
            conn.execute(_sql("DELETE FROM job_openings WHERE id = :id"), {"id": oid})
            conn.commit()
    except Exception as e:
        print(f"[DB] _delete_opening failed for {oid}: {e}")


def _save_interview(iid: str, data: dict):
    if not _db_engine:
        return
    try:
        with _db_engine.connect() as conn:
            conn.execute(_sql("""
                INSERT INTO interviews (
                    id, opening_id, status, consent_status, consent_raw, consent_re_asked,
                    candidate_name, phone, job_title, jd_text, twilio_call_sid,
                    transcript, fail_reason, processing_step, callback_time_raw,
                    callback_scheduled_at, questions, recordings, transcriptions,
                    repeat_counts, score_result, call_log, updated_at
                ) VALUES (
                    :id, (SELECT id FROM job_openings WHERE id = :opening_id), :status, :consent_status, :consent_raw, :consent_re_asked,
                    :candidate_name, :phone, :job_title, :jd_text, :twilio_call_sid,
                    :transcript, :fail_reason, :processing_step, :callback_time_raw,
                    :callback_scheduled_at, CAST(:questions AS jsonb), CAST(:recordings AS jsonb),
                    CAST(:transcriptions AS jsonb), CAST(:repeat_counts AS jsonb), CAST(:score_result AS jsonb),
                    CAST(:call_log AS jsonb), NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                    opening_id            = EXCLUDED.opening_id,
                    status                = EXCLUDED.status,
                    consent_status        = EXCLUDED.consent_status,
                    consent_raw           = EXCLUDED.consent_raw,
                    consent_re_asked      = EXCLUDED.consent_re_asked,
                    candidate_name        = EXCLUDED.candidate_name,
                    phone                 = EXCLUDED.phone,
                    job_title             = EXCLUDED.job_title,
                    jd_text               = EXCLUDED.jd_text,
                    twilio_call_sid       = EXCLUDED.twilio_call_sid,
                    transcript            = EXCLUDED.transcript,
                    fail_reason           = EXCLUDED.fail_reason,
                    processing_step       = EXCLUDED.processing_step,
                    callback_time_raw     = EXCLUDED.callback_time_raw,
                    callback_scheduled_at = EXCLUDED.callback_scheduled_at,
                    questions             = EXCLUDED.questions,
                    recordings            = EXCLUDED.recordings,
                    transcriptions        = EXCLUDED.transcriptions,
                    repeat_counts         = EXCLUDED.repeat_counts,
                    score_result          = EXCLUDED.score_result,
                    call_log              = EXCLUDED.call_log,
                    updated_at            = NOW()
            """), {
                "id":                    iid,
                "opening_id":            data.get("opening_id"),
                "status":                data.get("status", "calling"),
                "consent_status":        data.get("consent_status", "pending"),
                "consent_raw":           data.get("consent_raw"),
                "consent_re_asked":      data.get("consent_re_asked", False),
                "candidate_name":        data.get("candidate_name"),
                "phone":                 data.get("phone"),
                "job_title":             data.get("job_title"),
                "jd_text":               data.get("jd_text"),
                "twilio_call_sid":       data.get("twilio_call_sid"),
                "transcript":            data.get("transcript"),
                "fail_reason":           data.get("fail_reason"),
                "processing_step":       data.get("processing_step"),
                "callback_time_raw":     data.get("callback_time_raw"),
                "callback_scheduled_at": _cb_ts(data.get("callback_scheduled_at")),
                "questions":             json.dumps(data.get("questions", [])),
                "recordings":            json.dumps({str(k): v for k, v in data.get("recordings", {}).items()}),
                "transcriptions":        json.dumps({str(k): v for k, v in data.get("transcriptions", {}).items()}),
                "repeat_counts":         json.dumps({str(k): v for k, v in data.get("repeat_counts", {}).items()}),
                "score_result":          json.dumps(data["score_result"]) if data.get("score_result") else None,
                "call_log":              json.dumps(data.get("call_log", [])),
            })
            conn.commit()
    except Exception as e:
        print(f"[DB] _save_interview failed for {iid}: {e}")


def _save_transcript_entries(iid: str, data: dict):
    if not _db_engine:
        return
    questions      = data.get("questions", [])
    transcriptions = data.get("transcriptions", {})
    recordings     = data.get("recordings", {})
    repeat_counts  = data.get("repeat_counts", {})
    if not questions:
        return
    try:
        with _db_engine.connect() as conn:
            for i, q_text in enumerate(questions):
                answer = transcriptions.get(i) or transcriptions.get(str(i))
                rec    = recordings.get(i) or recordings.get(str(i))
                rc     = repeat_counts.get(i, 0) or repeat_counts.get(str(i), 0)
                conn.execute(_sql("""
                    INSERT INTO transcript_entries
                        (interview_id, question_index, question_text, answer_text, recording_url, repeat_count)
                    VALUES (:iid, :idx, :q, :a, :rec, :rc)
                    ON CONFLICT (interview_id, question_index) DO UPDATE SET
                        question_text = EXCLUDED.question_text,
                        answer_text   = EXCLUDED.answer_text,
                        recording_url = EXCLUDED.recording_url,
                        repeat_count  = EXCLUDED.repeat_count
                """), {"iid": iid, "idx": i, "q": q_text, "a": answer, "rec": rec, "rc": rc or 0})
            conn.commit()
    except Exception as e:
        print(f"[DB] _save_transcript_entries failed for {iid}: {e}")


def _save_batch(bid: str, data: dict):
    if not _db_engine:
        return
    try:
        with _db_engine.connect() as conn:
            conn.execute(_sql("""
                INSERT INTO batches (id, opening_id, status, jd_text, job_title, total, completed, updated_at)
                VALUES (:id, (SELECT id FROM job_openings WHERE id = :opening_id), :status, :jd_text, :job_title, :total, :completed, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    opening_id = EXCLUDED.opening_id,
                    status     = EXCLUDED.status,
                    jd_text    = EXCLUDED.jd_text,
                    job_title  = EXCLUDED.job_title,
                    total      = EXCLUDED.total,
                    completed  = EXCLUDED.completed,
                    updated_at = NOW()
            """), {
                "id":         bid,
                "opening_id": data.get("opening_id"),
                "status":     data.get("status", "processing"),
                "jd_text":    data.get("jd_text"),
                "job_title":  data.get("job_title"),
                "total":      data.get("total", 0),
                "completed":  data.get("completed", 0),
            })
            for c in data.get("candidates", []):
                conn.execute(_sql("""
                    INSERT INTO batch_candidates (
                        batch_id, interview_id, file_name, name, email, phone,
                        resume_score, filter_status, interview_status, interview_score,
                        combined_score, callback_scheduled_at, resume_text,
                        analyze_result, score_result, updated_at
                    ) VALUES (
                        :batch_id, (SELECT id FROM interviews WHERE id = :interview_id), :file_name, :name, :email, :phone,
                        :resume_score, :filter_status, :interview_status, :interview_score,
                        :combined_score, :callback_scheduled_at, :resume_text,
                        CAST(:analyze_result AS jsonb), CAST(:score_result AS jsonb), NOW()
                    )
                    ON CONFLICT (batch_id, file_name) DO UPDATE SET
                        interview_id          = EXCLUDED.interview_id,
                        name                  = EXCLUDED.name,
                        email                 = EXCLUDED.email,
                        phone                 = EXCLUDED.phone,
                        resume_score          = EXCLUDED.resume_score,
                        filter_status         = EXCLUDED.filter_status,
                        interview_status      = EXCLUDED.interview_status,
                        interview_score       = EXCLUDED.interview_score,
                        combined_score        = EXCLUDED.combined_score,
                        callback_scheduled_at = EXCLUDED.callback_scheduled_at,
                        resume_text           = EXCLUDED.resume_text,
                        analyze_result        = EXCLUDED.analyze_result,
                        score_result          = EXCLUDED.score_result,
                        updated_at            = NOW()
                """), {
                    "batch_id":              bid,
                    "interview_id":          c.get("interview_id"),
                    "file_name":             c.get("file_name"),
                    "name":                  c.get("name"),
                    "email":                 c.get("email"),
                    "phone":                 c.get("phone"),
                    "resume_score":          c.get("resume_score"),
                    "filter_status":         c.get("filter_status", "pending"),
                    "interview_status":      c.get("interview_status", "pending"),
                    "interview_score":       c.get("interview_score"),
                    "combined_score":        c.get("combined_score"),
                    "callback_scheduled_at": _cb_ts(c.get("callback_scheduled_at")),
                    "resume_text":           c.get("resume_text"),
                    "analyze_result":        json.dumps(c["analyze_result"]) if c.get("analyze_result") else None,
                    "score_result":          json.dumps(c["score_result"])    if c.get("score_result")    else None,
                })
            conn.commit()
    except Exception as e:
        print(f"[DB] _save_batch failed for {bid}: {e}")


def load_stores() -> tuple[dict, dict, dict]:
    if not _db_engine:
        return {}, {}, {}

    def _int_keys(d):
        return {int(k): v for k, v in d.items()} if d else {}

    ivs = {}
    batches = {}
    try:
        with _db_engine.connect() as conn:
            openings = {}
            for orow in conn.execute(_sql("SELECT * FROM job_openings ORDER BY created_at")).mappings():
                ca = orow["created_at"]
                openings[orow["id"]] = {
                    "id":        orow["id"],
                    "title":     orow["title"],
                    "jd":        orow["jd_text"] or "",
                    "createdAt": ca.date().isoformat() if ca else "",
                    "stats":     {"total": 0, "qualified": 0, "done": 0},
                    "batchIds":  [],
                    "candidates": [],
                }
            for row in conn.execute(_sql("SELECT * FROM interviews ORDER BY created_at")).mappings():
                cb = row["callback_scheduled_at"]
                ivs[row["id"]] = {
                    "interview_id":          row["id"],
                    "opening_id":            row["opening_id"],
                    "status":                row["status"],
                    "consent_status":        row["consent_status"],
                    "consent_raw":           row["consent_raw"],
                    "consent_re_asked":      row["consent_re_asked"],
                    "candidate_name":        row["candidate_name"],
                    "phone":                 row["phone"],
                    "job_title":             row["job_title"],
                    "jd_text":               row["jd_text"],
                    "twilio_call_sid":       row["twilio_call_sid"],
                    "transcript":            row["transcript"],
                    "fail_reason":           row["fail_reason"],
                    "processing_step":       row["processing_step"],
                    "callback_time_raw":     row["callback_time_raw"],
                    "callback_scheduled_at": cb.isoformat() if cb else None,
                    "questions":             row["questions"] or [],
                    "recordings":            _int_keys(row["recordings"]),
                    "transcriptions":        _int_keys(row["transcriptions"]),
                    "repeat_counts":         _int_keys(row["repeat_counts"]),
                    "score_result":          row["score_result"],
                    "call_log":              row["call_log"] or [],
                }
            for brow in conn.execute(_sql("SELECT * FROM batches ORDER BY created_at")).mappings():
                bid = brow["id"]
                candidates = []
                for crow in conn.execute(
                    _sql("SELECT * FROM batch_candidates WHERE batch_id = :b ORDER BY id"), {"b": bid}
                ).mappings():
                    cb = crow["callback_scheduled_at"]
                    candidates.append({
                        "file_name":             crow["file_name"],
                        "resume_text":           crow["resume_text"],
                        "name":                  crow["name"],
                        "email":                 crow["email"],
                        "phone":                 crow["phone"],
                        "resume_score":          crow["resume_score"],
                        "analyze_result":        crow["analyze_result"],
                        "filter_status":         crow["filter_status"],
                        "interview_id":          crow["interview_id"],
                        "interview_status":      crow["interview_status"],
                        "interview_score":       crow["interview_score"],
                        "combined_score":        crow["combined_score"],
                        "callback_scheduled_at": cb.isoformat() if cb else None,
                        "score_result":          crow["score_result"],
                    })
                batches[bid] = {
                    "batch_id":   bid,
                    "opening_id": brow["opening_id"],
                    "status":     brow["status"],
                    "jd_text":    brow["jd_text"],
                    "job_title":  brow["job_title"],
                    "total":      brow["total"],
                    "completed":  brow["completed"],
                    "candidates": candidates,
                }
        print(f"[DB] Loaded {len(openings)} openings, {len(ivs)} interviews, {len(batches)} batches from PostgreSQL")
    except Exception as e:
        print(f"[DB] load_stores failed: {e}")
        openings = {}
    return ivs, batches, openings
