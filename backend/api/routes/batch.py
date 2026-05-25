import uuid
import threading
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel

from backend.services.analyzer import analyze
from backend.services.interviewer import generate_questions, start_twilio_call
from backend.utils.file_utils import extract_text, extract_job_title
from backend.app.state import interview_store, batch_store, DEFAULT_QUESTIONS
from backend.app.database import _save_batch, _save_interview

router = APIRouter()


class BatchCallRequest(BaseModel):
    file_name: str


@router.post("/batch/start")
async def batch_start(
    background_tasks: BackgroundTasks,
    files:      List[UploadFile] = File(...),
    jd_text:    str = Form(...),
    job_title:  str = Form(default=''),
    opening_id: str = Form(default=''),
):
    if not jd_text.strip():
        raise HTTPException(400, "Job description is required.")

    candidates = []
    for file in files:
        entry = {
            "file_name":        file.filename or "unknown",
            "resume_text":      None,
            "name":             None,
            "email":            None,
            "phone":            None,
            "resume_score":     None,
            "analyze_result":   None,
            "filter_status":    "pending",
            "interview_id":     None,
            "interview_status": "pending",
            "interview_score":  None,
            "combined_score":   None,
            "callback_scheduled_at": None,
            "score_result":     None,
        }
        try:
            content = await file.read()
            entry["resume_text"] = extract_text(content, file.filename or "")
        except Exception as e:
            print(f"[Batch] Failed to parse {file.filename}: {e}")
            entry["filter_status"] = "filtered_out"
        candidates.append(entry)

    if all(c["resume_text"] is None for c in candidates):
        raise HTTPException(422, "No files could be parsed. Check that files are valid PDF or DOCX.")

    batch_id = str(uuid.uuid4())
    batch_store[batch_id] = {
        "batch_id":   batch_id,
        "opening_id": opening_id.strip() or None,
        "status":     "processing",
        "jd_text":    jd_text,
        "job_title":  job_title.strip() if job_title.strip() else extract_job_title(jd_text),
        "total":      len(candidates),
        "completed":  0,
        "candidates": candidates,
    }
    _save_batch(batch_id, batch_store[batch_id])
    background_tasks.add_task(_process_batch, batch_id)
    return {"batch_id": batch_id, "total": len(candidates), "status": "processing"}


@router.get("/batch/status/{batch_id}")
async def batch_status(batch_id: str):
    data = batch_store.get(batch_id)
    if not data:
        raise HTTPException(404, "Batch not found.")
    candidates_out = []
    for c in data["candidates"]:
        cd = {k: v for k, v in c.items() if k not in ("resume_text", "_batch_done")}
        iid = c.get("interview_id")
        if iid and iid in interview_store:
            iv = interview_store[iid]
            cd["call_log"] = iv.get("call_log", [])
            iv_status = iv.get("status")
            if iv_status and iv_status != "calling":
                cd["interview_status"]      = iv_status
                cd["fail_reason"]           = iv.get("fail_reason")
                cd["score_result"]          = iv.get("score_result")
                cd["transcript"]            = iv.get("transcript")
                cd["questions"]             = iv.get("questions")
                cd["callback_scheduled_at"] = iv.get("callback_scheduled_at")
                cd["processing_step"]       = iv.get("processing_step")
                if iv_status == "completed" and iv.get("score_result"):
                    sr = iv["score_result"]
                    try:
                        iscore = int(str(sr.get("interview_score", "0")).split("/")[0].strip())
                    except (ValueError, AttributeError):
                        iscore = None
                    if iscore is not None:
                        cd["interview_score"] = iscore
                        rscore = c.get("resume_score")
                        if rscore is not None:
                            cd["combined_score"] = round(rscore * 0.4 + iscore * 0.6)
        candidates_out.append(cd)
    return {
        "batch_id":  data["batch_id"],
        "status":    data["status"],
        "total":     data["total"],
        "completed": data["completed"],
        "candidates": candidates_out,
    }


def _process_batch(batch_id: str):
    data = batch_store.get(batch_id)
    if not data:
        return

    jd_text    = data["jd_text"]
    candidates = data["candidates"]

    def analyze_one(idx):
        cand = candidates[idx]
        if not cand["resume_text"]:
            cand["filter_status"] = "filtered_out"
            return
        try:
            result    = analyze(cand["resume_text"], jd_text)
            score_str = result.get("match_score", "0 / 100")
            score_num = int(str(score_str).split("/")[0].strip())
            cand.update({
                "analyze_result": result,
                "name":           result.get("name"),
                "email":          result.get("email"),
                "phone":          result.get("phone"),
                "resume_score":   score_num,
                "filter_status":  "qualified" if score_num >= 75 else "filtered_out",
            })
        except Exception as e:
            print(f"[Batch] analyze failed for {cand['file_name']}: {e}")
            cand["filter_status"] = "filtered_out"

    threads = [threading.Thread(target=analyze_one, args=(i,)) for i in range(len(candidates))]
    for t in threads: t.start()
    for t in threads: t.join()

    for cand in candidates:
        if cand["filter_status"] == "qualified" and not cand.get("phone"):
            cand["filter_status"]    = "no_phone"
            cand["interview_status"] = "no_phone"

    data["completed"] = len(candidates)
    data["status"]    = "completed"
    _save_batch(batch_id, data)
    print(f"[Batch] Analysis complete — {len(candidates)} candidates ranked. Use Call button to interview.")


@router.post("/batch/{batch_id}/interview/start")
async def batch_interview_start(batch_id: str, req: BatchCallRequest):
    data = batch_store.get(batch_id)
    if not data:
        raise HTTPException(404, "Batch not found.")

    cand = next((c for c in data["candidates"] if c["file_name"] == req.file_name), None)
    if not cand:
        raise HTTPException(404, "Candidate not found in batch.")
    if not cand.get("phone"):
        raise HTTPException(400, "Candidate has no phone number.")
    if not cand.get("resume_text"):
        raise HTTPException(400, "Resume text unavailable — re-upload this candidate's CV.")

    try:
        questions = generate_questions(cand["resume_text"], data["jd_text"])
    except Exception:
        questions = DEFAULT_QUESTIONS[:]

    interview_id = str(uuid.uuid4())
    interview_store[interview_id] = {
        "interview_id":          interview_id,
        "status":                "calling",
        "consent_status":        "pending",
        "consent_raw":           None,
        "consent_re_asked":      False,
        "callback_time_raw":     None,
        "callback_scheduled_at": None,
        "candidate_name":        cand.get("name"),
        "phone":                 cand["phone"],
        "questions":             questions,
        "jd_text":               data["jd_text"],
        "job_title":             data.get("job_title") or extract_job_title(data["jd_text"]),
        "recordings":            {},
        "transcriptions":        {},
        "repeat_counts":         {},
        "transcript":            None,
        "score_result":          None,
        "fail_reason":           None,
        "call_log":              [{"attempt": 1, "started_at": datetime.now().isoformat(), "status": "calling"}],
    }

    try:
        start_twilio_call(cand["phone"], interview_id)
    except Exception as e:
        del interview_store[interview_id]
        raise HTTPException(500, f"Failed to initiate call: {e}")

    cand["interview_id"]     = interview_id
    cand["interview_status"] = "calling"
    _save_interview(interview_id, interview_store[interview_id])
    _save_batch(batch_id, batch_store[batch_id])
    return {"interview_id": interview_id, "status": "calling"}
