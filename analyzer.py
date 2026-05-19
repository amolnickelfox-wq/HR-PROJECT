import re
import os
import json
import hashlib
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Claude client setup
# ─────────────────────────────────────────────
try:
    import anthropic as _anthropic
    _key = os.getenv("CLAUDE_API_KEY")
    claude_client = _anthropic.Anthropic(api_key=_key, timeout=60.0) if _key else None
except ImportError:
    claude_client = None

CLAUDE_MODEL = "claude-sonnet-4-6"


def _claude(system: str, prompt: str) -> str:
    resp = claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        temperature=0,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


# ─────────────────────────────────────────────
# Skills Knowledge Base (used as fallback)
# ─────────────────────────────────────────────
SKILLS_DB = [
    # Programming
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "php", "scala", "kotlin", "swift", "r", "matlab", "bash", "shell",
    # ML / AI
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "reinforcement learning", "neural networks", "transformers",
    "bert", "gpt", "llm", "rag", "fine-tuning", "transfer learning",
    # Frameworks & Libraries
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "xgboost",
    "lightgbm", "hugging face", "spacy", "nltk", "opencv", "fastai",
    "sentence transformers", "faiss", "langchain",
    # Web / API
    "fastapi", "flask", "django", "react", "angular", "vue", "node.js",
    "express", "spring boot", "rest api", "graphql",
    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "jenkins",
    "ci/cd", "terraform", "ansible", "linux",
    # Databases
    "sql", "mysql", "postgresql", "mongodb", "redis", "sqlite",
    "elasticsearch", "cassandra", "nosql",
    # Data & Tools
    "git", "airflow", "kafka", "spark", "hadoop", "tableau", "power bi",
    "pandas", "numpy", "matplotlib", "seaborn", "jupyter",
    # Methodologies
    "microservices", "agile", "scrum", "devops", "mlops",
]


# ─────────────────────────────────────────────
# Regex Extraction Helpers (fallback)
# ─────────────────────────────────────────────

def extract_email(text: str) -> str | None:
    match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text)
    return match.group(0) if match else None


def validate_email(email: str | None) -> bool:
    if not email:
        return False
    return bool(re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', email))


def extract_phone(text: str) -> str | None:
    for pat in [r'\+?\d[\d\s\-().]{8,}\d']:
        for m in re.finditer(pat, text):
            digits = re.sub(r'\D', '', m.group(0))
            if 10 <= len(digits) <= 15:
                return m.group(0).strip()
    return None


def validate_phone(phone: str | None) -> bool:
    if not phone:
        return False
    digits = re.sub(r'\D', '', phone)
    return 10 <= len(digits) <= 15


def extract_name(text: str) -> str | None:
    skip_kw = {'resume', 'cv', 'curriculum', 'vitae', 'profile', 'summary',
               'skills', 'experience', 'education', 'contact'}
    for line in text.strip().splitlines()[:5]:
        cleaned = re.sub(r'[^\w\s]', '', line).strip()
        words = cleaned.split()
        if 2 <= len(words) <= 5 and not (set(w.lower() for w in words) & skip_kw):
            if all(w[0].isupper() for w in words if w):
                return cleaned
    return None


def extract_skills(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for skill in SKILLS_DB:
        pattern = r'(?<!\w)' + re.escape(skill) + r'(?!\w)'
        if re.search(pattern, text_lower):
            found.append(skill.title() if len(skill) > 3 else skill.upper())
    return list(dict.fromkeys(found))


def calculate_experience_years(text: str) -> str | None:
    month_map = {m: i+1 for i, m in enumerate(
        ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'])}
    now = datetime.now()
    total_months = 0
    p1 = (r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*'
          r'\s+(\d{4})\s*[–\-—]+\s*'
          r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{4})')
    p2 = (r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*'
          r'\s+(\d{4})\s*[–\-—]+\s*(present|current|now)')
    tl = text.lower()
    for m in re.finditer(p1, tl):
        s = month_map.get(m.group(1)[:3], 1), int(m.group(2))
        e = month_map.get(m.group(3)[:3], 1), int(m.group(4))
        total_months += max(0, (e[1]-s[1])*12 + (e[0]-s[0]))
    for m in re.finditer(p2, tl):
        s = month_map.get(m.group(1)[:3], 1), int(m.group(2))
        total_months += max(0, (now.year-s[1])*12 + (now.month-s[0]))
    if total_months:
        return f"~{total_months/12:.1f} years"
    m = re.search(r'(\d+)\+?\s*years?\s*(of\s*)?(experience|exp)', tl)
    if m:
        return f"{m.group(1)}+ years"
    return None


def extract_education(text: str) -> list[str]:
    edu_kw = ['b.tech','btech','b.e','be ','m.tech','mtech','mba',
              'b.sc','bsc','m.sc','msc','bachelor','master','phd',
              'ph.d','bca','mca','diploma','b.com']
    lines = text.splitlines()
    result = []
    for i, line in enumerate(lines):
        if any(kw in line.lower() for kw in edu_kw):
            entry = line.strip()
            if i+1 < len(lines):
                nxt = lines[i+1].strip()
                if nxt and not any(k in nxt.lower() for k in ['skill','experience','project','certification']):
                    entry += f"  |  {nxt}"
            result.append(entry)
    return result or None


def extract_projects(text: str) -> list[str]:
    titles = re.findall(r'\*\*([^*\n]{5,60})\*\*', text)
    section_kw = {'experience','skills','education','summary','certification',
                  'work','professional','contact','tool','framework'}
    return [t.strip() for t in titles
            if not any(k in t.lower() for k in section_kw)] or None


def extract_roles(text: str) -> list[str]:
    roles = []
    pattern = r'\*\*([A-Z][^\n*]{5,60})\*\*\s*\n([^\n]+\|[^\n]+)'
    for m in re.finditer(pattern, text):
        roles.append(f"{m.group(1).strip()}  —  {m.group(2).strip()}")
    return roles or None


# ─────────────────────────────────────────────
# Regex Scoring Helpers (fallback)
# ─────────────────────────────────────────────

def _exp_numeric(exp_str: str | None) -> float:
    if not exp_str:
        return 0.0
    m = re.search(r'(\d+\.?\d*)', exp_str)
    return float(m.group(1)) if m else 0.0


def score_skills(resume_skills, jd_skills):
    rl = [s.lower() for s in resume_skills]
    jl = [s.lower() for s in jd_skills]
    matching_jd, missing_jd = [], []
    for js in jl:
        hit = any(js in rs or rs in js for rs in rl)
        (matching_jd if hit else missing_jd).append(js)
    skill_pct = len(matching_jd) / len(jl) if jl else 0.5
    raw = round(skill_pct * 40)
    matching_out = []
    for m in matching_jd:
        for rs in resume_skills:
            if m in rs.lower() or rs.lower() in m:
                matching_out.append(rs)
                break
        else:
            matching_out.append(m.title())
    return raw, list(dict.fromkeys(matching_out)), missing_jd


def score_experience(exp_str, jd_text):
    candidate = _exp_numeric(exp_str)
    m = re.search(r'(\d+)\s*[–\-—to]+\s*(\d+)\s*years?', jd_text.lower())
    if not m:
        return 22
    lo, hi = int(m.group(1)), int(m.group(2))
    if lo <= candidate <= hi:
        return 30
    if candidate > hi:
        return 25
    if candidate >= lo - 1:
        return 18
    return 8


def score_projects(resume_text, jd_text):
    keywords = ['recommendation','nlp','classification','detection','prediction',
                'chatbot','summarization','sentiment','ocr','generation','search',
                'ranking','api','model','pipeline']
    jl = jd_text.lower()
    rl = resume_text.lower()
    jd_kw = [k for k in keywords if k in jl]
    if not jd_kw:
        return 14
    hits = sum(1 for k in jd_kw if k in rl)
    return round((hits / len(jd_kw)) * 20)


def score_education(resume_text):
    tl = resume_text.lower()
    if any(k in tl for k in ['b.tech','btech','bachelor','master','m.tech','mtech','phd','mca','bca']):
        if any(k in tl for k in ['computer science','information technology','software','data science',
                                  'electronics','mathematics','statistics']):
            return 10
        return 7
    return 3


def get_experience_fit(candidate_exp, jd_text):
    m = re.search(r'(\d+)\s*[–\-—to]+\s*(\d+)\s*years?', jd_text.lower())
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if candidate_exp >= lo:
            return "Good"
        if candidate_exp >= lo - 1:
            return "Average"
        return "Poor"
    if candidate_exp >= 1:
        return "Good"
    return "Average"


def generate_reason(name, score, matching, missing, fit, exp):
    strength = "strong" if score >= 85 else ("good" if score >= 70 else "partial")
    verdict  = "highly recommended" if score >= 85 else ("recommended" if score >= 70 else "consider with reservations")
    m_str = ", ".join(matching[:4]) if matching else "relevant skills"
    x_str = ", ".join(missing[:3])  if missing  else "none significant"
    return (
        f"{name or 'The candidate'} shows a {strength} match with core skills "
        f"including {m_str}. "
        f"Experience fit is {fit.lower()} ({exp or 'N/A'} of experience). "
        f"Minor gaps: {x_str}. Overall verdict: {verdict}."
    )


# ─────────────────────────────────────────────
# Grok-powered functions
# ─────────────────────────────────────────────

def _strip_markdown_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r'^```[a-z]*\n?', '', raw)
        raw = re.sub(r'\n?```$', '', raw.rstrip())
    return raw.strip()


def _grok_parse(resume_text: str) -> dict:
    prompt = f"""Parse the resume below and return a JSON object with exactly these keys:
- name: full name string or null
- email: email string or null
- phone: phone number string or null
- skills: array of technical skill strings (be thorough)
- experience_years: total experience like "~3.5 years" or null
- education: array of education entry strings or null
- projects: array of project name strings or null
- roles: array of strings like "Job Title  —  Company | Start – End" or null

Return valid JSON only, no markdown, no extra text.

RESUME:
{resume_text}"""

    raw = _claude("You are an expert resume parser. Return only valid JSON.", prompt)
    return json.loads(_strip_markdown_json(raw))


def _extract_jd_skills(jd_text: str) -> list[str]:
    """Extract required skills from JD using Claude for accuracy."""
    prompt = f"""List every technical skill, tool, language, or framework required or preferred in this job description.
Return a JSON array of lowercase strings only. No markdown, no extra text.

JOB DESCRIPTION:
{jd_text}"""
    raw = _claude("You are a technical recruiter. Return only a valid JSON array of skill strings.", prompt)
    return json.loads(_strip_markdown_json(raw))


def _grok_analyze(resume_text: str, jd_text: str) -> dict:
    # Step 1: Claude extracts facts (no scoring — just reading)
    parsed = _grok_parse(resume_text)

    # Step 2: Claude extracts required skills from JD
    try:
        jd_skills = _extract_jd_skills(jd_text)
    except Exception:
        jd_skills = extract_skills(jd_text)

    resume_skills = parsed.get("skills") or []

    # Step 3: Fixed Python formulas — same rules for every resume
    s_skill, matching_skills, missing_skills = score_skills(resume_skills, jd_skills)
    exp_years = parsed.get("experience_years")
    s_exp  = score_experience(exp_years, jd_text)
    s_proj = score_projects(resume_text, jd_text)
    s_edu  = score_education(resume_text)
    total  = min(100, s_skill + s_exp + s_proj + s_edu)

    candidate_exp = _exp_numeric(exp_years)
    exp_fit = get_experience_fit(candidate_exp, jd_text)
    reason  = generate_reason(
        parsed.get("name"), total, matching_skills, missing_skills, exp_fit, exp_years
    )

    email_ok = validate_email(parsed.get("email"))
    phone_ok = validate_phone(parsed.get("phone"))

    return {
        "name":             parsed.get("name"),
        "email":            parsed.get("email") if email_ok else None,
        "phone":            parsed.get("phone") if phone_ok else None,
        "skills":           resume_skills,
        "experience_years": exp_years,
        "match_score":      f"{total} / 100",
        "matching_skills":  matching_skills,
        "missing_skills":   missing_skills,
        "experience_fit":   exp_fit,
        "reason":           reason,
        "education":        parsed.get("education"),
        "projects":         parsed.get("projects"),
        "roles":            parsed.get("roles"),
        "email_valid":      email_ok,
        "phone_valid":      phone_ok,
        "score_breakdown": {
            "skill_match":          {"score": s_skill, "max": 40, "weight": "40%"},
            "experience_relevance": {"score": s_exp,   "max": 30, "weight": "30%"},
            "project_relevance":    {"score": s_proj,  "max": 20, "weight": "20%"},
            "education":            {"score": s_edu,   "max": 10, "weight": "10%"},
        },
    }


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def parse_resume(resume_text: str) -> dict:
    if claude_client:
        try:
            return _grok_parse(resume_text)
        except Exception as e:
            print(f"[Grok parse fallback] {e}")

    # Regex fallback
    return {
        "name":             extract_name(resume_text),
        "email":            extract_email(resume_text),
        "phone":            extract_phone(resume_text),
        "skills":           extract_skills(resume_text),
        "experience_years": calculate_experience_years(resume_text),
        "education":        extract_education(resume_text),
        "projects":         extract_projects(resume_text),
        "roles":            extract_roles(resume_text),
    }


_analyze_cache: dict = {}


def analyze(resume_text: str, jd_text: str) -> dict:
    cache_key = hashlib.md5((resume_text + jd_text).encode()).hexdigest()
    if cache_key in _analyze_cache:
        print(f"[Analyzer] cache hit {cache_key[:8]}")
        return _analyze_cache[cache_key]

    if claude_client:
        try:
            result = _grok_analyze(resume_text, jd_text)
            _analyze_cache[cache_key] = result
            return result
        except Exception as e:
            print(f"[Grok analyze fallback] {e}")

    # Regex fallback
    parsed = parse_resume(resume_text)
    jd_skills     = extract_skills(jd_text)
    resume_skills = parsed["skills"]
    exp_years     = parsed["experience_years"]
    candidate_exp = _exp_numeric(exp_years)

    s_skill, matching_skills, missing_skills = score_skills(resume_skills, jd_skills)
    s_exp  = score_experience(exp_years, jd_text)
    s_proj = score_projects(resume_text, jd_text)
    s_edu  = score_education(resume_text)
    total  = min(100, s_skill + s_exp + s_proj + s_edu)

    exp_fit = get_experience_fit(candidate_exp, jd_text)
    reason  = generate_reason(
        parsed["name"], total, matching_skills, missing_skills, exp_fit, exp_years
    )
    email_ok = validate_email(parsed["email"])
    phone_ok = validate_phone(parsed["phone"])

    return {
        "name":             parsed["name"],
        "email":            parsed["email"] if email_ok else None,
        "phone":            parsed["phone"] if phone_ok else None,
        "skills":           resume_skills,
        "experience_years": exp_years,
        "match_score":      f"{total} / 100",
        "matching_skills":  matching_skills,
        "missing_skills":   missing_skills,
        "experience_fit":   exp_fit,
        "reason":           reason,
        "education":        parsed["education"],
        "projects":         parsed["projects"],
        "roles":            parsed["roles"],
        "email_valid":      email_ok,
        "phone_valid":      phone_ok,
        "score_breakdown": {
            "skill_match":          {"score": s_skill, "max": 40, "weight": "40%"},
            "experience_relevance": {"score": s_exp,   "max": 30, "weight": "30%"},
            "project_relevance":    {"score": s_proj,  "max": 20, "weight": "20%"},
            "education":            {"score": s_edu,   "max": 10, "weight": "10%"},
        },
    }
