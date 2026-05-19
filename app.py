from dotenv import load_dotenv
load_dotenv(override=True)

import os, uuid, io, html, time, threading, traceback, re, json
import anthropic as _anthropic
from datetime import datetime
from typing import List
from contextlib import asynccontextmanager

import fitz
import httpx as _httpx
from fastapi import FastAPI, HTTPException, Request, Form, BackgroundTasks, UploadFile, File
from fastapi.responses import HTMLResponse, Response
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


# ─── In-memory only — no file persistence ────────────────────────────────────
def _save_store():       pass   # no-op
def _load_store():       pass
def _save_batch_store(): pass
def _load_batch_store(): pass

def _reschedule_pending_callbacks():
    pass  # no persistent store — callbacks are in-memory only


# ─── Lifespan ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_app: FastAPI):
    if _SCHEDULER_OK:
        _scheduler.start()
        print("[Startup] APScheduler started (in-memory) — callback scheduling enabled")
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

COMPANY_NAME = os.getenv("COMPANY_NAME", "our company")

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
    """Extract job title from JD — tries labelled patterns first, then Claude, then first line."""
    # 1. Look for explicit label patterns
    label_patterns = [
        r'(?:job\s+title|position\s+title|role\s+title|title)\s*[:\-]\s*(.+)',
        r'(?:position|role|opening)\s*[:\-]\s*(.+)',
        r'(?:we\s+are\s+(?:hiring|looking)\s+for|seeking)\s+(?:a\s+|an\s+)?(.+?)(?:\s+to\b|\s+who\b|\s*[.,]|$)',
        r'(?:vacancy|opening)\s+for\s+(?:a\s+|an\s+)?(.+?)(?:\s*[.,]|$)',
    ]
    for line in jd_text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        for pat in label_patterns:
            m = re.search(pat, stripped, re.IGNORECASE)
            if m:
                title = m.group(1).strip().rstrip('.,;:').strip()
                if 3 <= len(title) <= 80:
                    return title[:60]

    # 2. Claude extraction (fast, haiku)
    claude_key = os.getenv("CLAUDE_API_KEY")
    if claude_key:
        try:
            client = _anthropic.Anthropic(api_key=claude_key)
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=20,
                system="Extract only the job title from the job description. Reply with only the job title — no other words.",
                messages=[{"role": "user", "content": jd_text[:600]}],
            )
            title = resp.content[0].text.strip().strip('"\'').rstrip('.,;:')
            if 3 <= len(title) <= 80:
                return title[:60]
        except Exception:
            pass

    # 3. Fallback: first non-empty line ≤ 80 chars
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
    """Return True if the candidate agreed to proceed.
    Uses keyword matching for clear cases; falls back to Claude sentiment for ambiguous ones."""
    t = text.lower().strip()
    if not t:
        return False  # no speech captured → not ready

    no_words  = ["no", "nope", "nah", "not", "busy", "later", "bad time", "can't", "cannot", "different"]
    yes_words = ["yes", "yeah", "yep", "sure", "okay", "ok", "good", "fine", "ready",
                 "go ahead", "of course", "absolutely", "now", "perfect", "great"]

    has_no  = any(re.search(r'\b' + re.escape(w) + r'\b', t) for w in no_words)
    has_yes = any(re.search(r'\b' + re.escape(w) + r'\b', t) for w in yes_words)

    # Clear unambiguous keyword match → use it immediately
    if has_no and not has_yes:
        print(f"[Consent] keyword=NO  text='{text}'")
        return False
    if has_yes and not has_no:
        print(f"[Consent] keyword=YES text='{text}'")
        return True

    # Ambiguous or no keyword match → ask Claude for sentiment
    claude_key = os.getenv("CLAUDE_API_KEY")
    if claude_key:
        try:
            client = _anthropic.Anthropic(api_key=claude_key)
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
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

    # Claude unavailable: if any no-keyword present, decline; else give benefit of doubt
    print(f"[Consent] fallback has_no={has_no} text='{text}'")
    return not has_no


def _parse_callback_time(raw: str) -> str | None:
    """Use Claude to convert spoken callback time into an ISO datetime string.
    Handles absolute times ('tomorrow at 3pm', 'Friday at 2') and
    relative times ('after 30 minutes', 'in an hour', 'call me tonight')."""
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
            model="claude-haiku-4-5-20251001",
            max_tokens=30,
            system="Return only an ISO 8601 datetime string or the word null. No explanation.",
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
        print(f"[Callback] interview_id {interview_id} not found in store — skipping")
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
    _save_store()
    try:
        start_twilio_call(data["phone"], interview_id)
        print(f"[Callback] Re-calling {data['phone']} for {interview_id}")
    except Exception as e:
        data["status"] = "failed"
        _save_store()
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
    job_title: str | None = None

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
        "job_title":             (req.job_title.strip() if req.job_title and req.job_title.strip() else _extract_job_title(req.jd_text)),
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

    _save_store()
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

    name        = data.get("candidate_name") or "there"
    safe_name   = html.escape(name.split()[0])   # first name only — more natural
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


REPEAT_KEYWORDS = [
    "repeat", "say that again", "again please", "pardon",
    "didn't hear", "didn't understand", "come again", "what was the question",
    "can you repeat", "please repeat",
]


@app.api_route("/twilio/consent/{interview_id}", methods=["GET", "POST"])
async def twilio_consent(
    interview_id: str,
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

    # If nothing was captured, re-ask once before giving up
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
            # Still no speech on second try — hang up gracefully
            data["status"]         = "failed"
            data["fail_reason"]    = "No response during consent check"
            data["consent_status"] = "declined"
            return _hangup_xml()

    if _detect_consent(transcript):
        data["consent_status"] = "accepted"
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
            f"  maxLength='300' playBeep='true' finishOnKey='#' timeout='15'"
            f"/>"
            f"<Redirect method='POST'>{base_url}/twilio/answer/{interview_id}/0</Redirect>"
            f"</Response>"
        )
    else:
        data["consent_status"] = "declined"
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


@app.api_route("/twilio/callback-time/{interview_id}", methods=["GET", "POST"])
async def twilio_callback_time(
    interview_id: str,
    SpeechResult: str = Form(default=None),
    RecordingUrl: str = Form(default=None),
):
    """Receives callback time via Gather speech (instant) or Record fallback, schedules re-call."""
    data = interview_store.get(interview_id)
    if not data:
        return _hangup_xml()

    # Gather gives SpeechResult instantly — no transcription needed
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

    # Mark the current call_log entry as callback_scheduled (not left as "calling")
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

    _save_store()

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
        duration = int(RecordingDuration or "0")

        print(f"[Twilio answer] interview={interview_id} q={q_idx}/{total-1} duration={duration}s")

        # ── Silence detection ─────────────────────────────────────────────────
        # Never advance on silence — always re-prompt and re-record same question.
        #   duration < 2  → pressed # immediately (no speech) → hint to say repeat
        #   13 ≤ dur ≤ 17 → 15s silence timeout fired         → hint to press #
        if RecordingUrl:
            is_immediate_silence = duration < 2
            is_timeout_silence   = 13 <= duration <= 17
            if is_immediate_silence:
                print(f"[Twilio answer] immediate silence q={q_idx} — prompting repeat hint")
                return _xml(
                    f"<Response>"
                    f"<Say voice='Google.en-IN-Neural2-A'>"
                    f"Please say repeat after the beep to hear the question again."
                    f"</Say>"
                    f"<Record"
                    f"  action='{base_url}/twilio/answer/{interview_id}/{q_idx}'"
                    f"  maxLength='300' playBeep='true' finishOnKey='#' timeout='15'"
                    f"/>"
                    f"<Redirect method='POST'>{base_url}/twilio/answer/{interview_id}/{q_idx}</Redirect>"
                    f"</Response>"
                )
            if is_timeout_silence:
                print(f"[Twilio answer] timeout silence q={q_idx} — prompting hash hint")
                return _xml(
                    f"<Response>"
                    f"<Say voice='Google.en-IN-Neural2-A'>"
                    f"Please press hash after completing your answer."
                    f"</Say>"
                    f"<Record"
                    f"  action='{base_url}/twilio/answer/{interview_id}/{q_idx}'"
                    f"  maxLength='300' playBeep='true' finishOnKey='#' timeout='15'"
                    f"/>"
                    f"<Redirect method='POST'>{base_url}/twilio/answer/{interview_id}/{q_idx}</Redirect>"
                    f"</Response>"
                )

            # ── Repeat detection ──────────────────────────────────────────────
            # Transcribe inline so we know if the candidate said "repeat".
            # Cache the transcription so _process_interview skips re-downloading.
            quick_text = None
            is_repeat  = False
            try:
                quick_text = transcribe_recording(RecordingUrl + ".mp3")
                print(f"[Twilio answer] q={q_idx} transcript: {quick_text[:100]!r}")
                is_repeat = any(kw in quick_text.lower() for kw in REPEAT_KEYWORDS)
            except Exception as te:
                print(f"[Twilio answer] inline transcription failed (skipping repeat check): {te}")

            if is_repeat:
                print(f"[Twilio answer] repeat detected q={q_idx} — re-asking")
                safe_q = html.escape(questions[q_idx])
                return _xml(
                    f"<Response>"
                    f"<Say voice='Google.en-IN-Neural2-A'>"
                    f"Of course! <break time='400ms'/>"
                    f"Question {q_idx+1} of {total}. <break time='300ms'/>{safe_q}"
                    f"</Say>"
                    f"<Record"
                    f"  action='{base_url}/twilio/answer/{interview_id}/{q_idx}'"
                    f"  maxLength='300' playBeep='true' finishOnKey='#' timeout='15'"
                    f"/>"
                    f"<Redirect method='POST'>{base_url}/twilio/answer/{interview_id}/{q_idx}</Redirect>"
                    f"</Response>"
                )

            # Save recording + cached transcription (avoids re-download during scoring)
            data["recordings"][q_idx] = RecordingUrl + ".mp3"
            if quick_text:
                data["transcriptions"][q_idx] = quick_text

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
                f"  maxLength='300' playBeep='true' finishOnKey='#' timeout='15'"
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
    call_log   = data.get("call_log", [])
    now_iso    = datetime.now().isoformat()
    if call_status in ("no-answer", "busy"):
        data["status"]      = "failed"
        data["fail_reason"] = "Call not answered" if call_status == "no-answer" else "Candidate's line was busy"
        if call_log:
            call_log[-1].update({"status": "failed", "ended_at": now_iso, "fail_reason": data["fail_reason"]})
    elif len(recordings) == 0:
        data["status"]      = "abandoned"
        data["fail_reason"] = "Candidate disconnected before answering any question"
        if call_log:
            call_log[-1].update({"status": "abandoned", "ended_at": now_iso})
    else:
        data["status"] = "processing"
        if call_log:
            call_log[-1]["status"] = "processing"
        background_tasks.add_task(_process_interview, interview_id)

    _save_store()
    return {"status": "ok"}


# ─── Background: Transcribe + Score ──────────────────────────────────────────
def _process_interview(interview_id: str):
    """Download each recording in parallel → transcribe → score with Claude."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    data = interview_store.get(interview_id)
    if not data:
        return

    questions  = data["questions"]
    recordings = data.get("recordings", {})
    total      = len(questions)

    # Prepend consent exchange to transcript
    lines = []
    consent_raw = data.get("consent_raw")
    if consent_raw:
        lines.append(f"Interviewer: Is this a good time for the interview?\nCandidate: {consent_raw}")

    # Transcribe all recordings in parallel
    done_count = 0
    answers    = {}

    cached_transcriptions = data.get("transcriptions", {})

    def transcribe_one(i):
        if i in cached_transcriptions:
            return i, cached_transcriptions[i]
        rec_url = recordings.get(i)
        if not rec_url:
            return i, "[no recording]"
        try:
            return i, transcribe_recording(rec_url)
        except Exception as e:
            return i, f"[transcription error: {e}]"

    data["processing_step"] = f"Transcribing 0 / {total}"
    _save_store()

    with ThreadPoolExecutor(max_workers=min(total, 6)) as pool:
        futures = {pool.submit(transcribe_one, i): i for i in range(total)}
        for fut in as_completed(futures):
            i, answer = fut.result()
            answers[i] = answer
            done_count += 1
            data["processing_step"] = f"Transcribing {done_count} / {total}"
            _save_store()

    for i, question in enumerate(questions):
        lines.append(f"Q{i+1}: {question}\nA{i+1}: {answers.get(i, '[no recording]')}")

    full_transcript = "\n\n".join(lines)

    data["processing_step"] = "Scoring interview…"
    _save_store()

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
    _save_store()


@app.post("/interview/recall/{interview_id}")
async def recall_interview(interview_id: str):
    """Re-dial a candidate using their existing interview session and questions."""
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

    _save_store()
    return {"interview_id": interview_id, "status": "calling"}


# ─── Batch Pipeline ───────────────────────────────────────────────────────────
@app.post("/batch/start")
async def batch_start(
    background_tasks: BackgroundTasks,
    files:     List[UploadFile] = File(...),
    jd_text:   str = Form(...),
    job_title: str = Form(default=''),
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
        "job_title":  job_title.strip() if job_title.strip() else _extract_job_title(jd_text),
        "total":      len(candidates),
        "completed":  0,
        "candidates": candidates,
    }
    _save_batch_store()
    background_tasks.add_task(_process_batch, batch_id)
    return {"batch_id": batch_id, "total": len(candidates), "status": "processing"}


@app.get("/batch/status/{batch_id}")
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
            # Sync live interview state so batch view reflects real call outcome
            iv_status = iv.get("status")
            if iv_status and iv_status != "calling":
                cd["interview_status"]      = iv_status
                cd["fail_reason"]           = iv.get("fail_reason")
                cd["score_result"]          = iv.get("score_result")
                cd["transcript"]            = iv.get("transcript")
                cd["questions"]             = iv.get("questions")
                cd["callback_scheduled_at"] = iv.get("callback_scheduled_at")
                cd["processing_step"]       = iv.get("processing_step")
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

    # Mark no-phone qualified candidates
    for cand in candidates:
        if cand["filter_status"] == "qualified" and not cand.get("phone"):
            cand["filter_status"]    = "no_phone"
            cand["interview_status"] = "no_phone"

    data["completed"] = len(candidates)
    data["status"]    = "completed"
    _save_batch_store()
    print(f"[Batch] Analysis complete — {len(candidates)} candidates ranked. Use Call button to interview.")


class BatchCallRequest(BaseModel):
    file_name: str

@app.post("/batch/{batch_id}/interview/start")
async def batch_interview_start(batch_id: str, req: BatchCallRequest):
    """Start a phone interview for a specific candidate in a completed batch."""
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
        "job_title":             data.get("job_title") or _extract_job_title(data["jd_text"]),
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
    _save_store()
    _save_batch_store()
    return {"interview_id": interview_id, "status": "calling"}


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
