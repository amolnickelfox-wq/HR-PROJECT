from dotenv import load_dotenv
load_dotenv(override=True)

import os, uuid, io, html, time, threading, traceback, re
import anthropic as _anthropic
from datetime import datetime
from typing import List
from contextlib import asynccontextmanager

import fitz
import httpx as _httpx
from fastapi import FastAPI, HTTPException, Request, Form, BackgroundTasks, UploadFile, File
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    _scheduler = BackgroundScheduler()
    _SCHEDULER_OK = True
except ImportError:
    _scheduler = None
    _SCHEDULER_OK = False
    print("[Startup] apscheduler not installed — callback scheduling disabled. Run: pip install apscheduler")

from analyzer    import analyze, parse_resume
from interviewer import generate_questions, transcribe_recording, score_interview, start_twilio_call


# ─── Lifespan ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_app: FastAPI):
    if _SCHEDULER_OK:
        _scheduler.start()
        print("[Startup] APScheduler started — callback scheduling enabled")
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

# ─── In-memory stores ─────────────────────────────────────────────────────────
interview_store: dict = {}
batch_store:     dict = {}

DEFAULT_QUESTIONS = [
    "Tell me a bit about yourself and what brought you to apply for this role.",
    "What do you know about this position and why does it interest you?",
    "Can you walk me through a situation where you had to handle pressure or a tight deadline?",
    "Tell me about an achievement from your recent work that you're proud of.",
    "How do you prefer to communicate and collaborate with your team?",
    "Where do you see yourself growing in the next couple of years?",
]


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _extract_job_title(jd_text: str) -> str:
    for line in jd_text.split('\n'):
        line = line.strip()
        if line and len(line) <= 80:
            return line[:60]
    return "the position"



def _extract_text(content: bytes, filename: str) -> str:
    """Extract plain text from PDF or DOCX bytes."""
    fn = (filename or "").lower()
    if fn.endswith(".pdf"):
        pdf  = fitz.open(stream=content, filetype="pdf")
        text = "\n".join(page.get_text() for page in pdf)
        pdf.close()
    elif fn.endswith((".docx", ".doc")):
        import docx
        doc  = docx.Document(io.BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    else:
        raise ValueError("Only PDF and DOCX files are supported.")
    if not text.strip():
        raise ValueError("Could not extract any text from the file.")
    return text


def _detect_consent(text: str) -> bool:
    """Return True if the candidate agreed to proceed with the interview."""
    t = text.lower()
    no_words  = {"no", "not", "busy", "later", "bad time", "can't", "cannot", "different", "nope", "nah"}
    yes_words = {"yes", "sure", "okay", "ok", "now", "good", "fine", "ready", "go ahead", "of course", "yeah", "yep", "absolutely"}
    if any(w in t for w in no_words):  return False
    if any(w in t for w in yes_words): return True
    return True  # default: proceed if unclear


def _parse_callback_time(raw: str) -> str | None:
    """Use Claude to convert spoken callback time into an ISO datetime string."""
    claude_key = os.getenv("CLAUDE_API_KEY")
    if not claude_key:
        return None
    try:
        client = _anthropic.Anthropic(api_key=claude_key)
        prompt = (
            f"The candidate said: \"{raw}\"\n"
            f"Today is {datetime.now().strftime('%A, %d %B %Y, %I:%M %p')} IST.\n"
            "Return ONLY an ISO 8601 datetime string (e.g. 2025-05-14T15:00:00) "
            "for the time they mentioned. If you cannot parse it, return the word null."
        )
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=50,
            system="Return only an ISO 8601 datetime string or the word null.",
            messages=[{"role": "user", "content": prompt}],
        )
        dt_str = resp.content[0].text.strip().strip('"\'')
        if dt_str.lower() == "null":
            return None
        datetime.fromisoformat(dt_str)   # validate
        return dt_str
    except Exception:
        return None


def _trigger_callback_call(interview_id: str):
    """Re-dial the candidate at the APScheduler-scheduled callback time."""
    data = interview_store.get(interview_id)
    if not data:
        return
    data.update({
        "status":                "calling",
        "consent_status":        "pending",
        "consent_raw":           None,
        "callback_time_raw":     None,
        "callback_scheduled_at": None,
        "recordings":            {},
        "repeat_counts":         {},
        "transcript":            None,
        "score_result":          None,
    })
    try:
        start_twilio_call(data["phone"], interview_id)
        print(f"[Callback] Re-calling {data['phone']} for {interview_id}")
    except Exception as e:
        data["status"] = "failed"
        print(f"[Callback] Failed to re-call: {e}")


# ─── Pydantic Models ──────────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    resume_text: str
    jd_text: str

class ParseRequest(BaseModel):
    resume_text: str

class InterviewRequest(BaseModel):
    phone: str
    resume_text: str
    jd_text: str
    candidate_name: str | None = None

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


# ─── Core Routes ──────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/analyze")
async def analyze_resume(req: AnalyzeRequest):
    if not req.resume_text.strip(): raise HTTPException(400, "Resume text is required.")
    if not req.jd_text.strip():     raise HTTPException(400, "Job description is required.")
    return analyze(req.resume_text, req.jd_text)


@app.post("/parse")
async def parse_only(req: ParseRequest):
    if not req.resume_text.strip(): raise HTTPException(400, "Resume text is required.")
    return parse_resume(req.resume_text)


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    content = await file.read()
    try:
        text = _extract_text(content, file.filename or "")
    except ValueError as e:
        code = 400 if "supported" in str(e) else 422
        raise HTTPException(status_code=code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {e}")
    return {"resume_text": text}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "AI Recruitment Assistant"}


@app.post("/interview/questions")
async def get_interview_questions(req: AnalyzeRequest):
    try:
        questions = generate_questions(req.resume_text, req.jd_text)
    except Exception:
        questions = DEFAULT_QUESTIONS[:]
    return {"questions": questions}


@app.post("/interview/simulate")
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


@app.post("/interview/local/next")
async def local_interview_next(req: LocalChatRequest):
    from interviewer import get_next_question
    try:
        return get_next_question(req.resume_text, req.jd_text, req.conversation, req.candidate_name)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/interview/local/score")
async def local_interview_score(req: LocalScoreRequest):
    from interviewer import score_conversation
    try:
        return score_conversation(req.conversation, req.jd_text)
    except Exception as e:
        raise HTTPException(500, str(e))


# ─── Interview — Trigger ──────────────────────────────────────────────────────
@app.post("/interview/start")
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
        "status":                "calling",
        "consent_status":        "pending",
        "consent_raw":           None,
        "callback_time_raw":     None,
        "callback_scheduled_at": None,
        "candidate_name":        req.candidate_name,
        "phone":                 req.phone,
        "questions":             questions,
        "jd_text":               req.jd_text,
        "job_title":             _extract_job_title(req.jd_text),
        "recordings":            {},
        "repeat_counts":         {},
        "transcript":            None,
        "score_result":          None,
    }

    try:
        start_twilio_call(req.phone, interview_id)
    except Exception as e:
        del interview_store[interview_id]
        raise HTTPException(500, f"Failed to initiate call: {e}")

    return {"interview_id": interview_id, "call_id": interview_id, "status": "calling", "questions": questions}


@app.get("/interview/status/{interview_id}")
async def interview_status(interview_id: str):
    if interview_id not in interview_store:
        raise HTTPException(404, "Interview not found.")
    return {k: v for k, v in interview_store[interview_id].items() if k != "jd_text"}


# ─── Twilio TwiML Routes ──────────────────────────────────────────────────────
def _xml(content: str) -> Response:
    return Response(content=f'<?xml version="1.0" encoding="UTF-8"?>\n{content}', media_type="application/xml")

def _hangup_xml() -> Response:
    return _xml("<Response><Hangup/></Response>")


@app.api_route("/twilio/start/{interview_id}", methods=["GET", "POST"])
async def twilio_start(interview_id: str):
    """Twilio calls this when the candidate picks up. Plays greeting then asks for consent."""
    data = interview_store.get(interview_id)
    if not data:
        return _hangup_xml()

    name       = data.get("candidate_name") or "there"
    safe_name  = html.escape(name)
    safe_title = html.escape(data.get("job_title", "the position"))
    base_url   = os.getenv("BASE_URL", "").rstrip("/")
    data["consent_status"] = "pending"

    return _xml(
        f"<Response>"
        f"<Gather input='speech' speechTimeout='auto' action='{base_url}/twilio/consent/{interview_id}' method='POST'>"
        f"<Say voice='Google.en-IN-Neural2-A'>"
        f"Hello {safe_name}. I am calling from the HR team at Nickelfox Technologies "
        f"regarding your application for the {safe_title} role. "
        f"Before we begin, I just want to check — is this a good time for the interview? "
        f"Please say yes or no."
        f"</Say>"
        f"</Gather>"
        f"<Redirect method='POST'>{base_url}/twilio/consent/{interview_id}</Redirect>"
        f"</Response>"
    )


REPEAT_KEYWORDS = [
    "repeat", "say that again", "again please", "pardon",
    "didn't hear", "didn't understand", "come again", "what was the question",
    "can you repeat", "please repeat",
]


@app.api_route("/twilio/consent/{interview_id}", methods=["GET", "POST"])
async def twilio_consent(
    interview_id: str,
    request:      Request,
    SpeechResult: str = Form(default=None),
    RecordingUrl: str = Form(default=None),
):
    """Processes candidate's yes/no consent. Starts interview or asks for callback time."""
    data = interview_store.get(interview_id)
    if not data:
        return _hangup_xml()

    base_url  = os.getenv("BASE_URL", "").rstrip("/")
    questions = data["questions"]
    total     = len(questions)
    safe_q0   = html.escape(questions[0])

    # Gather gives SpeechResult inline (fast). Fall back to recording transcription if needed.
    transcript = SpeechResult or ""
    if not transcript and RecordingUrl:
        try:
            transcript = transcribe_recording(RecordingUrl)
        except Exception as e:
            print(f"[Consent] transcription failed: {e}")

    print(f"[Consent] interview={interview_id} transcript='{transcript}'")
    data["consent_raw"] = transcript

    if _detect_consent(transcript):
        data["consent_status"] = "accepted"
        return _xml(
            f"<Response>"
            f"<Say voice='Google.en-IN-Neural2-A'>"
            f"Great, let us get started. "
            f"I will ask you {total} questions. "
            f"Speak your answer clearly. Pause for a few seconds when you are done and I will move to the next question automatically. "
            f"If you need a question repeated, just say repeat. "
            f"Question 1 of {total}. {safe_q0}"
            f"</Say>"
            f"<Record"
            f"  action='{base_url}/twilio/answer/{interview_id}/0'"
            f"  maxLength='120' playBeep='true' timeout='10'"
            f"/>"
            f"<Redirect method='POST'>{base_url}/twilio/answer/{interview_id}/0</Redirect>"
            f"</Response>"
        )
    else:
        data["consent_status"] = "declined"
        return _xml(
            f"<Response>"
            f"<Say voice='Google.en-IN-Neural2-A'>"
            f"No problem at all! Could you let us know what time works better for you? "
            f"Please say the day and time after the beep."
            f"</Say>"
            f"<Record"
            f"  action='{base_url}/twilio/callback-time/{interview_id}'"
            f"  maxLength='15' playBeep='true' timeout='10'"
            f"/>"
            f"<Redirect method='POST'>{base_url}/twilio/callback-time/{interview_id}</Redirect>"
            f"</Response>"
        )


@app.api_route("/twilio/callback-time/{interview_id}", methods=["GET", "POST"])
async def twilio_callback_time(
    interview_id: str,
    RecordingUrl: str = Form(default=None),
):
    """Records callback time, parses it with Claude, schedules re-call via APScheduler."""
    data = interview_store.get(interview_id)
    if not data:
        return _hangup_xml()

    raw_time = ""
    if RecordingUrl:
        try:
            raw_time = transcribe_recording(RecordingUrl)
            print(f"[CallbackTime] interview={interview_id} raw='{raw_time}'")
        except Exception as e:
            print(f"[CallbackTime] transcription failed: {e}")

    data["callback_time_raw"] = raw_time
    dt_str = _parse_callback_time(raw_time) if raw_time else None
    data["callback_scheduled_at"] = dt_str
    data["status"] = "callback_scheduled"

    if dt_str and _SCHEDULER_OK:
        try:
            dt = datetime.fromisoformat(dt_str)
            _scheduler.add_job(
                _trigger_callback_call, 'date',
                run_date=dt,
                args=[interview_id],
                id=f"callback_{interview_id}",
                replace_existing=True,
            )
            print(f"[Callback] Scheduled {interview_id} at {dt_str}")
        except Exception as e:
            print(f"[Callback] Schedule failed: {e}")

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


@app.api_route("/twilio/answer/{interview_id}/{q_idx}", methods=["GET", "POST"])
async def twilio_answer(
    interview_id:      str,
    q_idx:             int,
    background_tasks:  BackgroundTasks,
    request:           Request,
    RecordingUrl:      str = Form(default=None),
    RecordingDuration: str = Form(default=None),
    CallSid:           str = Form(default=None),
):
    """Twilio posts here after each answer is recorded. Checks repeat, saves, advances."""
    try:
        data = interview_store.get(interview_id)
        if not data:
            return _hangup_xml()

        if CallSid:
            data["twilio_call_sid"] = CallSid

        questions     = data["questions"]
        total         = len(questions)
        base_url      = os.getenv("BASE_URL", "").rstrip("/")
        repeat_counts = data.setdefault("repeat_counts", {})
        duration      = int(RecordingDuration or "0")

        print(f"[Twilio answer] interview={interview_id} q={q_idx}/{total-1} duration={duration}s")

        # Repeat detection — only for short recordings
        if RecordingUrl and duration <= 5:
            import concurrent.futures
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(transcribe_recording, RecordingUrl)
                    transcript = future.result(timeout=5)
                print(f"[Twilio answer] transcript: '{transcript}'")
            except Exception:
                transcript = ""

            words     = transcript.lower().split()
            is_repeat = (len(words) <= 12 and any(kw in transcript.lower() for kw in REPEAT_KEYWORDS))

            if is_repeat and repeat_counts.get(q_idx, 0) < 2:
                repeat_counts[q_idx] = repeat_counts.get(q_idx, 0) + 1
                print(f"[Twilio answer] repeat requested (count={repeat_counts[q_idx]}) for q={q_idx}")
                return _xml(
                    f"<Response>"
                    f"<Say voice='Google.en-IN-Neural2-A'>Sure. {html.escape(questions[q_idx])}</Say>"
                    f"<Record"
                    f"  action='{base_url}/twilio/answer/{interview_id}/{q_idx}'"
                    f"  maxLength='120' playBeep='true' timeout='10'"
                    f"/>"
                    f"<Redirect method='POST'>{base_url}/twilio/answer/{interview_id}/{q_idx}</Redirect>"
                    f"</Response>"
                )

        if RecordingUrl:
            data["recordings"][q_idx] = RecordingUrl

        next_q = q_idx + 1
        if next_q < total:
            print(f"[Twilio answer] advancing to q={next_q}")
            return _xml(
                f"<Response>"
                f"<Say voice='Google.en-IN-Neural2-A'>Question {next_q+1} of {total}. {html.escape(questions[next_q])}</Say>"
                f"<Record"
                f"  action='{base_url}/twilio/answer/{interview_id}/{next_q}'"
                f"  maxLength='120' playBeep='true' timeout='10'"
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


@app.post("/twilio/status/{interview_id}")
async def twilio_status_callback(interview_id: str, request: Request, background_tasks: BackgroundTasks):
    """Twilio posts call status here when call ends for any reason."""
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
    if call_status in ("no-answer", "busy"):
        data["status"]      = "failed"
        data["fail_reason"] = "Call not answered" if call_status == "no-answer" else "Candidate's line was busy"
    elif len(recordings) == 0:
        data["status"]      = "abandoned"
        data["fail_reason"] = "Candidate disconnected before answering any question"
    else:
        data["status"] = "processing"
        background_tasks.add_task(_process_interview, interview_id)

    return {"status": "ok"}


# ─── Background: Transcribe + Score ──────────────────────────────────────────
def _process_interview(interview_id: str):
    """Download each recording → transcribe → score with Claude."""
    data = interview_store.get(interview_id)
    if not data:
        return

    questions  = data["questions"]
    recordings = data.get("recordings", {})
    lines      = []

    # Prepend consent exchange to transcript
    consent_raw = data.get("consent_raw")
    if consent_raw:
        lines.append(f"Interviewer: Is this a good time for the interview?\nCandidate: {consent_raw}")

    for i, question in enumerate(questions):
        rec_url = recordings.get(i)
        if rec_url:
            try:
                answer = transcribe_recording(rec_url)
            except Exception as e:
                answer = f"[transcription error: {e}]"
        else:
            answer = "[no recording]"
        lines.append(f"Q{i+1}: {question}\nA{i+1}: {answer}")

    full_transcript = "\n\n".join(lines)

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

    interview_store[interview_id] = {
        **data,
        "status":       "completed",
        "transcript":   full_transcript,
        "score_result": score_result,
    }


# ─── Batch Pipeline ───────────────────────────────────────────────────────────
@app.post("/batch/start")
async def batch_start(
    background_tasks: BackgroundTasks,
    files:   List[UploadFile] = File(...),
    jd_text: str = Form(...),
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
            entry["resume_text"] = _extract_text(content, file.filename or "")
        except Exception as e:
            print(f"[Batch] Failed to parse {file.filename}: {e}")
            entry["filter_status"] = "filtered_out"
        candidates.append(entry)

    if all(c["resume_text"] is None for c in candidates):
        raise HTTPException(422, "No files could be parsed. Check that files are valid PDF or DOCX.")

    batch_id = str(uuid.uuid4())
    batch_store[batch_id] = {
        "batch_id":   batch_id,
        "status":     "processing",
        "jd_text":    jd_text,
        "total":      len(candidates),
        "completed":  0,
        "candidates": candidates,
    }
    background_tasks.add_task(_process_batch, batch_id)
    return {"batch_id": batch_id, "total": len(candidates), "status": "processing"}


@app.get("/batch/status/{batch_id}")
async def batch_status(batch_id: str):
    data = batch_store.get(batch_id)
    if not data:
        raise HTTPException(404, "Batch not found.")
    candidates_out = [
        {k: v for k, v in c.items() if k not in ("resume_text", "analyze_result", "_batch_done")}
        for c in data["candidates"]
    ]
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

    # Phase 2: analyze all resumes in parallel threads
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

    # Phase 3: start Twilio calls for qualified candidates
    for cand in candidates:
        if cand["filter_status"] != "qualified":
            cand["interview_status"] = "skipped"
            data["completed"] += 1
            continue
        if not cand.get("phone"):
            cand["filter_status"]    = "no_phone"
            cand["interview_status"] = "no_phone"
            data["completed"] += 1
            continue

        interview_id = str(uuid.uuid4())
        try:
            questions = generate_questions(cand["resume_text"], jd_text)
        except Exception:
            questions = DEFAULT_QUESTIONS[:]

        interview_store[interview_id] = {
            "interview_id":          interview_id,
            "status":                "calling",
            "consent_status":        "pending",
            "consent_raw":           None,
            "callback_time_raw":     None,
            "callback_scheduled_at": None,
            "candidate_name":        cand["name"],
            "phone":                 cand["phone"],
            "questions":             questions,
            "jd_text":               jd_text,
            "job_title":             _extract_job_title(jd_text),
                "recordings":            {},
            "repeat_counts":         {},
            "transcript":            None,
            "score_result":          None,
        }
        try:
            start_twilio_call(cand["phone"], interview_id)
            cand["interview_id"]     = interview_id
            cand["interview_status"] = "calling"
        except Exception as e:
            print(f"[Batch] call failed for {cand.get('name')}: {e}")
            cand["interview_status"] = "failed"
            data["completed"] += 1

    # Phase 4: poll until all interviews reach a terminal state (30 min max)
    terminal = {"completed", "abandoned", "failed", "callback_scheduled"}
    for _ in range(120):   # 120 × 15s = 30 min
        all_done = True
        for cand in candidates:
            iid = cand.get("interview_id")
            if not iid:
                continue
            iv        = interview_store.get(iid, {})
            iv_status = iv.get("status", "unknown")
            cand["interview_status"] = iv_status

            if iv_status in terminal and not cand.get("_batch_done"):
                cand["_batch_done"] = True
                if iv_status == "callback_scheduled":
                    cand["callback_scheduled_at"] = iv.get("callback_scheduled_at")
                else:
                    sr = iv.get("score_result")
                    if sr:
                        try:
                            iscore = int(str(sr.get("interview_score", "0/100")).split("/")[0].strip())
                        except Exception:
                            iscore = 0
                        cand["interview_score"] = iscore
                        cand["score_result"]    = sr
                        cand["combined_score"]  = round((cand["resume_score"] or 0) * 0.4 + iscore * 0.6, 1)
                data["completed"] += 1
            elif iv_status not in terminal:
                all_done = False

        if all_done:
            break
        time.sleep(15)

    # Phase 5: timeout any still-running interviews
    for cand in candidates:
        iid = cand.get("interview_id")
        if iid and not cand.get("_batch_done") and cand["interview_status"] not in terminal:
            cand["_batch_done"]      = True
            cand["interview_status"] = "timeout"
            data["completed"] += 1

    data["status"] = "completed"


# ─── Diagnostic ───────────────────────────────────────────────────────────────
@app.get("/debug/config")
async def debug_config():
    return {
        "BASE_URL":            os.getenv("BASE_URL"),
        "TWILIO_ACCOUNT_SID":  os.getenv("TWILIO_ACCOUNT_SID"),
        "TWILIO_PHONE_NUMBER": os.getenv("TWILIO_PHONE_NUMBER"),
        "scheduler_running":   (_scheduler.running if _SCHEDULER_OK and _scheduler else False),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
