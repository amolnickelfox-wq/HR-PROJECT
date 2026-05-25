import os
import uuid
import html
import re
import json
import traceback
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic as _anthropic
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Form
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from backend.services.interviewer import (
    generate_questions, transcribe_recording, score_interview,
    start_twilio_call, get_next_question, score_conversation,
)
from backend.utils.file_utils import extract_job_title
from backend.app.state import interview_store, batch_store, DEFAULT_QUESTIONS, _scheduler, _SCHEDULER_OK
from backend.app.database import _save_interview, _save_transcript_entries
from backend.app.callbacks import _trigger_callback_call

router = APIRouter()

REPEAT_KEYWORDS = [
    "repeat", "say that again", "again please", "pardon",
    "didn't hear", "didn't understand", "come again", "what was the question",
    "can you repeat", "please repeat",
]


# ─── Pydantic Models ──────────────────────────────────────────────────────────
class InterviewRequest(BaseModel):
    phone: str
    resume_text: str
    jd_text: str
    candidate_name: str | None = None
    job_title: str | None = None
    opening_id: str | None = None


class SimulateRequest(BaseModel):
    resume_text: str
    jd_text: str
    answers: list[str]
    candidate_name: str | None = None


class LocalChatRequest(BaseModel):
    resume_text: str
    jd_text: str
    conversation: list[dict]
    candidate_name: str | None = None


class LocalScoreRequest(BaseModel):
    resume_text: str
    jd_text: str
    conversation: list[dict]


# ─── TwiML helpers ───────────────────────────────────────────────────────────
def _xml(content: str) -> Response:
    return Response(content=f'<?xml version="1.0" encoding="UTF-8"?>\n{content}', media_type="application/xml")


def _hangup_xml() -> Response:
    return _xml("<Response><Hangup/></Response>")


# ─── Consent / Callback helpers ──────────────────────────────────────────────
def _detect_consent(text: str) -> bool:
    t = text.lower().strip()
    if not t:
        return False

    no_words  = ["no", "nope", "nah", "not", "busy", "later", "bad time", "can't", "cannot", "different"]
    yes_words = ["yes", "yeah", "yep", "sure", "okay", "ok", "good", "fine", "ready",
                 "go ahead", "of course", "absolutely", "now", "perfect", "great"]

    has_no  = any(re.search(r'\b' + re.escape(w) + r'\b', t) for w in no_words)
    has_yes = any(re.search(r'\b' + re.escape(w) + r'\b', t) for w in yes_words)

    if has_no and not has_yes:
        print(f"[Consent] keyword=NO  text='{text}'")
        return False
    if has_yes and not has_no:
        print(f"[Consent] keyword=YES text='{text}'")
        return True

    claude_key = os.getenv("CLAUDE_API_KEY")
    if claude_key:
        try:
            client = _anthropic.Anthropic(api_key=claude_key)
            resp = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=5,
                system="You classify spoken responses. Reply with only the word YES or NO.",
                messages=[{"role": "user", "content":
                    f"A candidate was asked: \"Is this a good time for a job interview?\"\n"
                    f"They responded: \"{text}\"\n"
                    f"Are they agreeing to proceed with the interview right now? Reply YES or NO only."
                }],
            )
            result = resp.content[0].text.strip().upper()
            print(f"[Consent] Claude sentiment='{result}' text='{text}'")
            return result.startswith("Y")
        except Exception as e:
            print(f"[Consent] Claude sentiment failed: {e}")

    print(f"[Consent] fallback has_no={has_no} text='{text}'")
    return not has_no


def _parse_callback_time(raw: str) -> str | None:
    claude_key = os.getenv("CLAUDE_API_KEY")
    if not claude_key:
        return None
    try:
        client = _anthropic.Anthropic(api_key=claude_key)
        now = datetime.now()
        prompt = (
            f"The candidate said: \"{raw}\"\n"
            f"Current date and time: {now.strftime('%A, %d %B %Y, %I:%M %p')} IST.\n\n"
            "Convert what they said into an exact ISO 8601 datetime (e.g. 2025-05-14T15:00:00).\n"
            "Handle all of these correctly:\n"
            "- Relative: 'after 30 minutes' → now + 30 min, 'in an hour' → now + 1 hour, 'in 2 hours' → now + 2 hours\n"
            "- Today: 'today at 5pm' → today 17:00, 'tonight at 8' → today 20:00\n"
            "- Named day: 'tomorrow at 3pm' → tomorrow 15:00, 'Friday at 2pm' → next Friday 14:00\n"
            "- Vague: 'morning' → next day 10:00, 'afternoon' → next day 14:00, 'evening' → next day 18:00\n"
            "Return ONLY the ISO 8601 string. If you truly cannot interpret it, return the word null."
        )
        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=30,
            system="Return only an ISO 8601 datetime string or the word null. No explanation.",
            messages=[{"role": "user", "content": prompt}],
        )
        dt_str = resp.content[0].text.strip().strip('"\'')
        if dt_str.lower() == "null":
            return None
        datetime.fromisoformat(dt_str)
        return dt_str
    except Exception:
        return None


# ─── Background: Transcribe + Score ──────────────────────────────────────────
def _process_interview(interview_id: str):
    data = interview_store.get(interview_id)
    if not data:
        return
    if data.get("_processing_started"):
        print(f"[Process] {interview_id} already processing — skipping duplicate")
        return
    data["_processing_started"] = True

    questions  = data["questions"]
    recordings = data.get("recordings", {})
    total      = len(questions)

    lines = []
    consent_raw = data.get("consent_raw")
    if consent_raw:
        lines.append(f"Interviewer: Is this a good time for the interview?\nCandidate: {consent_raw}")

    done_count = 0
    answers    = {}
    cached_transcriptions = data.get("transcriptions", {})

    def transcribe_one(i):
        rec_url = recordings.get(i)
        if not rec_url:
            return i, "[no recording]"
        try:
            return i, transcribe_recording(rec_url)
        except Exception as e:
            return i, f"[transcription error: {e}]"

    data["processing_step"] = f"Transcribing 0 / {total}"
    _save_interview(interview_id, data)

    with ThreadPoolExecutor(max_workers=min(total, 6)) as pool:
        futures = {pool.submit(transcribe_one, i): i for i in range(total)}
        for fut in as_completed(futures):
            i, answer = fut.result()
            answers[i] = answer
            done_count += 1
            data["processing_step"] = f"Transcribing {done_count} / {total}"
            _save_interview(interview_id, data)

    for i, question in enumerate(questions):
        lines.append(f"Q{i+1}: {question}\nA{i+1}: {answers.get(i, '[no recording]')}")

    full_transcript = "\n\n".join(lines)

    data["processing_step"] = "Scoring interview…"
    _save_interview(interview_id, data)

    try:
        score_result = score_interview(full_transcript, questions, data["jd_text"])
    except Exception as e:
        score_result = {
            "interview_score":    "Error",
            "communication":      {"score": 0, "max": 35},
            "confidence":         {"score": 0, "max": 30},
            "motivation_fit":     {"score": 0, "max": 20},
            "behavioral_quality": {"score": 0, "max": 15},
            "verdict":            "Error",
            "strengths":          [],
            "improvements":       [],
            "summary":            f"Scoring failed: {e}",
        }

    call_log = data.get("call_log", [])
    if call_log and call_log[-1].get("status") in ("processing", "calling"):
        call_log[-1]["status"] = "completed"
        call_log[-1].setdefault("ended_at", datetime.now().isoformat())

    interview_store[interview_id] = {
        **data,
        "status":       "completed",
        "transcript":   full_transcript,
        "score_result": score_result,
        "call_log":     call_log,
    }
    _save_interview(interview_id, interview_store[interview_id])
    _save_transcript_entries(interview_id, interview_store[interview_id])


class _QuestionsRequest(BaseModel):
    resume_text: str
    jd_text: str


# ─── Interview Routes ─────────────────────────────────────────────────────────
@router.post("/interview/questions")
async def get_interview_questions(req: _QuestionsRequest):
    try:
        questions = generate_questions(req.resume_text, req.jd_text)
    except Exception:
        questions = DEFAULT_QUESTIONS[:]
    return {"questions": questions}


@router.post("/interview/simulate")
async def simulate_interview(req: SimulateRequest):
    try:
        questions = generate_questions(req.resume_text, req.jd_text)
    except Exception:
        questions = DEFAULT_QUESTIONS[:]
    answers  = list(req.answers) + ["[no answer provided]"] * max(0, len(questions) - len(req.answers))
    answers  = answers[:len(questions)]
    lines    = [f"Q{i+1}: {q}\nA{i+1}: {a}" for i, (q, a) in enumerate(zip(questions, answers))]
    transcript = "\n\n".join(lines)
    try:
        score_result = score_interview(transcript, questions, req.jd_text)
    except Exception as e:
        raise HTTPException(500, f"Scoring failed: {e}")
    return {"questions": questions, "transcript": transcript, "score_result": score_result}


@router.post("/interview/local/next")
async def local_interview_next(req: LocalChatRequest):
    try:
        return get_next_question(req.resume_text, req.jd_text, req.conversation, req.candidate_name)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/interview/local/score")
async def local_interview_score(req: LocalScoreRequest):
    try:
        return score_conversation(req.conversation, req.jd_text)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/interview/start")
async def start_interview(req: InterviewRequest):
    if not req.phone.strip(): raise HTTPException(400, "Phone number is required.")
    interview_id = str(uuid.uuid4())
    try:
        questions = generate_questions(req.resume_text, req.jd_text)
    except Exception as e:
        print(f"[generate_questions error] {e}")
        questions = DEFAULT_QUESTIONS[:]

    interview_store[interview_id] = {
        "interview_id":          interview_id,
        "opening_id":            req.opening_id,
        "status":                "calling",
        "consent_status":        "pending",
        "consent_raw":           None,
        "callback_time_raw":     None,
        "callback_scheduled_at": None,
        "candidate_name":        req.candidate_name,
        "phone":                 req.phone,
        "questions":             questions,
        "jd_text":               req.jd_text,
        "job_title":             (req.job_title.strip() if req.job_title and req.job_title.strip() else extract_job_title(req.jd_text)),
        "recordings":            {},
        "transcriptions":        {},
        "repeat_counts":         {},
        "transcript":            None,
        "score_result":          None,
        "call_log":              [{"attempt": 1, "started_at": datetime.now().isoformat(), "status": "calling"}],
    }

    try:
        start_twilio_call(req.phone, interview_id)
    except Exception as e:
        del interview_store[interview_id]
        raise HTTPException(500, f"Failed to initiate call: {e}")

    _save_interview(interview_id, interview_store[interview_id])
    return {"interview_id": interview_id, "call_id": interview_id, "status": "calling", "questions": questions}


@router.get("/interview/status/{interview_id}")
async def interview_status(interview_id: str):
    if interview_id not in interview_store:
        raise HTTPException(404, "Interview not found.")
    return {k: v for k, v in interview_store[interview_id].items() if k != "jd_text"}


@router.get("/interview/stream/{interview_id}")
async def interview_stream(interview_id: str):
    async def _generator():
        while True:
            data = interview_store.get(interview_id)
            if not data:
                yield 'data: {"status":"not_found"}\n\n'
                break
            payload = {k: v for k, v in data.items() if k != "jd_text"}
            yield f"data: {json.dumps(payload)}\n\n"
            if data["status"] in ("completed", "abandoned", "failed", "callback_scheduled"):
                break
            await asyncio.sleep(0.3)

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/interview/recall/{interview_id}")
async def recall_interview(interview_id: str):
    data = interview_store.get(interview_id)
    if not data:
        raise HTTPException(404, "Interview session not found — server may have restarted.")

    existing_log = data.get("call_log", [])
    data.update({
        "status":                "calling",
        "consent_status":        "pending",
        "consent_raw":           None,
        "consent_re_asked":      False,
        "recordings":            {},
        "transcriptions":        {},
        "transcript":            None,
        "score_result":          None,
        "fail_reason":           None,
        "callback_time_raw":     None,
        "callback_scheduled_at": None,
        "call_log":              existing_log + [{"attempt": len(existing_log) + 1, "started_at": datetime.now().isoformat(), "status": "calling"}],
    })

    try:
        start_twilio_call(data["phone"], interview_id)
    except Exception as e:
        raise HTTPException(500, f"Failed to initiate call: {e}")

    _save_interview(interview_id, data)
    return {"interview_id": interview_id, "status": "calling"}


@router.get("/callbacks/due")
async def callbacks_due():
    now = datetime.now().isoformat()
    due = []
    for iid, iv in interview_store.items():
        if iv.get("status") != "callback_scheduled":
            continue
        scheduled = iv.get("callback_scheduled_at")
        if scheduled and scheduled <= now:
            due.append({
                "interview_id":          iid,
                "candidate_name":        iv.get("candidate_name"),
                "phone":                 iv.get("phone"),
                "job_title":             iv.get("job_title"),
                "callback_scheduled_at": scheduled,
                "callback_time_raw":     iv.get("callback_time_raw"),
            })
    return {"due": due}


# ─── Twilio TwiML Routes ──────────────────────────────────────────────────────
@router.api_route("/twilio/start/{interview_id}", methods=["GET", "POST"])
async def twilio_start(interview_id: str):
    data = interview_store.get(interview_id)
    if not data:
        return _hangup_xml()

    COMPANY_NAME = os.getenv("COMPANY_NAME", "Nickelfox Technologies")
    name        = data.get("candidate_name") or "there"
    safe_name   = html.escape(name.split()[0])
    safe_title  = html.escape(data.get("job_title", "the open position"))
    safe_co     = html.escape(COMPANY_NAME)
    base_url    = os.getenv("BASE_URL", "").rstrip("/")
    data["consent_status"] = "pending"

    return _xml(
        f"<Response>"
        f"<Gather input='speech' speechTimeout='3' action='{base_url}/twilio/consent/{interview_id}' method='POST'>"
        f"<Say voice='Google.en-IN-Neural2-A'>"
        f"Hello, may I speak with {safe_name}? "
        f"<break time='500ms'/>"
        f"Hi {safe_name}! This is Sarah calling from the HR team at {safe_co}. "
        f"I'm reaching out regarding your application for the {safe_title} role. "
        f"<break time='300ms'/>"
        f"I'd like to conduct a quick phone screening interview with you — it should take around 5 to 7 minutes. "
        f"Is this a good time to talk?"
        f"</Say>"
        f"</Gather>"
        f"<Redirect method='POST'>{base_url}/twilio/consent/{interview_id}</Redirect>"
        f"</Response>"
    )


@router.api_route("/twilio/consent/{interview_id}", methods=["GET", "POST"])
async def twilio_consent(
    interview_id: str,
    SpeechResult: str = Form(default=None),
    RecordingUrl: str = Form(default=None),
):
    data = interview_store.get(interview_id)
    if not data:
        return _hangup_xml()

    base_url  = os.getenv("BASE_URL", "").rstrip("/")
    name      = data.get("candidate_name") or "there"
    safe_name = html.escape(name.split()[0])
    questions = data["questions"]
    total     = len(questions)
    safe_q0   = html.escape(questions[0])

    transcript = SpeechResult or ""
    if not transcript and RecordingUrl:
        try:
            transcript = transcribe_recording(RecordingUrl)
        except Exception as e:
            print(f"[Consent] transcription failed: {e}")

    print(f"[Consent] interview={interview_id} transcript='{transcript}'")
    data["consent_raw"] = transcript

    if not transcript.strip():
        if not data.get("consent_re_asked"):
            data["consent_re_asked"] = True
            return _xml(
                f"<Response>"
                f"<Gather input='speech' speechTimeout='3' action='{base_url}/twilio/consent/{interview_id}' method='POST'>"
                f"<Say voice='Google.en-IN-Neural2-A'>I'm sorry, I didn't quite catch that. Could you please say yes if you're ready, or no if now isn't a good time?</Say>"
                f"</Gather>"
                f"<Redirect method='POST'>{base_url}/twilio/consent/{interview_id}</Redirect>"
                f"</Response>"
            )
        else:
            data["status"]         = "failed"
            data["fail_reason"]    = "No response during consent check"
            data["consent_status"] = "declined"
            _save_interview(interview_id, data)
            return _hangup_xml()

    if _detect_consent(transcript):
        data["consent_status"] = "accepted"
        _save_interview(interview_id, data)
        return _xml(
            f"<Response>"
            f"<Say voice='Google.en-IN-Neural2-A'>"
            f"Wonderful, thank you {safe_name}! "
            f"<break time='300ms'/>"
            f"So here is how this works — I will ask you {total} questions one by one. "
            f"After you finish answering each question, please press the hash key, that is the pound sign, to move on to the next one. "
            f"If you need me to repeat a question at any point, just say the word repeat and I will ask it again. "
            f"Take your time with each answer — there is no rush. "
            f"<break time='500ms'/>"
            f"Alright, let us begin! "
            f"<break time='400ms'/>"
            f"Question 1 of {total}. "
            f"<break time='300ms'/>"
            f"{safe_q0}"
            f"</Say>"
            f"<Record"
            f"  action='{base_url}/twilio/answer/{interview_id}/0'"
            f"  maxLength='120' playBeep='true' finishOnKey='#' timeout='5'"
            f"/>"
            f"<Redirect method='POST'>{base_url}/twilio/answer/{interview_id}/0</Redirect>"
            f"</Response>"
        )
    else:
        data["consent_status"] = "declined"
        _save_interview(interview_id, data)
        return _xml(
            f"<Response>"
            f"<Gather input='speech' speechTimeout='4' action='{base_url}/twilio/callback-time/{interview_id}' method='POST'>"
            f"<Say voice='Google.en-IN-Neural2-A'>"
            f"Absolutely, no problem at all! "
            f"Could you let me know when would be a better time to call you back? "
            f"You can say something like — in 30 minutes, today at 5 PM, or tomorrow morning."
            f"</Say>"
            f"</Gather>"
            f"<Redirect method='POST'>{base_url}/twilio/callback-time/{interview_id}</Redirect>"
            f"</Response>"
        )


@router.api_route("/twilio/callback-time/{interview_id}", methods=["GET", "POST"])
async def twilio_callback_time(
    interview_id: str,
    SpeechResult: str = Form(default=None),
    RecordingUrl: str = Form(default=None),
):
    data = interview_store.get(interview_id)
    if not data:
        return _hangup_xml()

    raw_time = SpeechResult or ""
    if not raw_time and RecordingUrl:
        try:
            raw_time = transcribe_recording(RecordingUrl)
            print(f"[CallbackTime] interview={interview_id} transcribed='{raw_time}'")
        except Exception as e:
            print(f"[CallbackTime] transcription failed: {e}")

    print(f"[CallbackTime] interview={interview_id} raw='{raw_time}'")

    data["callback_time_raw"] = raw_time
    dt_str = _parse_callback_time(raw_time) if raw_time else None
    data["callback_scheduled_at"] = dt_str
    data["status"] = "callback_scheduled"

    call_log = data.get("call_log", [])
    if call_log:
        call_log[-1]["status"]   = "callback_scheduled"
        call_log[-1]["ended_at"] = datetime.now().isoformat()
        if dt_str:
            call_log[-1]["callback_scheduled_at"] = dt_str

    if dt_str and _SCHEDULER_OK:
        try:
            dt = datetime.fromisoformat(dt_str)
            _scheduler.add_job(
                _trigger_callback_call, 'date',
                run_date=dt,
                args=[interview_id],
                id=f"callback_{interview_id}",
                replace_existing=True,
                misfire_grace_time=3600,
            )
            print(f"[Callback] Scheduled {interview_id} at {dt_str}")
        except Exception as e:
            print(f"[Callback] Schedule failed: {e}")

    _save_interview(interview_id, data)

    if dt_str:
        try:
            readable = datetime.fromisoformat(dt_str).strftime("%A at %I:%M %p")
        except Exception:
            readable = "the time you mentioned"
    else:
        readable = "the time you mentioned"

    return _xml(
        f"<Response>"
        f"<Say voice='Google.en-IN-Neural2-A'>"
        f"Perfect, we will call you back on {html.escape(readable)}. "
        f"Thank you for your time, have a great day!"
        f"</Say>"
        f"<Hangup/>"
        f"</Response>"
    )


@router.api_route("/twilio/answer/{interview_id}/{q_idx}", methods=["GET", "POST"])
async def twilio_answer(
    interview_id:      str,
    q_idx:             int,
    background_tasks:  BackgroundTasks,
    request:           Request,
    RecordingUrl:      str = Form(default=None),
    RecordingDuration: str = Form(default=None),
    CallSid:           str = Form(default=None),
    Digits:            str = Form(default=None),
):
    try:
        data = interview_store.get(interview_id)
        if not data:
            return _hangup_xml()

        if CallSid:
            data["twilio_call_sid"] = CallSid

        questions = data["questions"]
        total     = len(questions)
        base_url  = os.getenv("BASE_URL", "").rstrip("/")
        duration  = int(RecordingDuration or "0")

        print(f"[Twilio answer] interview={interview_id} q={q_idx}/{total-1} duration={duration}s digits={Digits!r}")

        if RecordingUrl and not data["transcriptions"].get(q_idx):
            data["status"] = "processing"

            # Truly silent — no speech at all
            if duration < 1 and not Digits:
                retries = data["repeat_counts"].get(q_idx, 0) + 1
                data["repeat_counts"][q_idx] = retries
                if retries < 3:
                    print(f"[Twilio answer] silence q={q_idx} retry={retries}/3")
                    return _xml(
                        f"<Response>"
                        f"<Say voice='Google.en-IN-Neural2-A'>"
                        f"I didn't hear anything. Please answer after the beep, then press hash."
                        f"</Say>"
                        f"<Record"
                        f"  action='{base_url}/twilio/answer/{interview_id}/{q_idx}'"
                        f"  maxLength='120' playBeep='true' finishOnKey='#' timeout='5'"
                        f"/>"
                        f"<Redirect method='POST'>{base_url}/twilio/answer/{interview_id}/{q_idx}</Redirect>"
                        f"</Response>"
                    )
                else:
                    print(f"[Twilio answer] silence q={q_idx} max retries — marking no answer")
                    data["transcriptions"][q_idx] = "[no answer provided]"

            else:
                # Transcribe first — repeat check must happen before pause hint
                quick_text = None
                try:
                    from concurrent.futures import ThreadPoolExecutor, TimeoutError as _TE
                    with ThreadPoolExecutor(max_workers=1) as _pool:
                        _fut = _pool.submit(transcribe_recording, RecordingUrl + ".mp3", fast=True)
                        try:
                            quick_text = _fut.result(timeout=10)
                            print(f"[Twilio answer] q={q_idx} transcript: {quick_text[:100]!r}")
                        except _TE:
                            print(f"[Twilio answer] q={q_idx} transcription timed out")
                except Exception as te:
                    print(f"[Twilio answer] inline transcription failed: {te}")

                is_repeat = bool(quick_text) and any(kw in quick_text.lower() for kw in REPEAT_KEYWORDS)

                if is_repeat:
                    repeat_count = data["repeat_counts"].get(q_idx, 0)
                    if repeat_count < 2:
                        data["repeat_counts"][q_idx] = repeat_count + 1
                        data["status"] = "calling"
                        print(f"[Twilio answer] repeat detected q={q_idx} count={repeat_count+1}/2 — re-asking")
                        safe_q = html.escape(questions[q_idx])
                        return _xml(
                            f"<Response>"
                            f"<Say voice='Google.en-IN-Neural2-A'>"
                            f"Of course! <break time='400ms'/>"
                            f"Question {q_idx+1} of {total}. <break time='300ms'/>{safe_q}"
                            f"</Say>"
                            f"<Record"
                            f"  action='{base_url}/twilio/answer/{interview_id}/{q_idx}'"
                            f"  maxLength='120' playBeep='true' finishOnKey='#' timeout='5'"
                            f"/>"
                            f"<Redirect method='POST'>{base_url}/twilio/answer/{interview_id}/{q_idx}</Redirect>"
                            f"</Response>"
                        )
                    else:
                        print(f"[Twilio answer] repeat limit reached q={q_idx} — moving on")
                        is_repeat = False

                # Spoke but didn't press # and transcription isn't a repeat
                if duration > 6 and not Digits:
                    print(f"[Twilio answer] spoke then paused q={q_idx} — prompting press #")
                    return _xml(
                        f"<Response>"
                        f"<Say voice='Google.en-IN-Neural2-A'>"
                        f"Please press hash to complete your answer."
                        f"</Say>"
                        f"<Record"
                        f"  action='{base_url}/twilio/answer/{interview_id}/{q_idx}'"
                        f"  maxLength='120' playBeep='true' finishOnKey='#' timeout='5'"
                        f"/>"
                        f"<Redirect method='POST'>{base_url}/twilio/answer/{interview_id}/{q_idx}</Redirect>"
                        f"</Response>"
                    )

                data["recordings"][q_idx] = RecordingUrl + ".mp3"
                if quick_text:
                    data["transcriptions"][q_idx] = quick_text

            if q_idx + 1 < total:
                data["status"] = "calling"
            _save_interview(interview_id, data)
            _save_transcript_entries(interview_id, data)

        next_q = q_idx + 1
        if next_q < total:
            print(f"[Twilio answer] advancing to q={next_q}")
            safe_next_q = html.escape(questions[next_q])
            return _xml(
                f"<Response>"
                f"<Say voice='Google.en-IN-Neural2-A'>"
                f"Question {next_q+1} of {total}. <break time='300ms'/>{safe_next_q}"
                f"</Say>"
                f"<Record"
                f"  action='{base_url}/twilio/answer/{interview_id}/{next_q}'"
                f"  maxLength='120' playBeep='true' finishOnKey='#' timeout='5'"
                f"/>"
                f"<Redirect method='POST'>{base_url}/twilio/answer/{interview_id}/{next_q}</Redirect>"
                f"</Response>"
            )
        else:
            print(f"[Twilio answer] all questions done — closing call")
            data["status"] = "processing"
            background_tasks.add_task(_process_interview, interview_id)
            return _xml(
                "<Response>"
                "<Say voice='Google.en-IN-Neural2-A'>"
                "Thank you so much for your time. "
                "We will review your responses and get back to you soon. "
                "Have a wonderful day. Goodbye!"
                "</Say>"
                "<Hangup/>"
                "</Response>"
            )

    except Exception as e:
        print(f"[Twilio answer] UNHANDLED ERROR at q={q_idx}: {e}")
        traceback.print_exc()
        return _xml(
            "<Response>"
            "<Say voice='Google.en-IN-Neural2-A'>"
            "We encountered a technical issue. Thank you for your time. Goodbye!"
            "</Say>"
            "<Hangup/>"
            "</Response>"
        )


@router.post("/twilio/status/{interview_id}")
async def twilio_status_callback(interview_id: str, request: Request, background_tasks: BackgroundTasks):
    form        = await request.form()
    call_status = form.get("CallStatus", "")
    print(f"[Twilio status] interview={interview_id} CallStatus={call_status}")

    data = interview_store.get(interview_id)
    if not data:
        return {"status": "ok"}

    terminal_call = {"completed", "no-answer", "busy", "failed", "canceled"}
    if call_status not in terminal_call:
        return {"status": "ok"}
    if data["status"] in ("processing", "completed", "abandoned", "failed", "callback_scheduled"):
        return {"status": "ok"}

    recordings = data.get("recordings", {})
    call_log   = data.get("call_log", [])
    now_iso    = datetime.now().isoformat()
    if call_status in ("no-answer", "busy"):
        data["status"]      = "failed"
        data["fail_reason"] = "Call not answered" if call_status == "no-answer" else "Candidate's line was busy"
        if call_log:
            call_log[-1].update({"status": "failed", "ended_at": now_iso, "fail_reason": data["fail_reason"]})
    elif len(recordings) == 0 and call_status != "completed":
        data["status"]      = "abandoned"
        data["fail_reason"] = "Candidate disconnected before answering any question"
        if call_log:
            call_log[-1].update({"status": "abandoned", "ended_at": now_iso})
    else:
        data["status"] = "processing"
        if call_log:
            call_log[-1]["status"] = "processing"
        background_tasks.add_task(_process_interview, interview_id)

    _save_interview(interview_id, data)
    return {"status": "ok"}
