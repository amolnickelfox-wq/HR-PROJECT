import os
from collections import defaultdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.state import opening_store
from backend.app.database import _save_opening, _delete_opening
from backend.services.interviewer import claude_client, CLAUDE_MODEL

router = APIRouter()


class OpeningCreate(BaseModel):
    id: str
    title: str
    jd: str = ''
    createdAt: str = ''
    jd_fields: dict | None = None


class OpeningUpdate(BaseModel):
    title: str | None = None
    jd: str | None = None


class JdGenerateRequest(BaseModel):
    job_title: str
    experience_level: str
    responsibilities: str
    skills: str
    good_to_have: str = ""
    preferred_qualifications: str = ""
    work_mode: str
    perks: str = ""


@router.post("/openings/generate-jd")
async def generate_jd(body: JdGenerateRequest):
    if not claude_client:
        raise HTTPException(500, "Claude API not configured.")
    good_to_have_section = (
        f"\n\nGood to Have Skills\n{body.good_to_have}"
        if body.good_to_have.strip() else ""
    )
    preferred_qual_section = (
        f"\n\nPreferred Qualifications\n{body.preferred_qualifications}"
        if body.preferred_qualifications.strip() else ""
    )
    perks_hint = body.perks.strip() or "mentorship, cross-domain projects, health insurance, learning budget"
    prompt = f"""Expand the following job details into a polished job description. Use EXACTLY these section headings in this order, and no others. Do not add any intro, summary, or "About the company" section.

Job Title: {body.job_title}
Experience Level: {body.experience_level}

Key Responsibilities
{body.responsibilities}

Required Technical Skills & Stack
{body.skills}{good_to_have_section}{preferred_qual_section}

Work Mode
{body.work_mode}

What We Offer
{perks_hint}

Instructions:
- Start with a "Role Summary" section: 2 sentences max. What the role is and what we need.
- Then include the remaining sections with headings word-for-word as shown above.
- Under "Key Responsibilities": 4-5 tight bullet points, action verbs only.
- Under "Required Technical Skills & Stack": bullet list of skills as-is; do not invent or expand.
- Under "Good to Have Skills" (include only if provided): bullet list as-is; do not invent or expand.
- Under "Preferred Qualifications" (include only if provided): 2-3 bullets max.
- Under "Work Mode": one short phrase, no full sentence needed.
- Under "What We Offer": 4-5 bullets; use hints provided, no padding.
- Total output under 250 words. Crisp, no filler phrases. Return only the job description, no preamble."""
    try:
        resp = claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return {"jd": resp.content[0].text.strip()}
    except Exception as e:
        raise HTTPException(500, f"JD generation failed: {e}")


@router.post("/openings", status_code=201)
async def create_opening(req: OpeningCreate):
    opening_store[req.id] = {
        "id":        req.id,
        "title":     req.title,
        "jd":        req.jd,
        "createdAt": req.createdAt,
        "jd_fields": req.jd_fields or {},
    }
    _save_opening(req.id, opening_store[req.id])
    return opening_store[req.id]


@router.get("/openings")
async def list_openings():
    return list(opening_store.values())


@router.get("/openings/full")
async def list_openings_full():
    """All openings with candidates — single DB round-trip for multi-user sync."""
    from backend.app.state import interview_store
    from backend.app.database import _db_engine, _sql
    openings_list = list(opening_store.values())
    if not openings_list or not _db_engine:
        return [{"candidates": [], **o} for o in openings_list]

    opening_ids = [o["id"] for o in openings_list]
    try:
        with _db_engine.connect() as conn:
            rows = conn.execute(_sql("""
                SELECT bc.batch_id, bc.single_id,
                       COALESCE(bc.opening_id, b.opening_id) AS opening_id,
                       bc.interview_id,
                       bc.file_name, bc.name, bc.email, bc.phone,
                       bc.resume_score, bc.filter_status, bc.interview_status,
                       bc.interview_score, bc.combined_score, bc.callback_scheduled_at,
                       bc.analyze_result, bc.score_result,
                       i.status        AS iv_status,
                       i.score_result  AS iv_score_result,
                       i.transcript, i.questions, i.fail_reason, i.call_log
                FROM batch_candidates bc
                LEFT JOIN batches b    ON b.id = bc.batch_id
                LEFT JOIN interviews i ON i.id = bc.interview_id
                WHERE COALESCE(bc.opening_id, b.opening_id) = ANY(:oids)
                ORDER BY COALESCE(bc.opening_id, b.opening_id),
                         bc.resume_score DESC NULLS LAST, bc.created_at ASC
            """), {"oids": opening_ids}).mappings().all()
    except Exception as e:
        print(f"[DB] list_openings_full failed: {e}")
        return [{"candidates": [], **o} for o in openings_list]

    cands_by_opening = defaultdict(list)
    for row in rows:
        c = dict(row)
        oid            = c.pop("opening_id", None)
        c["_batchId"]  = c.pop("batch_id", None)
        c["_singleId"] = c.pop("single_id", None)
        c["_type"]     = "single" if c["_singleId"] else "batch"

        iid             = c.get("interview_id")
        iv_status       = c.pop("iv_status", None)
        iv_score_result = c.pop("iv_score_result", None)

        iv = interview_store.get(iid) if iid else None
        if iv:
            c["interview_status"] = iv.get("status", c["interview_status"])
            if iv.get("score_result"):  c["score_result"] = iv["score_result"]
            if iv.get("transcript"):    c["transcript"]   = iv["transcript"]
            if iv.get("questions"):     c["questions"]    = iv["questions"]
            if iv.get("fail_reason"):   c["fail_reason"]  = iv["fail_reason"]
        elif iv_status and iv_status != c["interview_status"]:
            c["interview_status"] = iv_status
            if iv_score_result and not c.get("score_result"):
                c["score_result"] = iv_score_result

        if c.get("score_result") and c.get("interview_score") is None:
            try:
                raw    = c["score_result"].get("interview_score", "0")
                iscore = int(str(raw).split("/")[0].strip())
                if iscore > 0:
                    c["interview_score"] = iscore
                    rscore = c.get("resume_score")
                    if rscore is not None:
                        c["combined_score"] = round(rscore * 0.4 + iscore * 0.6)
            except Exception:
                pass

        if c.get("callback_scheduled_at"):
            c["callback_scheduled_at"] = c["callback_scheduled_at"].isoformat()
        if oid:
            cands_by_opening[oid].append(c)

    return [
        {**o, "candidates": cands_by_opening.get(o["id"], [])}
        for o in openings_list
    ]


@router.get("/openings/{opening_id}")
async def get_opening(opening_id: str):
    o = opening_store.get(opening_id)
    if not o:
        raise HTTPException(404, "Opening not found.")
    return o


@router.put("/openings/{opening_id}")
async def update_opening(opening_id: str, req: OpeningUpdate):
    o = opening_store.get(opening_id)
    if not o:
        raise HTTPException(404, "Opening not found.")
    if req.title is not None:
        o["title"] = req.title
    if req.jd is not None:
        o["jd"] = req.jd
    _save_opening(opening_id, o)
    return o


@router.delete("/openings/{opening_id}", status_code=204)
async def delete_opening(opening_id: str):
    opening_store.pop(opening_id, None)
    _delete_opening(opening_id)


@router.get("/openings/{opening_id}/candidates")
async def get_opening_candidates(opening_id: str):
    from backend.app.state import interview_store
    from backend.app.database import _db_engine, _sql
    if not _db_engine:
        return []
    try:
        with _db_engine.connect() as conn:
            rows = conn.execute(_sql("""
                SELECT bc.batch_id, bc.single_id, bc.interview_id, bc.file_name, bc.name, bc.email, bc.phone,
                       bc.resume_score, bc.filter_status, bc.interview_status,
                       bc.interview_score, bc.combined_score, bc.callback_scheduled_at,
                       bc.analyze_result, bc.score_result,
                       i.status       AS iv_status,
                       i.score_result AS iv_score_result,
                       i.transcript, i.questions, i.fail_reason, i.call_log
                FROM batch_candidates bc
                LEFT JOIN interviews i ON i.id = bc.interview_id
                WHERE bc.opening_id = :oid
                ORDER BY bc.resume_score DESC NULLS LAST, bc.created_at ASC
            """), {"oid": opening_id}).mappings().all()
    except Exception as e:
        print(f"[DB] get_opening_candidates failed for {opening_id}: {e}")
        return []

    candidates = []
    for row in rows:
        c = dict(row)
        c["_batchId"]  = c.pop("batch_id", None)
        c["_singleId"] = c.pop("single_id", None)
        c["_type"]     = "single" if c["_singleId"] else "batch"

        iid            = c.get("interview_id")
        iv_status      = c.pop("iv_status", None)
        iv_score_result = c.pop("iv_score_result", None)

        # Enrich with live interview_store data (most current)
        iv = interview_store.get(iid) if iid else None
        if iv:
            c["interview_status"] = iv.get("status", c["interview_status"])
            if iv.get("score_result"):
                c["score_result"] = iv["score_result"]
            if iv.get("transcript"):
                c["transcript"] = iv["transcript"]
            if iv.get("questions"):
                c["questions"] = iv["questions"]
            if iv.get("fail_reason"):
                c["fail_reason"] = iv["fail_reason"]
        elif iv_status and iv_status != c["interview_status"]:
            # Fall back to interviews table status when batch_candidates is stale
            c["interview_status"] = iv_status
            if iv_score_result and not c.get("score_result"):
                c["score_result"] = iv_score_result

        if c.get("score_result") and c.get("interview_score") is None:
            try:
                raw    = c["score_result"].get("interview_score", "0")
                iscore = int(str(raw).split("/")[0].strip())
                if iscore > 0:
                    c["interview_score"] = iscore
                    rscore = c.get("resume_score")
                    if rscore is not None:
                        c["combined_score"] = round(rscore * 0.4 + iscore * 0.6)
            except Exception:
                pass

        if c.get("callback_scheduled_at"):
            c["callback_scheduled_at"] = c["callback_scheduled_at"].isoformat()
        candidates.append(c)
    return candidates
