"""Generate 10 test resume PDFs for Software Developer role."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

OUT = os.path.dirname(os.path.abspath(__file__))

# ── Job Description ──────────────────────────────────────────────────────────
JD = """Software Developer — NickelFox Technologies

About the Role:
We are looking for a skilled Software Developer to join our growing engineering team. You will design, build, and maintain scalable web applications and APIs. The ideal candidate has strong Python and JavaScript skills, experience with RESTful API design, and a collaborative mindset.

Responsibilities:
• Develop and maintain backend services using Python (FastAPI / Django / Flask)
• Build responsive frontend components using React or Vue.js
• Design and consume RESTful APIs
• Write clean, testable, and well-documented code
• Collaborate using Git and follow CI/CD best practices
• Work with relational databases (PostgreSQL / MySQL)
• Containerize applications using Docker
• Participate in code reviews and agile sprints
• Debug, profile, and optimize application performance

Required Skills:
• 2–5 years of software development experience
• Proficiency in Python (FastAPI, Django, or Flask)
• Proficiency in JavaScript / TypeScript and React or Vue.js
• RESTful API design and integration
• SQL databases — PostgreSQL or MySQL
• Git version control
• Docker and basic DevOps awareness
• Problem-solving and communication skills

Nice to Have:
• Experience with cloud platforms (AWS / GCP / Azure)
• Knowledge of Redis, Celery, or message queues
• Familiarity with CI/CD pipelines (GitHub Actions / Jenkins)
• GraphQL experience

Education:
Bachelor's degree in Computer Science, IT, or a related field (or equivalent experience)
"""

with open(os.path.join(OUT, "job_description_software_developer.txt"), "w") as f:
    f.write(JD)
print("JD written.")

# ── Candidate Data ────────────────────────────────────────────────────────────
CANDIDATES = [
    {
        "name": "Sudarshan Verma",
        "phone": "+91 9827763713",
        "email": "sudarshan.verma@gmail.com",
        "location": "Bhopal, MP",
        "summary": "Backend-focused software developer with 3 years of experience building Python-based REST APIs and database-driven web applications. Comfortable working across the stack using React for frontend tasks.",
        "skills": ["Python (FastAPI, Flask)", "JavaScript / React", "RESTful APIs", "PostgreSQL", "Git", "Docker", "Linux", "SQLAlchemy"],
        "experience": [
            {
                "title": "Software Developer",
                "company": "TechSolve India Pvt. Ltd.",
                "duration": "Jan 2022 – Present (2.5 yrs)",
                "points": [
                    "Built and maintained 12+ REST API endpoints using FastAPI serving 10k+ daily requests.",
                    "Developed React dashboards for internal analytics, reducing reporting time by 40%.",
                    "Managed PostgreSQL schemas, wrote optimized queries and migrations.",
                    "Containerized services with Docker; maintained CI pipeline on GitHub Actions.",
                ]
            },
            {
                "title": "Junior Developer",
                "company": "Webcraft Solutions",
                "duration": "Jul 2021 – Dec 2021 (6 months)",
                "points": [
                    "Assisted senior developers in building Flask-based microservices.",
                    "Wrote unit tests using pytest, achieving 80% coverage on new modules.",
                ]
            }
        ],
        "education": "B.Tech – Computer Science, RGPV Bhopal, 2021",
        "missing": "No cloud (AWS/GCP) or Redis experience",
    },
    {
        "name": "Yankit Sharma",
        "phone": "+91 9213396062",
        "email": "yankit.sharma@outlook.com",
        "location": "Delhi, NCR",
        "summary": "Full-stack developer with 4 years of hands-on experience in Python and JavaScript. Strong in agile teams, REST API development, and delivering production-grade features on tight schedules.",
        "skills": ["Python (Django)", "JavaScript / Vue.js", "REST APIs", "MySQL", "Git", "Docker", "Redis", "Postman"],
        "experience": [
            {
                "title": "Software Engineer",
                "company": "InnovateTech Pvt. Ltd.",
                "duration": "Mar 2021 – Present (3.3 yrs)",
                "points": [
                    "Led development of a multi-tenant Django application serving 500+ enterprise clients.",
                    "Designed RESTful APIs consumed by Vue.js frontend and mobile apps.",
                    "Optimised MySQL queries, reducing average API response time by 35%.",
                    "Used Docker Compose for local and staging environments; wrote Dockerfile best practices guide.",
                ]
            },
            {
                "title": "Associate Developer",
                "company": "DigitalBridge Corp",
                "duration": "Jun 2020 – Feb 2021 (9 months)",
                "points": [
                    "Built CRUD APIs and integrated third-party payment gateways.",
                    "Participated in daily standups, sprint planning, and retrospectives.",
                ]
            }
        ],
        "education": "B.Sc – Information Technology, Delhi University, 2020",
        "missing": "No significant cloud or CI/CD pipeline experience",
    },
    {
        "name": "Anshul Gupta",
        "phone": "+91 8171602029",
        "email": "anshul.gupta@protonmail.com",
        "location": "Meerut, UP",
        "summary": "Python developer specialising in backend API services and database optimisation. 2 years experience with agile teams, Docker-based deployments, and test-driven development.",
        "skills": ["Python (Flask, FastAPI)", "JavaScript", "REST APIs", "PostgreSQL", "Git", "Docker", "pytest", "Celery"],
        "experience": [
            {
                "title": "Python Developer",
                "company": "CloudNest Technologies",
                "duration": "Aug 2022 – Present (2 yrs)",
                "points": [
                    "Developed 8 microservices in FastAPI, each independently containerised and deployed.",
                    "Integrated Celery + Redis for asynchronous task processing of email and report generation.",
                    "Authored comprehensive API documentation using Swagger/OpenAPI.",
                    "Collaborated in 2-week Agile sprints; raised test coverage from 45% to 78%.",
                ]
            },
            {
                "title": "Intern – Software Development",
                "company": "Nexus Infotech",
                "duration": "Jan 2022 – Jul 2022 (7 months)",
                "points": [
                    "Wrote Python scripts for data processing and ETL pipelines.",
                    "Fixed bugs in legacy Flask application and refactored database models.",
                ]
            }
        ],
        "education": "B.Tech – Computer Science, CCS University, 2022",
        "missing": "Limited React/Vue experience; no cloud platform deployment",
    },
    {
        "name": "Abhash Kumar",
        "phone": "+91 9905830494",
        "email": "abhash.kumar@gmail.com",
        "location": "Patna, Bihar",
        "summary": "Versatile software developer with 3.5 years of experience in full-stack web development. Proficient in React and Python, with a track record of shipping features from design to production.",
        "skills": ["Python (FastAPI, Django)", "React / JavaScript", "REST APIs", "PostgreSQL", "Git", "Docker", "TypeScript", "AWS S3"],
        "experience": [
            {
                "title": "Full Stack Developer",
                "company": "Bitwise Solutions",
                "duration": "Feb 2021 – Present (3.5 yrs)",
                "points": [
                    "Built end-to-end features for a SaaS product: React frontend + FastAPI backend.",
                    "Integrated AWS S3 for media storage; reduced storage costs by 25% through lifecycle policies.",
                    "Wrote TypeScript interfaces ensuring type-safe API contracts between frontend and backend.",
                    "Managed database migrations with Alembic; maintained PostgreSQL performance under load.",
                ]
            },
            {
                "title": "Trainee Developer",
                "company": "Horizon IT",
                "duration": "Sep 2020 – Jan 2021 (5 months)",
                "points": [
                    "Assisted in building customer-facing features using Django and Bootstrap.",
                    "Resolved 30+ GitHub issues and participated in weekly code reviews.",
                ]
            }
        ],
        "education": "B.Tech – Computer Science, NIT Patna, 2020",
        "missing": "No CI/CD pipeline ownership; limited Redis/Celery usage",
    },
    {
        "name": "Sunny Rajput",
        "phone": "+91 9929789508",
        "email": "sunny.rajput@yahoo.com",
        "location": "Jaipur, Rajasthan",
        "summary": "Software developer with 2.5 years of experience building web applications using Python and JavaScript. Strong understanding of REST APIs and relational databases. Quick learner with an interest in DevOps.",
        "skills": ["Python (Flask, Django)", "JavaScript / React", "REST APIs", "MySQL", "PostgreSQL", "Git", "Docker", "Linux"],
        "experience": [
            {
                "title": "Software Developer",
                "company": "RajTech Digital",
                "duration": "Apr 2022 – Present (2.2 yrs)",
                "points": [
                    "Developed and maintained RESTful APIs for an e-commerce platform handling 5k daily users.",
                    "Built React components for product listing, cart, and checkout flows.",
                    "Migrated MySQL database to PostgreSQL; improved query performance by 20%.",
                    "Set up Docker environments for consistent dev/staging deployments.",
                ]
            },
            {
                "title": "Web Developer Intern",
                "company": "PixelCraft Labs",
                "duration": "Nov 2021 – Mar 2022 (5 months)",
                "points": [
                    "Developed Flask APIs and integrated them with a React dashboard.",
                    "Managed version control using Git branching strategies.",
                ]
            }
        ],
        "education": "B.E. – Information Technology, RTU Kota, 2021",
        "missing": "No cloud platform experience; no CI/CD pipeline setup",
    },
    {
        "name": "Krish Patel",
        "phone": "+91 9306112553",
        "email": "krish.patel@gmail.com",
        "location": "Ahmedabad, Gujarat",
        "summary": "Detail-oriented Python and JavaScript developer with 3 years of industry experience. Skilled at writing clean, maintainable code and collaborating effectively in remote-first agile teams.",
        "skills": ["Python (FastAPI)", "JavaScript / React", "TypeScript", "REST APIs", "PostgreSQL", "Git", "Docker", "GitHub Actions"],
        "experience": [
            {
                "title": "Backend Developer",
                "company": "Solaris Technologies",
                "duration": "Jun 2021 – Present (3 yrs)",
                "points": [
                    "Designed and built 20+ API endpoints in FastAPI for a fintech application.",
                    "Implemented GitHub Actions CI/CD pipeline; cut deployment time from 45 min to 8 min.",
                    "Enforced code quality with pre-commit hooks, linting (flake8, black), and PR reviews.",
                    "Wrote comprehensive pytest test suites achieving 85% coverage.",
                ]
            },
            {
                "title": "Junior Software Engineer",
                "company": "WebWave India",
                "duration": "Jan 2021 – May 2021 (5 months)",
                "points": [
                    "Developed internal tools using Python scripts and simple React UIs.",
                    "Collaborated with QA team on bug triage and resolution.",
                ]
            }
        ],
        "education": "B.Tech – Computer Engineering, GTU Ahmedabad, 2021",
        "missing": "No cloud deployment experience; limited Redis/queue knowledge",
    },
    {
        "name": "Gautam Singh",
        "phone": "+91 9220173473",
        "email": "gautam.singh@gmail.com",
        "location": "Lucknow, UP",
        "summary": "Software developer with 4+ years of experience across backend and frontend development. Passionate about building scalable Python APIs and modern React UIs with a focus on code quality.",
        "skills": ["Python (Django, FastAPI)", "React / JavaScript", "REST APIs", "PostgreSQL", "MySQL", "Git", "Docker", "AWS EC2"],
        "experience": [
            {
                "title": "Senior Software Developer",
                "company": "LogicLeap Pvt. Ltd.",
                "duration": "Oct 2020 – Present (3.8 yrs)",
                "points": [
                    "Led a 3-member team building a healthcare SaaS platform in Django + React.",
                    "Deployed services on AWS EC2 with Nginx and Gunicorn; achieved 99.7% uptime.",
                    "Designed database schema for multi-clinic patient management system (PostgreSQL).",
                    "Mentored 2 junior developers and conducted biweekly code reviews.",
                ]
            },
            {
                "title": "Web Developer",
                "company": "TechBridge Solutions",
                "duration": "Apr 2020 – Sep 2020 (6 months)",
                "points": [
                    "Built REST APIs for a logistics tracking application using Flask.",
                    "Wrote frontend features using vanilla JavaScript and jQuery.",
                ]
            }
        ],
        "education": "B.Tech – Computer Science, AKTU Lucknow, 2020",
        "missing": "No CI/CD pipeline experience; limited TypeScript usage",
    },
    {
        "name": "Tanishka Mehta",
        "phone": "+91 9069115019",
        "email": "tanishka.mehta@gmail.com",
        "location": "Pune, Maharashtra",
        "summary": "Software developer with 2 years of experience in Python backend development and React frontend. Strong communicator and quick learner, with hands-on experience delivering features in agile environments.",
        "skills": ["Python (Flask, FastAPI)", "JavaScript / React", "REST APIs", "PostgreSQL", "Git", "Docker", "pytest", "Postman"],
        "experience": [
            {
                "title": "Software Developer",
                "company": "NexGen Softwares",
                "duration": "Jul 2022 – Present (2 yrs)",
                "points": [
                    "Developed user authentication, role-based access, and session management modules in FastAPI.",
                    "Built React components for a data visualisation dashboard used by 200+ clients.",
                    "Wrote integration tests covering API endpoints; reduced regression bugs by 30%.",
                    "Used Docker Compose to standardise local development environments across 5-member team.",
                ]
            },
            {
                "title": "Software Trainee",
                "company": "Sparkle IT Solutions",
                "duration": "Jan 2022 – Jun 2022 (6 months)",
                "points": [
                    "Assisted in building Flask APIs and connecting them to a React admin panel.",
                    "Wrote documentation for internal API endpoints and database schema.",
                ]
            }
        ],
        "education": "B.E. – Computer Engineering, Pune University, 2022",
        "missing": "No cloud or CI/CD pipeline; limited Redis usage",
    },
    {
        "name": "Amol Thakur",
        "phone": "+91 9897657426",
        "email": "amol.thakur@protonmail.com",
        "location": "Dehradun, Uttarakhand",
        "summary": "Full-stack software developer with 3 years of experience in Python and React. Focused on writing clean, well-tested code and building APIs that scale. Comfortable with containerised deployments.",
        "skills": ["Python (FastAPI, Django)", "React / TypeScript", "REST APIs", "PostgreSQL", "Git", "Docker", "Redis", "CI/CD"],
        "experience": [
            {
                "title": "Software Developer",
                "company": "AlpineCode Technologies",
                "duration": "May 2021 – Present (3.1 yrs)",
                "points": [
                    "Built a multi-service backend in FastAPI with JWT authentication and RBAC.",
                    "Developed React + TypeScript frontend consuming internal REST APIs.",
                    "Set up Docker-based CI/CD pipeline reducing deployment cycles from 1 day to 2 hours.",
                    "Implemented Redis caching layer; improved response times by 50% on heavy endpoints.",
                ]
            },
            {
                "title": "Junior Developer",
                "company": "HillSoft Labs",
                "duration": "Dec 2020 – Apr 2021 (5 months)",
                "points": [
                    "Developed CRUD APIs in Flask and wrote corresponding pytest unit tests.",
                    "Helped migrate legacy PHP scripts to Python backend services.",
                ]
            }
        ],
        "education": "B.Tech – Computer Science, HNB Garhwal University, 2020",
        "missing": "No formal cloud (AWS/GCP/Azure) deployment experience",
    },
    {
        "name": "Jaya Mishra",
        "phone": "+91 8957155545",
        "email": "jaya.mishra@gmail.com",
        "location": "Varanasi, UP",
        "summary": "Software developer with 2.5 years of experience building Python APIs and JavaScript interfaces. Strong in database design, testing, and delivering well-documented features in cross-functional teams.",
        "skills": ["Python (Django, Flask)", "JavaScript / React", "REST APIs", "MySQL", "PostgreSQL", "Git", "Docker", "Linux"],
        "experience": [
            {
                "title": "Python Developer",
                "company": "KashiTech Solutions",
                "duration": "Mar 2022 – Present (2.3 yrs)",
                "points": [
                    "Developed Django-based REST APIs for an LMS serving 3,000+ students.",
                    "Integrated Razorpay payment gateway and automated invoice generation.",
                    "Built interactive React components for course browsing and progress tracking.",
                    "Used Docker for consistent staging deployments; introduced Git flow branching.",
                ]
            },
            {
                "title": "Web Development Intern",
                "company": "DigitalKashi",
                "duration": "Sep 2021 – Feb 2022 (6 months)",
                "points": [
                    "Built REST API endpoints in Flask and tested them using Postman.",
                    "Created basic HTML/CSS/JS pages and connected them to backend APIs.",
                ]
            }
        ],
        "education": "B.Tech – Computer Science, BHU Varanasi, 2021",
        "missing": "No cloud or CI/CD pipeline; no Redis/Celery experience",
    },
]

# ── PDF Builder ───────────────────────────────────────────────────────────────
PRIMARY   = colors.HexColor("#3730a3")   # indigo
LIGHT_BG  = colors.HexColor("#eef2ff")
DARK_TEXT = colors.HexColor("#1e1b4b")
MID_TEXT  = colors.HexColor("#374151")
SUB_TEXT  = colors.HexColor("#6b7280")

def build_resume(c, filepath):
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=16*mm,  bottomMargin=14*mm,
    )
    W = A4[0] - 36*mm
    story = []

    # ── Name header ──
    story.append(Paragraph(
        f'<font color="#3730a3" size="22"><b>{c["name"]}</b></font>',
        ParagraphStyle("name", alignment=TA_LEFT, spaceAfter=2)
    ))
    story.append(Paragraph(
        f'<font color="#6b7280" size="9">{c["location"]}  |  {c["phone"]}  |  {c["email"]}</font>',
        ParagraphStyle("contact", alignment=TA_LEFT, spaceAfter=4)
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=8))

    def section(title):
        story.append(Paragraph(
            f'<font color="#3730a3" size="10"><b>{title.upper()}</b></font>',
            ParagraphStyle("sec", spaceBefore=10, spaceAfter=4)
        ))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#c7d2fe"), spaceAfter=5))

    # ── Summary ──
    section("Professional Summary")
    story.append(Paragraph(
        f'<font color="#374151" size="9.5">{c["summary"]}</font>',
        ParagraphStyle("body", leading=14, spaceAfter=4)
    ))

    # ── Skills ──
    section("Technical Skills")
    skills_text = "  •  ".join(c["skills"])
    story.append(Paragraph(
        f'<font color="#374151" size="9.5">{skills_text}</font>',
        ParagraphStyle("skills", leading=14, spaceAfter=4)
    ))

    # ── Experience ──
    section("Work Experience")
    for exp in c["experience"]:
        story.append(Paragraph(
            f'<font color="#1e1b4b" size="10"><b>{exp["title"]}</b></font>'
            f'<font color="#6b7280" size="9">  —  {exp["company"]}</font>',
            ParagraphStyle("jobtitle", spaceBefore=4, spaceAfter=1)
        ))
        story.append(Paragraph(
            f'<font color="#9ca3af" size="8.5"><i>{exp["duration"]}</i></font>',
            ParagraphStyle("duration", spaceAfter=3)
        ))
        for pt in exp["points"]:
            story.append(Paragraph(
                f'<font color="#374151" size="9">• {pt}</font>',
                ParagraphStyle("bullet", leftIndent=10, leading=13, spaceAfter=2)
            ))

    # ── Education ──
    section("Education")
    story.append(Paragraph(
        f'<font color="#374151" size="9.5">{c["education"]}</font>',
        ParagraphStyle("edu", leading=13)
    ))

    doc.build(story)
    print(f"  OK  {filepath}")


print("\nGenerating resumes...")
for cand in CANDIDATES:
    fname = cand["name"].replace(" ", "_") + ".pdf"
    build_resume(cand, os.path.join(OUT, fname))

print(f"\nDone — {len(CANDIDATES)} PDFs + 1 JD saved to: {OUT}")
