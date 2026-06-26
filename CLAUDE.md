# RecruitAI — AI-Powered HR Screening Assistant

## What It Does
Phone-based AI recruitment pipeline: upload resumes → Claude scores them → Twilio calls candidates → Groq Whisper transcribes answers → Claude scores the interview. Supports single calls, batch processing, and parallel pipelines.

---

## Stack

### Backend
| Package | Version | Role |
|---------|---------|------|
| `fastapi` | 0.115.0 | HTTP framework |
| `uvicorn[standard]` | 0.30.6 | ASGI server |
| `pydantic` | 2.9.2 | Request/response validation |
| `python-dotenv` | ≥1.0.0 | `.env` loading via `backend/app/config.py` |
| `httpx` | ≥0.27.0 | HTTP client (ngrok detection, Twilio audio fetch) |
| `anthropic` | ≥0.25.0 | Claude API — question generation, consent detection, scoring, job title extraction |
| `groq` | ≥0.9.0 | Groq Whisper API — audio transcription |
| `twilio` | ≥9.0.0 | Outbound calls, TwiML, recording, AMD |
| `apscheduler` | ≥3.10.0 | Scheduled callback re-calls (`BackgroundScheduler`) |
| `sqlalchemy` | ≥2.0 | ORM / query layer |
| `psycopg` | ≥3.0 | PostgreSQL driver (psycopg3) |
| `PyMuPDF` | ≥1.23.0 | PDF text extraction (`fitz`) |
| `python-docx` | ≥1.1.0 | DOCX text extraction |
| `python-multipart` | ≥0.0.9 | Multipart form uploads (file + form fields) |
| `PyJWT` | (implicit) | JWT encode/decode in `auth.py` |

### Frontend (React + Vite)
| Package | Role |
|---------|------|
| React 18 | UI framework |
| Vite | Dev server + bundler, proxies API to `localhost:8000` |
| `@phosphor-icons/react` | Icon library used throughout |
| `useAnalyze`, `useInterview`, `useBatch` hooks | Encapsulate API call + state logic |
| `AppContext` | Global openings state, duplicate detection, callback alerts |

---

## Running the Project

> **CRITICAL: Start ngrok BEFORE the backend.** The server auto-detects ngrok on startup (`http://localhost:4040/api/tunnels`) and sets `BASE_URL` for Twilio webhooks. If ngrok isn't running first, all Twilio callbacks fail silently.

```
# Terminal 1 — ngrok (always first)
ngrok http 8000

# Terminal 2 — backend
cd backend
.venv\Scripts\activate
uvicorn backend.app.main:app --reload --port 8000

# Terminal 3 — frontend
cd frontend
npm run dev
```

---

## Environment Variables (`.env` at project root — NEVER commit)

```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
JWT_SECRET=<random string>
CLAUDE_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
BASE_URL=https://xxxx.ngrok.io    # auto-set on startup if ngrok running
COMPANY_NAME=NickelFox Technologies
SUPER_ADMIN_USERNAME=director
SUPER_ADMIN_PASSWORD=...
SMTP_USER=<SES SMTP user>         # optional — for welcome emails
SMTP_PASSWORD=<SES SMTP password>
SMTP_FROM=noreply@...
APP_URL=http://localhost:3001
```

Loaded by `backend/app/config.py` (first import in `main.py`).

---

## Project Structure

```
backend/
  app/
    main.py          — FastAPI app, lifespan (DB init, store restore, stale-call cleanup, pipeline auto-resume, ngrok detect, callback reschedule); global Twilio error handler
    state.py         — In-memory stores + APScheduler instance
    database.py      — ALL DB functions (init, save, load, sync, helpers); includes _reset_candidate_on_call_failure()
    config.py        — Loads .env via python-dotenv
    callbacks.py     — APScheduler callback re-dial logic
    dependencies.py  — FastAPI dependency injection helpers
  api/routes/
    auth.py          — JWT auth, user management
    interview.py     — ALL Twilio TwiML routes + _process_interview background job
    batch.py         — Batch upload, /calls/active endpoint
    pipeline.py      — Pipeline orchestration (start/stop/status, _on_pipeline_call_ended)
    openings.py      — Job openings CRUD
    health.py        — Health check endpoint
    resume.py        — Single resume analyze endpoint
  services/
    interviewer.py   — Claude (questions + scoring), Groq Whisper, start_twilio_call()
    email_service.py — Amazon SES SMTP welcome emails
  utils/
    file_utils.py    — PDF/DOCX text extraction, job title extraction

frontend/src/
  App.jsx              — Shell: routing, pipeline state, active calls polling, sidebar
  api/client.js        — All fetch() wrappers (apiAnalyze, apiStartInterview, apiActiveCalls, etc.)
  context/AppContext.jsx — Openings, batches, callbacks, duplicate detection
  hooks/
    useAnalyze.js      — Resume analyze flow
    useInterview.js    — Single Twilio call flow
    useBatch.js        — Batch upload + per-candidate call flow
  components/
    Sidebar.jsx           — Navigation + active calls / callbacks badges
    BatchResultsTable.jsx — Candidate table with call button
    BatchProgress.jsx     — Batch processing progress display
    InterviewPanel.jsx    — Live interview status during a call
    ResultsDashboard.jsx  — Score breakdown after completion
    ScoreBreakdown.jsx    — Bar charts for interview scoring dimensions
    CallbackAlertModal.jsx — Due callback alert banner
    LoginPage.jsx         — Auth page
    UserManagement.jsx    — super_admin user CRUD
    LocalInterview.jsx    — Browser-based simulated interview (no Twilio)
    SimulateForm.jsx      — Simulate interview with manual answers
    (+ CandidateCard, ContactCard, SkillsPanel, ScoreRing, JsonViewer, ReasonBox, Header)
```

---

## In-Memory Stores (`backend/app/state.py`)

| Store | Key | Value |
|-------|-----|-------|
| `interview_store` | `interview_id` (UUID) | Full interview dict — status, questions, recordings, score |
| `batch_store` | `batch_id` (UUID) | Batch metadata + all candidates list |
| `opening_store` | `opening_id` (UUID) | Job opening title + JD text |
| `pipeline_store` | `pipeline_id` (UUID) | Queue, active, completed, skipped, status |
| `opening_pipeline` | `opening_id` | `pipeline_id` — one active pipeline per opening |

`interview_store` is the live source of truth during a call. DB is ~1-2s behind. On startup, all stores are restored from PostgreSQL.

---

## Database Schema

### `job_openings`
`id, title, jd_text, created_at`

### `interviews`
`id, opening_id, status, consent_status, consent_raw, consent_re_asked, candidate_name, phone, job_title, jd_text, twilio_call_sid, transcript, fail_reason, processing_step, callback_time_raw, callback_scheduled_at, questions (jsonb), recordings (jsonb), transcriptions (jsonb), repeat_counts (jsonb), score_result (jsonb), call_log (jsonb), created_at, updated_at`

### `batch_candidates`
`id (serial), batch_id, single_id, opening_id, interview_id, file_name, name, email, phone, resume_score, filter_status, interview_status, interview_score, combined_score, callback_scheduled_at, resume_text, analyze_result (jsonb), score_result (jsonb), created_at, updated_at`

### `batches`
`id, opening_id, status, jd_text, job_title, total, completed, created_at, updated_at`

### `pipelines`
`id, opening_id, status, queue (jsonb), active (jsonb), completed (jsonb), skipped (jsonb), total, jd_text, job_title, created_at, updated_at`

### `transcript_entries`
`id (serial), interview_id, question_index, question_text, answer_text, recording_url, repeat_count, created_at`

### `users`
`id (serial), username, full_name, password_hash, role, must_change_password, temp_expires_at, created_at`

---

## All API Endpoints

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Login → JWT token |
| POST | `/auth/logout` | Logout (client-side token drop) |
| GET | `/auth/me` | Validate token, get current user |
| GET | `/auth/users` | List users (super_admin only) |
| POST | `/auth/users` | Create user + send welcome email (super_admin only) |
| DELETE | `/auth/users/{username}` | Delete user (super_admin only) |
| PUT | `/auth/users/{username}/password` | Reset password (super_admin only) |
| PUT | `/auth/change-password` | Change own password |

### Resume / Single Candidate
| Method | Path | Description |
|--------|------|-------------|
| POST | `/analyze` | Analyze single resume against JD, return score + candidate details |

### Interview (Single Call)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/interview/start` | Start Twilio call, create interview |
| GET | `/interview/status/{id}` | Poll interview status |
| GET | `/interview/stream/{id}` | SSE stream of interview status |
| POST | `/interview/recall/{id}` | Re-call same candidate |
| POST | `/interview/force-resolve/{id}` | Force processing or mark abandoned |
| POST | `/interview/questions` | Generate questions from resume + JD |
| POST | `/interview/simulate` | Simulate interview with provided answers |
| POST | `/interview/local/next` | Get next question for browser interview |
| POST | `/interview/local/score` | Score a browser interview conversation |

### Twilio Webhooks
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/twilio/start/{id}` | Initial TwiML — greeting + consent gather |
| GET/POST | `/twilio/consent/{id}` | Consent response handler |
| GET/POST | `/twilio/answer/{id}/{q}` | Answer recording handler (q = 0–6) |
| GET/POST | `/twilio/callback-time/{id}` | Callback time parser |
| POST | `/twilio/status/{id}` | Twilio call status callback |
| POST | `/twilio/amd/{id}` | Async AMD callback (voicemail detection) |

### Batch
| Method | Path | Description |
|--------|------|-------------|
| POST | `/batch/start` | Upload resumes + JD, start batch analysis |
| GET | `/batch/status/{id}` | Poll batch + all candidate statuses |
| POST | `/batch/{id}/interview/start` | Start call for one candidate in batch |
| GET | `/calls/active` | Global active calls across all batches + pipelines |

### Pipeline
| Method | Path | Description |
|--------|------|-------------|
| POST | `/openings/{id}/pipeline/start` | Start parallel calling pipeline |
| GET | `/openings/{id}/pipeline/status` | Poll pipeline progress |
| POST | `/openings/{id}/pipeline/stop` | Stop pipeline, drain queue |

### Openings
| Method | Path | Description |
|--------|------|-------------|
| GET | `/openings` | List all job openings |
| POST | `/openings` | Create opening |
| GET | `/openings/{id}` | Get single opening |
| PUT | `/openings/{id}` | Update title/JD |
| DELETE | `/openings/{id}` | Delete opening |

### Other
| Method | Path | Description |
|--------|------|-------------|
| GET | `/callbacks/due` | List overdue scheduled callbacks |
| GET | `/health` | Health check |

---

## AI / ML Services

### Claude (Anthropic)
Files: `backend/services/interviewer.py`, `backend/api/routes/interview.py`, `backend/utils/file_utils.py`
Model: `claude-haiku-4-5-20251001` (`interviewer.py`) / `claude-haiku-4-5` short alias (`interview.py`)

| Task | Where | Output |
|------|-------|--------|
| Resume scoring + candidate extraction | `resume.py` → `analyze()` | Structured JSON |
| Question generation (7 questions) | `generate_questions()` | JSON array |
| Consent detection (ambiguous speech) | `_detect_consent()` | YES/NO |
| Repeat request detection | `_is_repeat_request()` | YES/NO |
| Callback time parsing | `_parse_callback_time()` | ISO 8601 datetime |
| Interview scoring | `score_interview()` | JSON with 4 dimensions |
| Job title extraction | `extract_job_title()` | Plain text |

### Groq Whisper
File: `backend/services/interviewer.py` → `transcribe_recording(url, fast=False)`

- Model: `whisper-large-v3` (default) / `whisper-large-v3-turbo` (fast mode)
- Multilingual — handles Hindi, English, Hinglish natively
- Fetches audio from Twilio URL with Basic Auth, sends to Groq
- 3 retries with exponential backoff (Twilio recordings can 404 briefly)
- `ThreadPoolExecutor(max_workers=6)` for parallel transcription in `_process_interview`
- **Inline transcription** during live call uses `threading.Thread.join(timeout=12)` — hard 12s cap so Twilio webhook always responds in time. If it times out, `_process_interview` re-transcribes that answer from the recording URL after the call ends.

### Twilio
File: `backend/services/interviewer.py` → `start_twilio_call(phone, interview_id)`

- Outbound calls from `TWILIO_PHONE_NUMBER`
- AMD: `machine_detection="DetectMessageEnd"`, `machine_detection_timeout=30`, `async_amd=True`
- Status callback fires on: `initiated`, `ringing`, `answered`, `completed`
- `<Gather input='speech' language='hi-IN en-IN'>` — bilingual speech recognition
- `<Record maxLength='120' finishOnKey='#'>` — candidate answers, beep to start
- `timeout=20` — ring timeout in seconds before Twilio fires no-answer

---

## Interview Call Flow (Twilio TwiML)

```
/twilio/start/{id}
  → "Hello, could I speak with {name}? This is Sarah from NickelFox..."
  → <Gather language='hi-IN en-IN'> "Is this a good time?"
  → /twilio/consent/{id}

/twilio/consent/{id}
  → no speech → re-ask once → still silent → status=failed, pipeline: no_answer
  → _detect_consent(text): keyword check → Claude Haiku fallback
      YES → instructions ("press # when done, say repeat to re-hear") + Q1 → <Record> → /twilio/answer/{id}/0
      NO  → "Could you let me know a better time?" → /twilio/callback-time/{id}

/twilio/answer/{id}/{0..6}
  → silence (<3s, no #) → re-prompt up to 3 times
  → recording received → inline Groq transcription (12s timeout via Thread.join — Twilio limit is 15s)
  → if repeat keyword or Claude detects repeat → re-ask same question (max 2 times)
  → if spoke but no # and duration 6–118s → "press # to wrap up" prompt
  → save recording URL to data["recordings"][q_idx]
  → save transcription to data["transcriptions"][q_idx] (only if inline succeeded)
  → if q < 6 → transition phrase + next question
  → if q == 6 → closing message → _process_interview() in background → Hangup

/twilio/amd/{id}  [async, fires concurrently during active call]
  → AnsweredBy starts with "machine" → client.calls(sid).update(status="completed") → status=failed

/twilio/status/{id}  [fires when Twilio call reaches terminal state]
  → no-answer / busy → status=failed, pipeline: no_answer
  → completed + has recordings → status=processing → _process_interview()
  → completed + 0 recordings → status=abandoned, pipeline: no_answer
  → already terminal (processing/completed/failed/etc.) → skip (no double-fire)

/twilio/callback-time/{id}
  → parse time with Claude Haiku → _save_interview → schedule APScheduler job (save BEFORE schedule
    to prevent orphaned APScheduler jobs if save throws)
  → handles English AND Hindi/Hinglish: "10 minute baad", "kal 3 baje", "aaj shaam ko", etc.
  → status=callback_scheduled, pipeline: callback
  → unparseable → status=declined, pipeline: declined
```

**Global Twilio error handler** (`main.py`): `@app.exception_handler(Exception)` catches any unhandled
exception on `/twilio/` routes and returns graceful TwiML ("We're having a technical issue, we'll call
you back shortly") instead of Twilio's "application error has occurred" message.

### `_process_interview()` (background thread, `interview.py`)
1. `_processing_started` guard + `try/finally` cleanup (prevents permanent lock on crash)
2. `ThreadPoolExecutor(max_workers=min(total,6))` — parallel Groq Whisper; reuses inline transcription
   from `data["transcriptions"]` if already cached (skips Groq re-call for that answer)
3. `data["transcriptions"].update(answers)` — syncs all final transcriptions back (fills any that timed out inline)
4. Build full transcript: consent + Q1/A1 … Q7/A7
5. `score_interview(transcript, questions, jd_text)` via Claude
6. Save: `_save_interview`, `_save_transcript_entries`, `_sync_candidate_interview`
7. Fire `_on_pipeline_call_ended(id, "completed")` if this was a pipeline call

---

## Pipeline ("Call All Qualified")

```
POST /openings/{id}/pipeline/start
  → _get_qualified_candidates_for_opening(opening_id)
       filter_status='qualified', phone IS NOT NULL
       interview_status NOT IN ('completed', 'processing', 'calling', 'callback_scheduled', 'declined')
       ORDER BY resume_score DESC
  → dedup by phone (keep highest resume_score)
  → pipeline = {queue:[...], active:{}, completed:[], skipped:[], status:"running", max_concurrent:3}
  → _fill_slots() runs in daemon thread

_start_candidate_call(pipeline_id, candidate, pipeline)
  → generate_questions() via Claude
  → create interview_store entry with pipeline_id
  → _link_batch_candidate_interview() → batch_candidates.interview_status = 'calling'
  → start_twilio_call() with AMD
  → on failure: delete interview from store + DB, call _reset_candidate_on_call_failure(bc_id)
    to NULL out batch_candidates.interview_id/interview_status so candidate is re-eligible

_on_pipeline_call_ended(interview_id, outcome)  [called at every terminal point in interview.py]
  → find owning pipeline via pipeline_store scan
  → acquire _pipeline_locks[pipeline_id] (threading.Lock)
  → pop candidate from active
  → "completed"  → completed list
  → "no_answer"  → re-queue once (no_answer_count < 1) → then skipped as "no_answer_twice"
                   (2 total attempts per candidate)
  → "declined"   → skipped as "declined"
  → "callback"   → skipped as "callback"
  → _fill_slots() → start next candidates
  → queue empty + active empty → status="completed", remove from opening_pipeline
  → _save_pipeline() to DB
```

**Server restart recovery** (`main.py` lifespan):
1. Stale active entries (calls stuck mid-flight during downtime) are resolved: completed→completed,
   callback_scheduled→skipped, calling/in_progress/processing→re-queued once (max 1 retry), others→skipped
2. Any running pipeline with empty active + non-empty queue auto-resumes via `_fill_slots()` in daemon thread

**Stop Pipeline button**: available on the Active Calls page in the UI — drains the queue and sets status="stopped".

---

## Callbacks (APScheduler)

File: `backend/app/callbacks.py`

- `BackgroundScheduler` (APScheduler) started in `main.py` lifespan
- `_trigger_callback_call(interview_id)` — resets interview state (clears recordings/transcriptions), re-dials
- `_reschedule_pending_callbacks()` — on server startup, re-registers all `callback_scheduled` interviews with APScheduler; overdue ones fire immediately in daemon threads
- Jobs keyed as `callback_{interview_id}`, `replace_existing=True`
- `misfire_grace_time=3600` — fires up to 1 hour late if server was briefly down

---

## Auth System (`backend/api/routes/auth.py`)

- JWT HS256, 8-hour expiry; payload: `{sub, role, must_change, exp}`
- Passwords: SHA-256 + 16-byte random hex salt → stored as `salt:hash`
- Roles: `super_admin` (full access), `admin` (can call/edit), `user` (view-only, `canEdit=false`)
- New users: temp password (24h expiry) → welcome email → forced change on first login
- Only `@nickelfox.com` emails accepted for new accounts
- Token stored in browser `sessionStorage`, validated on load via `GET /auth/me`
- `_require_auth` / `_require_super_admin` FastAPI dependencies handle authorization

---

## Email Service (`backend/services/email_service.py`)

- Amazon SES via SMTP — host: `email-smtp.us-east-1.amazonaws.com`, port 587, STARTTLS
- Only used for welcome emails on new user creation
- Requires: `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` in `.env`
- Temp password format: `{First4chars_of_name}@{6randomChars}` e.g. `Shiv@aB3kM9`
- Failure is non-fatal — logs and continues if SMTP not configured

---

## File Parsing (`backend/utils/file_utils.py`)

- **PDF**: PyMuPDF (`fitz.open(stream=content, filetype="pdf")`) — page-by-page text join
- **DOCX**: python-docx (`docx.Document(io.BytesIO(content))`) — paragraph text join
- **Job title extraction**: regex label patterns first → Claude Haiku fallback → first non-empty line

---

## Interview Scoring

| Dimension | Max | Measures |
|-----------|-----|---------|
| `communication` | 35 | Clarity, fluency, structure, professionalism |
| `confidence` | 30 | Directness, assertiveness, absence of hedging |
| `motivation_fit` | 20 | Genuine interest, role understanding |
| `behavioral_quality` | 15 | Quality of situational/example answers |
| **Total** | **100** | |

Verdict options: `Strongly Recommended` / `Recommended` / `Consider` / `Not Recommended`

Combined score (batch table): `resume_score × 0.4 + interview_score × 0.6`

---

## Security

- `.env` in `.gitignore` — **never commit credentials**
- All secrets via `os.getenv()` after `backend/app/config.py` loads
- JWT required for all non-Twilio routes
- Twilio webhooks are unauthenticated (public) — Twilio signs requests but signature validation not implemented; `BASE_URL` keeps them secret by obscurity
- Passwords never stored in plain text
