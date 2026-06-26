from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env", override=True)

import os
import re
import json
import httpx
import anthropic as _anthropic

_claude_key   = os.getenv("CLAUDE_API_KEY")
claude_client = _anthropic.Anthropic(api_key=_claude_key, timeout=60.0) if _claude_key else None
CLAUDE_MODEL  = "claude-haiku-4-5-20251001"


def _claude(system: str, prompt: str) -> str:
    resp = claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,  
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def _strip_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r'^```[a-z]*\n?', '', raw)
        raw = re.sub(r'\n?```$', '', raw.rstrip())
    return raw.strip()


def get_next_question(resume_text: str, jd_text: str, conversation: list[dict], candidate_name: str = None) -> dict:
    name = candidate_name or "there"
    interviewer_turns = [m for m in conversation if m["role"] == "interviewer"]
    n = len(interviewer_turns)

    if n == 0:
        greeting = (
            f"Hi {name}! This is Sarah from the team at NickelFox Technologies — so glad you could make some time today! "
            f"I'd love to start by hearing a bit about you. Could you walk me through your background and what you've been up to recently?"
        )
        return {"next_question": greeting, "is_done": False}

    if n >= 6:
        closing = (
            f"That's all the questions I had for today — honestly, it was such a pleasure speaking with you, {name}! "
            "Our team will review everything and we'll be in touch very soon. "
            "Wishing you a fantastic rest of your day — take care!"
        )
        return {"next_question": closing, "is_done": True}

    if not claude_client:
        fallbacks = [
            "That's really interesting — what specifically draws you to this particular role?",
            "I'd love to hear about a challenge you faced at work and how you handled it.",
            "How do you usually go about building relationships when you join a new team?",
            "What kind of environment or work style really brings out the best in you?",
        ]
        return {"next_question": fallbacks[min(n - 1, len(fallbacks) - 1)], "is_done": False}

    conv_text = "\n".join(
        f"{'Interviewer' if m['role'] == 'interviewer' else 'Candidate'}: {m['content']}"
        for m in conversation
    )

    prompt = f"""You are Sarah, a warm and professional HR recruiter on a phone screening call.
This is turn {n + 1} of a planned 7-turn HR screening interview.

Your goal: assess the candidate's communication clarity, confidence, motivation, and cultural fit.
Do NOT ask deep technical questions.

Candidate resume (brief):
{resume_text[:600]}

Job description (brief):
{jd_text[:400]}

Conversation so far:
{conv_text}

Instructions:
- Write your next spoken line as the interviewer — one short, natural question or acknowledgement + question.
- Build directly on what the candidate just said.
- Keep it warm and conversational (1-2 sentences max).
- Return ONLY your spoken words. No labels, no JSON, no quotation marks."""

    raw = _claude(
        "You are Sarah, a warm and empathetic HR interviewer at NickelFox Technologies. Respond only with your next spoken line — conversational, encouraging, and human. No labels or formatting.",
        prompt,
    )
    return {"next_question": raw.strip(), "is_done": False}


def score_conversation(conversation: list[dict], jd_text: str) -> dict:
    if not conversation:
        return {
            "interview_score":    "N/A",
            "communication":      {"score": 0, "max": 35},
            "confidence":         {"score": 0, "max": 30},
            "motivation_fit":     {"score": 0, "max": 20},
            "behavioral_quality": {"score": 0, "max": 15},
            "verdict":            "No Data",
            "strengths":          [],
            "improvements":       [],
            "summary":            "No conversation data.",
        }
    transcript = "\n\n".join(
        f"{'Interviewer' if m['role'] == 'interviewer' else 'Candidate'}: {m['content']}"
        for m in conversation
    )
    questions = [m["content"] for m in conversation if m["role"] == "interviewer"]
    return score_interview(transcript, questions, jd_text)


def generate_questions(resume_text: str, jd_text: str) -> list[str]:
    if not claude_client:
        return [
            "Could you start by introducing yourself and walking me through your background?",
            "What specifically draws you to this role and company?",
            "Tell me about a time you worked with others on a project — how did you contribute and what was the outcome?",
            "Can you explain how you've used one of your core technical skills in a real or academic project?",
            "The role has some specific technical requirements — can you talk about your familiarity with the key technologies mentioned?",
            "Tell me about a specific project you've worked on — what was a challenge you faced and how did you handle it?",
        ]

    prompt = f"""You are a recruiter conducting a structured phone screening. First, read the resume and determine if the candidate is a FRESHER/INTERN (student, recent graduate, little or no work experience) or EXPERIENCED (has significant work experience).

Then generate exactly 7 questions in this fixed order, adapted to their profile:

Question 1 — Pure Introduction:
Ask the candidate to simply introduce themselves — just who they are and what they do. Keep it open and warm. Do NOT ask about their journey or history here.
- Fresher example: "Could you start by telling me a little about yourself?"
- Experienced example: "Great to connect — could you start by telling me a bit about yourself?"

Question 2 — Background / Journey:
Now ask them to walk through their background in more depth.
- Fresher: Ask about their academic background, what they studied, and what drew them to this field.
- Experienced: Ask them to walk through their career journey and what has brought them to where they are today.

Question 3 — Motivation / Why this role:
Ask why they are interested in this specific role or company. Reference something specific from the JD.

Question 4 — Behavioural:
- Fresher: Ask about a time they collaborated in a team on an academic project, group assignment, or personal project — how they contributed and what the outcome was.
- Experienced: Ask about a notable achievement at work, a difficult situation they navigated, or how they adapted to a significant change. Pick whichever fits the resume best.

Question 5 — Technical (Resume-based):
- Fresher: Ask a concise technical question based on a skill, technology, or concept from their coursework or academic projects. Ask a how/why/what question, not just "tell me about X".
- Experienced: Ask a concise technical question grounded in a specific technology or experience from their work history. Intermediate depth.

Question 6 — Technical (JD-based):
Ask a concise technical question based on a specific requirement or technology from the JOB DESCRIPTION. Test whether they understand the concept, not just the name. Same depth for both profiles.

Question 7 — Project deep-dive:
- Fresher: Pick one specific academic or personal project from their resume (by name). Ask about a challenge they faced, what they built, or what they learned.
- Experienced: Pick one specific work project from their resume (by name). Ask about a technical challenge, how they solved it, or what they would do differently.

Rules:
- Each question must be a single, complete sentence — aim for under 20 words but NEVER cut a question mid-thought; it must always be grammatically complete and make full sense
- No multi-part questions — do not combine two questions into one with "and" or follow-up clauses
- Write in casual, spoken language — as if asking a friend, not writing a formal document
- Do NOT number the questions
- Do NOT mention "fresher" or "experienced" in the questions themselves
- Return a JSON array of exactly 7 question strings. Valid JSON only, no markdown.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}"""

    raw = _claude("You are a recruiter conducting phone screenings. Return only valid JSON.", prompt)
    return json.loads(_strip_json(raw))


def start_twilio_call(phone_number: str, interview_id: str) -> dict:
    from twilio.rest import Client
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    base_url    = os.getenv("BASE_URL", "").rstrip("/")

    if not account_sid or not auth_token or not from_number:
        raise Exception("Twilio credentials missing — set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER in .env")

    digits = re.sub(r"\D", "", phone_number)
    if len(digits) == 10:
        to = f"+91{digits}"
    elif digits.startswith("91") and len(digits) == 12:
        to = f"+{digits}"
    else:
        to = f"+{digits}"

    print(f"[Twilio] Calling {to}, interview_id={interview_id}")
    client = Client(account_sid, auth_token)
    call = client.calls.create(
        to=to,
        from_=from_number,
        url=f"{base_url}/twilio/start/{interview_id}",
        status_callback=f"{base_url}/twilio/status/{interview_id}",
        status_callback_event=["initiated", "ringing", "answered", "completed"],
        timeout=20,
        record=True,
        machine_detection="DetectMessageEnd",
        machine_detection_timeout=30,
        async_amd=True,
        async_amd_status_callback=f"{base_url}/twilio/amd/{interview_id}",
    )
    print(f"[Twilio] Call initiated — SID={call.sid}")
    return {"call_sid": call.sid}


def transcribe_recording(recording_url: str, *, fast: bool = False) -> str:
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        return "[transcription skipped — no GROQ_API_KEY set]"

    auth  = (os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    model = "whisper-large-v3-turbo" if fast else "whisper-large-v3"

    import time as _time
    last_err = None
    audio_resp = None
    for attempt in range(3):
        try:
            audio_resp = httpx.get(
                recording_url, auth=auth, follow_redirects=True, timeout=30
            )
            if audio_resp.status_code == 404 and attempt < 2:
                print(f"[Transcribe] recording not ready (attempt {attempt+1}/3) — retrying")
                _time.sleep(2 ** attempt)
                continue
            audio_resp.raise_for_status()
            last_err = None
            break
        except Exception as e:
            last_err = e
            if attempt < 2:
                print(f"[Transcribe] fetch error (attempt {attempt+1}/3): {e} — retrying")
                _time.sleep(2 ** attempt)
    if last_err:
        raise last_err

    from groq import Groq
    client = Groq(api_key=groq_key)
    result = client.audio.transcriptions.create(
        file=("answer.mp3", audio_resp.content),
        model=model,
        language="hi",
        temperature=0,
        prompt="Interviewer: Tell me about your experience. Candidate:",
    )
    return result.text.strip()


def score_interview(transcript: str, questions: list[str], jd_text: str) -> dict:
    if not claude_client or not transcript.strip():
        return {
            "interview_score":    "N/A",
            "communication":      {"score": 0, "max": 35},
            "confidence":         {"score": 0, "max": 30},
            "motivation_fit":     {"score": 0, "max": 20},
            "behavioral_quality": {"score": 0, "max": 15},
            "verdict":            "No Data",
            "strengths":          [],
            "improvements":       [],
            "summary":            "No transcript available to score.",
        }

    questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])

    prompt = f"""You are an experienced HR recruiter scoring a first-round phone screening interview.

This is an HR screening round — not a technical deep-dive. Score fairly and generously for natural, conversational answers.

Scoring dimensions and anchors:
- communication (0-35): Clarity, fluency, structure, professionalism.
  35 = exceptionally clear and polished | 25-30 = speaks clearly, professional tone | 15-24 = mostly understandable, some gaps | below 15 = hard to follow or very unprofessional
- confidence (0-30): Assertiveness, directness, absence of excessive hedging ("I think maybe", "I'm not sure", "kind of").
  28-30 = very direct and assured | 20-27 = generally confident with minor hedging | 10-19 = noticeable self-doubt | below 10 = very passive or hesitant throughout
- motivation_fit (0-20): Genuine interest in the role, understanding of the position, enthusiasm.
  18-20 = specific reasons, clear understanding of role | 12-17 = shows interest, general awareness | 6-11 = generic answers | below 6 = no apparent motivation or understanding
- behavioral_quality (0-15): Quality of situational/example answers — do they describe real situations with outcomes?
  13-15 = specific examples with clear outcomes | 8-12 = decent examples, outcome implied | 3-7 = vague or generic examples | 0-2 = no examples given

Important scoring rule: A competent, reasonably articulate candidate should score 72-82 overall. Only score below 50 if answers are clearly poor. Give benefit of the doubt for natural speech patterns. Do not penalize for being conversational rather than formal.

Interview Questions:
{questions_text}

Job Description (context):
{jd_text[:800]}

Full Interview Transcript:
{transcript}

Return this exact JSON (no markdown):
{{
  "interview_score": "XX / 100",
  "communication":      {{"score": 0-35, "max": 35}},
  "confidence":         {{"score": 0-30, "max": 30}},
  "motivation_fit":     {{"score": 0-20, "max": 20}},
  "behavioral_quality": {{"score": 0-15, "max": 15}},
  "verdict": "Strongly Recommended | Recommended | Consider | Not Recommended",
  "strengths":    ["strength 1", "strength 2", "strength 3"],
  "improvements": ["area 1", "area 2"],
  "summary": "2-3 sentence overall HR assessment of the candidate's screening performance"
}}"""

    raw = _claude("You are an experienced HR recruiter. Return only valid JSON.", prompt)
    return json.loads(_strip_json(raw))
