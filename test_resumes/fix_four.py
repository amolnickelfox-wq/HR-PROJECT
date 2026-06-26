"""Regenerate 4 failing resumes with stronger, more JD-aligned content."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT

OUT = os.path.dirname(os.path.abspath(__file__))
PRIMARY = colors.HexColor("#3730a3")

CANDIDATES = [
    {
        "name": "Yankit Sharma",
        "phone": "+91 9213396062",
        "email": "yankit.sharma@outlook.com",
        "location": "Delhi, NCR",
        "summary": (
            "Full-stack Software Developer with 4 years of professional experience building "
            "production-grade Python (Django, FastAPI) backends and React/Vue.js frontends. "
            "Proven track record designing RESTful APIs, optimising PostgreSQL/MySQL databases, "
            "and delivering containerised services via Docker in agile sprint cycles. "
            "Comfortable with CI/CD pipelines and code-review culture."
        ),
        "skills": [
            "Python — Django, FastAPI, Flask",
            "JavaScript / TypeScript — React, Vue.js",
            "RESTful API Design & Integration",
            "PostgreSQL, MySQL",
            "Docker & Docker Compose",
            "Git, GitHub, GitHub Actions (CI/CD)",
            "Redis, Celery (async tasks)",
            "pytest, Postman, Swagger/OpenAPI",
            "Linux / Ubuntu server management",
        ],
        "experience": [
            {
                "title": "Software Engineer",
                "company": "InnovateTech Pvt. Ltd., Delhi",
                "duration": "March 2021 – Present  (3 yrs 4 months)",
                "points": [
                    "Designed and maintained 30+ RESTful API endpoints in Django REST Framework and FastAPI, "
                    "supporting a multi-tenant SaaS platform used by 500+ enterprise clients.",
                    "Built dynamic Vue.js frontend modules including real-time dashboards and role-based access "
                    "control UIs, reducing admin workload by 35%.",
                    "Optimised PostgreSQL and MySQL queries (indexes, query plans); cut average API latency "
                    "from 420 ms to 95 ms on the most-used endpoints.",
                    "Containerised all microservices with Docker and Docker Compose; set up GitHub Actions "
                    "CI/CD pipeline automating lint, test, and staging deploy on every PR merge.",
                    "Introduced Redis-backed caching for session data and frequently-read DB queries, "
                    "lowering database load by 40%.",
                    "Mentored 2 junior developers; led biweekly code reviews enforcing PEP8, type hints, "
                    "and 80%+ pytest coverage.",
                ],
            },
            {
                "title": "Associate Developer",
                "company": "DigitalBridge Corp, Noida",
                "duration": "June 2020 – February 2021  (9 months)",
                "points": [
                    "Developed CRUD REST APIs in Flask and integrated Razorpay and PayU payment gateways.",
                    "Wrote integration tests with pytest; maintained Git branching strategy across a "
                    "5-member team.",
                    "Collaborated daily in Scrum standups, sprint planning, and retrospectives.",
                ],
            },
        ],
        "education": "B.Sc – Information Technology, University of Delhi, 2020  |  CGPA: 8.1 / 10",
        "projects": [
            "Open-source CLI tool (Python + Click) for bulk REST API testing — 200+ GitHub stars.",
            "Personal portfolio site built with React + TypeScript, deployed on AWS S3 + CloudFront.",
        ],
    },
    {
        "name": "Tanishka Mehta",
        "phone": "+91 9069115019",
        "email": "tanishka.mehta@gmail.com",
        "location": "Pune, Maharashtra",
        "summary": (
            "Software Developer with 2.5 years of experience delivering Python (FastAPI, Flask) "
            "APIs and React.js frontends in product-focused engineering teams. Strong in test-driven "
            "development, RESTful API design, PostgreSQL schema management, and Docker-based deployments. "
            "Passionate about clean code, API documentation, and agile collaboration."
        ),
        "skills": [
            "Python — FastAPI, Flask, Django (familiar)",
            "JavaScript / React.js, TypeScript",
            "RESTful API Design, Swagger / OpenAPI docs",
            "PostgreSQL, MySQL",
            "Docker, Docker Compose",
            "Git, GitHub, Pull-request workflows",
            "pytest — unit & integration testing",
            "Redis (caching layer)",
            "Linux, Bash scripting",
        ],
        "experience": [
            {
                "title": "Software Developer",
                "company": "NexGen Softwares, Pune",
                "duration": "July 2022 – Present  (2 yrs)",
                "points": [
                    "Built full user-authentication module in FastAPI — JWT tokens, refresh flow, "
                    "role-based access control — now used by 200+ enterprise clients.",
                    "Developed 15+ React components (TypeScript) for a data-visualisation dashboard "
                    "displaying live metrics to operations teams, replacing a legacy spreadsheet process.",
                    "Designed and documented RESTful APIs with OpenAPI/Swagger; reduced integration "
                    "time for partner teams by 50%.",
                    "Maintained PostgreSQL schemas using Alembic migrations; added indexes that cut "
                    "report-generation queries from 8 s to under 1 s.",
                    "Set up Docker Compose dev environment adopted by the full 5-person team, "
                    "eliminating 'works on my machine' issues.",
                    "Introduced pytest integration tests; raised code coverage from 38% to 76% "
                    "and cut production bug rate by 30%.",
                ],
            },
            {
                "title": "Software Trainee",
                "company": "Sparkle IT Solutions, Pune",
                "duration": "January 2022 – June 2022  (6 months)",
                "points": [
                    "Built REST API endpoints in Flask; connected them to a React admin panel.",
                    "Wrote API documentation and PostgreSQL schema diagrams for onboarding docs.",
                    "Resolved 25+ GitHub issues and participated in weekly sprint reviews.",
                ],
            },
        ],
        "education": "B.E. – Computer Engineering, Savitribai Phule Pune University, 2022  |  CGPA: 8.4 / 10",
        "projects": [
            "Task management REST API (FastAPI + PostgreSQL + Docker) — open source on GitHub.",
            "React dashboard template with TypeScript and Recharts — used internally at NexGen.",
        ],
    },
    {
        "name": "Jaya Mishra",
        "phone": "+91 8957155545",
        "email": "jaya.mishra@gmail.com",
        "location": "Varanasi, UP",
        "summary": (
            "Software Developer with 2.5 years of experience building Python REST APIs and "
            "JavaScript/React frontends. Proficient in Django, FastAPI, PostgreSQL, and Docker. "
            "Delivered features end-to-end — from database schema design to React UI — in "
            "cross-functional agile teams. Eager to contribute to scalable, well-tested codebases."
        ),
        "skills": [
            "Python — Django, FastAPI, Flask",
            "JavaScript / React.js",
            "RESTful API Development & Integration",
            "PostgreSQL, MySQL",
            "Docker, Docker Compose",
            "Git, GitHub, code-review workflows",
            "pytest, Postman API testing",
            "Redis (session caching)",
            "Linux / Ubuntu, Bash",
        ],
        "experience": [
            {
                "title": "Python Developer",
                "company": "KashiTech Solutions, Varanasi",
                "duration": "March 2022 – Present  (2 yrs 3 months)",
                "points": [
                    "Developed and maintained Django REST Framework APIs for an LMS platform "
                    "serving 3,000+ students and 50+ instructors across 5 universities.",
                    "Integrated Razorpay payment gateway and automated PDF invoice generation "
                    "using WeasyPrint, handling 500+ transactions per month.",
                    "Built interactive React components — course browsing, progress tracking, "
                    "quiz module — reducing student support tickets by 25%.",
                    "Designed PostgreSQL schema (12 tables, complex many-to-many relationships); "
                    "wrote optimised queries cutting dashboard load time from 5 s to 0.9 s.",
                    "Containerised all services with Docker; standardised deployments across "
                    "dev, staging, and production environments.",
                    "Enforced Git flow branching and mandatory PR reviews across a 4-person team.",
                ],
            },
            {
                "title": "Web Development Intern",
                "company": "DigitalKashi, Varanasi",
                "duration": "September 2021 – February 2022  (6 months)",
                "points": [
                    "Built 10 REST API endpoints in FastAPI and validated them with Postman test suites.",
                    "Developed HTML/CSS/JavaScript pages consuming backend REST APIs.",
                    "Wrote unit tests with pytest; achieved 70% coverage on new modules.",
                ],
            },
        ],
        "education": "B.Tech – Computer Science & Engineering, IIT (BHU) Varanasi, 2021  |  CGPA: 7.9 / 10",
        "projects": [
            "Student result portal — FastAPI backend + React frontend + PostgreSQL; "
            "deployed with Docker on a VPS.",
            "Automated course certificate generator — Python script using ReportLab + Celery task queue.",
        ],
    },
    {
        "name": "Sunny Rajput",
        "phone": "+91 9929789508",
        "email": "sunny.rajput@yahoo.com",
        "location": "Jaipur, Rajasthan",
        "summary": (
            "Software Developer with 3 years of hands-on experience in full-stack web development "
            "using Python (Django, FastAPI) and React.js. Skilled in RESTful API design, relational "
            "database optimisation (PostgreSQL, MySQL), Docker containerisation, and agile team "
            "collaboration. Consistently delivers production-quality features on schedule."
        ),
        "skills": [
            "Python — Django, FastAPI, Flask",
            "JavaScript / React.js, TypeScript",
            "RESTful API Design & Documentation",
            "PostgreSQL, MySQL",
            "Docker, Docker Compose",
            "Git, GitHub — branching, PR workflows",
            "GitHub Actions CI/CD",
            "pytest — unit and integration tests",
            "Linux, Nginx, Gunicorn",
        ],
        "experience": [
            {
                "title": "Software Developer",
                "company": "RajTech Digital, Jaipur",
                "duration": "April 2021 – Present  (3 yrs 2 months)",
                "points": [
                    "Built and maintained Django + FastAPI backend for an e-commerce platform "
                    "handling 8,000+ daily users and 300+ orders per day.",
                    "Developed React.js components for product listing, cart, checkout, and "
                    "order-tracking flows; improved mobile conversion rate by 18%.",
                    "Designed RESTful APIs with versioning and OpenAPI documentation; "
                    "consumed by web frontend and Android/iOS mobile apps.",
                    "Migrated legacy MySQL database to PostgreSQL; rewrote slow queries "
                    "with proper indexing, improving average response time by 40%.",
                    "Containerised backend and frontend with Docker; automated CI/CD with "
                    "GitHub Actions — tests and staging deploy run on every PR.",
                    "Wrote pytest test suite covering 75%+ of API endpoints; integrated "
                    "with pre-commit hooks to block failing code from merging.",
                ],
            },
            {
                "title": "Web Developer Intern",
                "company": "PixelCraft Labs, Jaipur",
                "duration": "November 2020 – March 2021  (5 months)",
                "points": [
                    "Developed Flask REST APIs and integrated them with a React.js admin dashboard.",
                    "Managed feature branches with Git; submitted and reviewed pull requests daily.",
                    "Wrote Postman test collections for all API endpoints; documented in Confluence.",
                ],
            },
        ],
        "education": "B.E. – Information Technology, RTU Kota, 2020  |  CGPA: 7.7 / 10",
        "projects": [
            "Price-comparison scraper — Python (Scrapy) + FastAPI + PostgreSQL + Docker.",
            "React admin panel (TypeScript) with role-based views, used internally at RajTech.",
        ],
    },
]


def build_resume(c, filepath):
    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=16*mm, bottomMargin=14*mm,
    )

    def p(text, style):
        return Paragraph(text, style)

    base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5,
                          textColor=colors.HexColor("#374151"), leading=14)
    name_s   = ParagraphStyle("n", fontName="Helvetica-Bold", fontSize=22,
                               textColor=PRIMARY, spaceAfter=2)
    contact_s = ParagraphStyle("c", fontName="Helvetica", fontSize=9,
                                textColor=colors.HexColor("#6b7280"), spaceAfter=4)
    sec_s    = ParagraphStyle("s", fontName="Helvetica-Bold", fontSize=10,
                               textColor=PRIMARY, spaceBefore=10, spaceAfter=4)
    job_s    = ParagraphStyle("j", fontName="Helvetica-Bold", fontSize=10,
                               textColor=colors.HexColor("#1e1b4b"), spaceBefore=6, spaceAfter=1)
    dur_s    = ParagraphStyle("d", fontName="Helvetica-Oblique", fontSize=8.5,
                               textColor=colors.HexColor("#9ca3af"), spaceAfter=3)
    bull_s   = ParagraphStyle("b", fontName="Helvetica", fontSize=9,
                               textColor=colors.HexColor("#374151"), leftIndent=12,
                               leading=13, spaceAfter=2)

    def hr(): return HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#c7d2fe"), spaceAfter=5)
    def hr_thick(): return HRFlowable(width="100%", thickness=1.5,
                                      color=PRIMARY, spaceAfter=8)

    story = []
    story.append(p(c["name"], name_s))
    story.append(p(f'{c["location"]}  |  {c["phone"]}  |  {c["email"]}', contact_s))
    story.append(hr_thick())

    def section(title):
        story.append(p(title.upper(), sec_s))
        story.append(hr())

    section("Professional Summary")
    story.append(p(c["summary"], base))

    section("Technical Skills")
    for skill in c["skills"]:
        story.append(p(f"• {skill}", ParagraphStyle("sk", fontName="Helvetica", fontSize=9.5,
                                                     textColor=colors.HexColor("#374151"),
                                                     leftIndent=8, leading=13, spaceAfter=1)))

    section("Work Experience")
    for exp in c["experience"]:
        story.append(p(f'{exp["title"]}  —  {exp["company"]}', job_s))
        story.append(p(exp["duration"], dur_s))
        for pt in exp["points"]:
            story.append(p(f"• {pt}", bull_s))

    section("Education")
    story.append(p(c["education"], base))

    if c.get("projects"):
        section("Projects")
        for proj in c["projects"]:
            story.append(p(f"• {proj}", bull_s))

    doc.build(story)
    print(f"  OK  {filepath}")


print("Regenerating 4 resumes...")
for cand in CANDIDATES:
    fname = cand["name"].replace(" ", "_") + ".pdf"
    build_resume(cand, os.path.join(OUT, fname))

print(f"\nDone — 4 updated PDFs saved to: {OUT}")
