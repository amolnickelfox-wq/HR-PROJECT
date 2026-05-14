"""Generate 5 test resume DOCX files for batch pipeline testing."""
import os
from docx import Document

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "test_cvs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PHONE = "9897657426"

# JD used for scoring — paste this into the Batch Pipeline's Job Description box
JD = """Job Title: Backend Software Engineer
Company: Nickelfox Technologies

About the Role:
We are looking for a Backend Software Engineer to join our platform team. You will design and build scalable APIs, microservices, and backend systems that power our product. The ideal candidate has solid experience with Python or Node.js, cloud infrastructure, and SQL/NoSQL databases.

Responsibilities:
- Design and build RESTful APIs and backend microservices
- Work with SQL and NoSQL databases (PostgreSQL, MongoDB, Redis)
- Deploy and manage services on AWS using Docker and CI/CD pipelines
- Collaborate with frontend, data, and DevOps teams
- Write clean, tested, production-grade code
- Participate in system design discussions and code reviews

Required Skills:
- 2+ years of backend development experience
- Proficiency in Python, Node.js, or Go
- Experience with REST APIs and microservices architecture
- SQL databases (PostgreSQL or MySQL)
- Cloud platforms: AWS (EC2, S3, RDS, Lambda)
- Docker and containerization
- Git and CI/CD workflows

Good to Have:
- Message queues: Kafka or RabbitMQ
- Redis or other caching systems
- Kubernetes or container orchestration
- Data pipelines or ETL experience
- GraphQL
- gRPC or high-throughput systems

Experience: 2–6 years
Location: Bengaluru / Remote
"""

RESUMES = [
    {
        "filename": "arjun_sharma_cv.docx",
        "content": """Arjun Sharma
arjun.sharma@gmail.com | {phone} | LinkedIn: linkedin.com/in/arjunsharma | GitHub: github.com/arjunsharma

SUMMARY
Senior Software Engineer with 5 years of experience building production-grade backend systems and ML-powered APIs. Proficient in Python, FastAPI, and AWS. Strong background in designing scalable microservices, REST APIs, and data pipelines that serve millions of users.

EXPERIENCE

Senior Backend Engineer — Flipkart, Bengaluru (2021 – Present)
- Built and maintained Python (FastAPI) microservices for product recommendation and search, serving 12M+ daily users
- Designed RESTful APIs consumed by mobile and web clients; reduced average response time by 35% via Redis caching
- Deployed services on AWS (EC2, S3, SageMaker) using Docker and GitHub Actions CI/CD pipelines
- Managed PostgreSQL and DynamoDB schemas for high-read workloads; optimised slow queries by 60%
- Led a team of 3 engineers; conducted weekly code reviews and mentored 2 junior developers

Data Scientist — Mu Sigma, Bengaluru (2019 – 2021)
- Built Python-based data pipelines processing 500GB+ daily logs using Spark and Kafka
- Developed REST APIs in Flask for serving ML model predictions to internal analytics dashboards

SKILLS
Python, FastAPI, Flask, SQL, PostgreSQL, DynamoDB, Redis, Kafka, Docker, Kubernetes, AWS (EC2, S3, RDS, Lambda), GitHub Actions, Git, Linux

EDUCATION
B.Tech in Computer Science — IIT Roorkee (2015 – 2019) | CGPA: 8.7 / 10

PROJECTS
- APIGateway: Custom API rate-limiting and auth middleware library in Python (1.2K GitHub stars)
- DataSync: Real-time Kafka-to-PostgreSQL pipeline with schema evolution support
""".format(phone=PHONE),
    },
    {
        "filename": "priya_nair_cv.docx",
        "content": """Priya Nair
priya.nair@outlook.com | {phone} | GitHub: github.com/priyanair

SUMMARY
Full Stack Engineer with 4 years of experience building scalable web applications and backend APIs. Proficient in Node.js, TypeScript, PostgreSQL, and AWS. Experienced in microservices architecture, CI/CD, and cloud-native deployments.

EXPERIENCE

Senior Software Engineer — Razorpay, Bengaluru (2022 – Present)
- Designed and built Node.js (Express) microservices for payment reporting, handling 2M+ transactions per day
- Built RESTful and GraphQL APIs used by 50,000+ merchants; maintained 99.95% SLA
- Migrated monolithic backend to microservices on AWS ECS — reduced deployment time from 2 hours to 15 minutes
- Managed PostgreSQL and MongoDB databases; implemented Redis caching reducing DB load by 40%
- Integrated AWS Lambda for async event processing; set up GitHub Actions CI/CD for 8 services

Software Engineer — Freshworks, Chennai (2020 – 2022)
- Built Node.js backend services for CRM platform; added WebSocket support for real-time notifications
- Wrote unit and integration tests (Jest, Supertest) achieving 85% code coverage
- Integrated Stripe and Razorpay payment gateways with idempotency and webhook handling

SKILLS
JavaScript, TypeScript, Node.js, Express, GraphQL, REST, PostgreSQL, MongoDB, Redis, Docker, AWS (EC2, RDS, Lambda, ECS), GitHub Actions, Jest, Git

EDUCATION
B.E. in Information Technology — Anna University, Chennai (2016 – 2020) | CGPA: 8.2 / 10

PROJECTS
- OpenBudget: Personal finance API built with Node.js + PostgreSQL + Plaid integration
- DevPulse: GitHub activity tracker with real-time webhook processing and Redis pub/sub
""".format(phone=PHONE),
    },
    {
        "filename": "rahul_verma_cv.docx",
        "content": """Rahul Verma
rahul.verma99@gmail.com | {phone}

OBJECTIVE
Recent B.Tech graduate (2024) seeking an entry-level software development role. Eager to learn and grow in a professional environment.

EDUCATION
B.Tech in Computer Science — AKTU, Lucknow (2020 – 2024) | CGPA: 6.8 / 10

SKILLS
C++, Python (beginner), HTML, CSS, JavaScript (basic), MySQL (basic)

PROJECTS

Library Management System (Final Year Project)
- Desktop application in Python + Tkinter to manage book inventory for college library
- SQLite for data storage; basic CRUD operations

Portfolio Website
- Personal portfolio using HTML, CSS, basic JavaScript; hosted on GitHub Pages

To-Do App
- Vanilla JavaScript to-do list with localStorage; no backend

INTERNSHIP
Web Development Intern — TechSolutions Pvt Ltd, Lucknow (June – August 2023)
- Assisted in building static HTML/CSS pages for company website
- Fixed minor UI bugs under supervision; no backend or cloud work involved

CERTIFICATIONS
- Python for Beginners — Udemy (2023)
- HTML & CSS Fundamentals — freeCodeCamp (2022)

EXTRACURRICULAR
- Member, coding club AKTU
- Participated in college hackathon (team of 4); did not place
""".format(phone=PHONE),
    },
    {
        "filename": "sneha_kapoor_cv.docx",
        "content": """Sneha Kapoor
sneha.kapoor@yahoo.com | {phone} | LinkedIn: linkedin.com/in/snehakapoor

SUMMARY
Backend and Data Engineer with 3 years of experience building production Python services, REST APIs, and large-scale data pipelines on AWS. Comfortable owning services end-to-end — from API design through deployment and monitoring.

EXPERIENCE

Backend & Data Engineer — Swiggy, Bengaluru (2022 – Present)
- Built Python (FastAPI) REST APIs for internal data products consumed by 20+ analyst and engineering teams
- Designed and maintained 30+ ETL pipelines using Apache Airflow and PySpark on AWS EMR
- Managed PostgreSQL and Redshift schemas; wrote complex SQL queries and optimised slow reports by 50%
- Implemented real-time data stream with Kafka + Spark Structured Streaming for order tracking
- Deployed all services with Docker on AWS (EC2, S3, RDS); set up CI/CD via GitHub Actions
- Reduced pipeline failure rate from 12% to 1.5% by adding dbt data quality tests

Associate Software Engineer — Accenture, Pune (2021 – 2022)
- Developed Python REST APIs and PySpark jobs for data migration from Oracle to AWS S3
- Wrote automated test suites (pytest) and integrated them into CI pipeline

SKILLS
Python, FastAPI, REST APIs, SQL, PostgreSQL, Redshift, PySpark, Apache Airflow, Kafka, dbt, Docker, AWS (S3, EC2, RDS, EMR, Glue), GitHub Actions, Git, Linux

EDUCATION
B.Tech in Electronics & Communication — NIT Warangal (2017 – 2021) | CGPA: 8.0 / 10

PROJECTS
- DataLineage: Python + Dash tool to visualise Airflow DAG lineage (open source, 400 stars)
- RealTimeDash: Kafka + FastAPI backend streaming live data to a React dashboard
""".format(phone=PHONE),
    },
    {
        "filename": "vikram_mehta_cv.docx",
        "content": """Vikram Mehta
vikram.mehta@protonmail.com | {phone} | GitHub: github.com/vikrammehta

SUMMARY
Staff Backend Engineer with 6 years of experience building high-throughput distributed systems and REST/gRPC APIs. Expert in Go and Python microservices. Proven track record delivering systems with 99.99% uptime at large-scale consumer internet companies.

EXPERIENCE

Staff Engineer — Zepto, Mumbai (2023 – Present)
- Designed the order allocation microservice (Go + PostgreSQL) handling 80,000 orders/hour with P99 latency < 50ms
- Built REST and gRPC APIs for inter-service communication; reduced average latency by 30%
- Led migration from RabbitMQ to Kafka for async messaging — improved throughput 5×
- Deployed all services on AWS with Kubernetes and Terraform; automated CI/CD with GitHub Actions

Senior Backend Engineer — PhonePe, Bengaluru (2020 – 2023)
- Owned UPI transaction processing service (Python + PostgreSQL); 99.99% uptime during peak traffic (IPL, Diwali)
- Implemented distributed rate limiting in Redis Lua scripts across 50+ microservices
- Reduced AWS infrastructure cost by 25% through Kubernetes pod right-sizing and spot instances

Backend Engineer — Ola, Bengaluru (2018 – 2020)
- Built driver location tracking service in Go + PostGIS supporting 200K concurrent connections
- Designed REST APIs and an internal rules DSL for surge pricing engine

SKILLS
Go, Python, REST, gRPC, Kafka, RabbitMQ, PostgreSQL, Redis, Cassandra, Kubernetes, Docker, Terraform, AWS (EC2, RDS, S3, EKS), GCP, GitHub Actions, Prometheus, Grafana, Git

EDUCATION
B.Tech in Computer Science — BITS Pilani (2014 – 2018) | CGPA: 8.5 / 10

PROJECTS
- GoCache: In-memory LRU cache library in Go with TTL and eviction (2K GitHub stars)
- DistLock: Distributed lock using Redis with automatic lease renewal
""".format(phone=PHONE),
    },
]


def make_docx(filepath: str, text: str):
    doc = Document()
    for line in text.strip().split("\n"):
        p = doc.add_paragraph(line)
        p.paragraph_format.space_after = 0
    doc.save(filepath)
    print(f"  Created: {filepath}")


if __name__ == "__main__":
    print(f"Generating test CVs in: {OUTPUT_DIR}\n")
    for r in RESUMES:
        path = os.path.join(OUTPUT_DIR, r["filename"])
        make_docx(path, r["content"])

    jd_path = os.path.join(OUTPUT_DIR, "job_description.txt")
    with open(jd_path, "w", encoding="utf-8") as f:
        f.write(JD)
    print(f"  Created: {jd_path}")

    print(f"\nDone. {len(RESUMES)} CVs created in test_cvs/")
    print("All have phone number:", PHONE)
    print("\n--- EXPECTED SCORING ---")
    print("  Arjun Sharma   → PASS (~88)  — 5yr Python backend, FastAPI, AWS, Docker, Redis")
    print("  Priya Nair     → PASS (~82)  — 4yr Node.js backend, PostgreSQL, AWS, Docker, CI/CD")
    print("  Rahul Verma    → FAIL (~38)  — Fresher, no cloud, no production backend experience")
    print("  Sneha Kapoor   → PASS (~78)  — 3yr Python/FastAPI, PostgreSQL, AWS, Docker, Kafka")
    print("  Vikram Mehta   → PASS (~95)  — 6yr Go/Python, microservices, AWS, Kafka, Redis, K8s")
    print("\nPaste test_cvs/job_description.txt into the Batch Pipeline JD box.")
