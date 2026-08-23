"""Sanitized resume/JD fixtures for Phase 2B matching tests."""

from services.job_description_parser import JobDescriptionParser
from services.parser_service import ResumeParser


SOFTWARE_ENGINEER_RESUME = """
Sample Engineer
sample.engineer@example.com

TECHNICAL SKILLS
Python, SQL, Git, REST APIs, FastAPI, Docker

PROFESSIONAL EXPERIENCE
Backend Developer - Clearpath Labs 2023 - 2025
- Developed software development services and REST APIs using Python, FastAPI, SQL, and Git.
- Built Docker deployment workflows for backend services.

PROJECTS
Inventory API Platform
- Built REST APIs with Python, FastAPI, SQL, and Docker.

EDUCATION
B.Tech Computer Science and Engineering - Sample Institute

CERTIFICATIONS
AWS Certified Cloud Practitioner
"""


DATA_ANALYST_MISMATCH_RESUME = """
Sample Analyst
sample.analyst@example.com

TECHNICAL SKILLS
Tableau, Excel, Power BI, Data Analysis

PROFESSIONAL EXPERIENCE
Reporting Analyst - Insight Co 2022 - 2025
- Created executive dashboards with Excel, Tableau, and Power BI.
- Analyzed sales reports and presented business trends.

PROJECTS
Sales Reporting Dashboard
- Built dashboard views using Tableau and Excel.

EDUCATION
Bachelor of Commerce - Sample College
"""


PREFERRED_TRAP_RESUME = """
Sample Frontend Cloud Developer
sample.frontend@example.com

TECHNICAL SKILLS
Python, React, AWS, Terraform

PROFESSIONAL EXPERIENCE
Frontend Developer - Cloud UI Co 2022 - 2025
- Developed software development workflows for React dashboards on AWS.
- Automated infrastructure changes with Terraform.

PROJECTS
Cloud Frontend Portal
- Built a React dashboard deployed on AWS using Terraform automation.

EDUCATION
B.Tech Information Technology - Sample Institute
"""


PROJECT_ONLY_BACKEND_RESUME = """
Sample Project Builder
sample.builder@example.com

TECHNICAL SKILLS
Python, REST APIs, FastAPI, Docker

PROJECTS
Backend Order API
- Built REST APIs using Python, FastAPI, and Docker.

Realtime Backend Worker
- Implemented backend services and API endpoints with Python.

EDUCATION
B.Tech Computer Science and Engineering - Sample Institute
"""


COMMERCE_EDUCATION_RESUME = """
Sample Commerce Graduate
sample.commerce@example.com

TECHNICAL SKILLS
Python, Git

PROJECTS
Budget Tracker
- Built a Python script for personal finance reports.

EDUCATION
Bachelor of Commerce - Sample College
"""


ALIAS_RESUME = """
Sample Platform Engineer
sample.platform@example.com

TECHNICAL SKILLS
React, JavaScript, Postgres, K8s

PROJECTS
Platform Console
- Built React and JavaScript UI backed by Postgres and deployed to K8s.

EDUCATION
B.Tech Computer Science - Sample Institute
"""


SKILLS_ONLY_AWS_RESUME = """
Sample Cloud Learner
sample.cloud@example.com

TECHNICAL SKILLS
AWS
"""


MISSING_DATE_EXPERIENCE_RESUME = """
Sample Backend Engineer
sample.backend@example.com

TECHNICAL SKILLS
Python, REST APIs

PROFESSIONAL EXPERIENCE
Backend Developer - Sample Services
- Developed REST APIs using Python for backend services.
"""


SOFTWARE_ENGINEER_JD = """
Software Engineer
Company: Clearpath Labs
Location: Remote
Employment Type: Full-time

Responsibilities
- Build REST APIs in Python and FastAPI.
- Collaborate with engineering teams using Git workflows.

Requirements
- 2+ years of software development experience.
- Must have Python, SQL, Git, and REST APIs.
- Bachelor's degree in Computer Science, Software Engineering, or related field.

Preferred Skills
- Docker and AWS are preferred.

Certifications
- AWS certification is preferred.
"""


PREFERRED_TRAP_JD = """
Software Engineer
Company: StackWorks
Location: Remote
Employment Type: Full-time

Requirements
- Must have Python, SQL, and Docker.
- 2+ years of software development experience.
- Bachelor's degree in Computer Science, Software Engineering, Information Technology, or related field.

Responsibilities
- Build React dashboards for cloud workflows.

Preferred Skills
- React, AWS, and Terraform are preferred.
"""


BACKEND_EXPERIENCE_JD = """
Backend Engineer
Company: API Foundry
Location: Remote
Employment Type: Full-time

Responsibilities
- Build REST APIs using Python.
- Implement backend services.

Requirements
- 2+ years of professional backend experience.
- Must have Python and REST APIs.
"""


EDUCATION_JD = """
Software Engineer
Company: DegreeCheck
Location: Remote
Employment Type: Full-time

Requirements
- Bachelor's degree in Computer Science, Software Engineering, or related field.
"""


CERTIFICATION_JD = """
Cloud Engineer
Company: CertCheck
Location: Remote
Employment Type: Full-time

Preferred Skills
- AWS is preferred.

Certifications
- AWS certification is preferred.
"""


ALIAS_JD = """
Platform Engineer
Company: AliasWorks
Location: Remote
Employment Type: Full-time

Required Skills: React.js, Postgres, k8s
"""


RESPONSIBILITIES_ONLY_JD = """
Backend Engineer
Company: ResponsibilityOnly
Location: Remote
Employment Type: Contract

Responsibilities
- Build REST APIs using Python.
- Implement backend services.
"""


REQUIRED_ONLY_JD = """
Backend Developer
Company: RequiredOnly
Location: Remote
Employment Type: Full-time

Requirements
- Must have Python and FastAPI.
"""


PREFERRED_ONLY_JD = """
Frontend Developer
Company: PreferredOnly
Location: Remote
Employment Type: Contract

Preferred Skills
- React and TypeScript are preferred.
"""


FINANCIAL_ANALYST_RESUME = """
Sample Technology Graduate
sample.finance@example.com

TECHNICAL SKILLS
Python, SQL, Excel

EDUCATION
B.Tech Computer Science - Sample Institute
"""


CA_FINANCIAL_RESUME = """
Sample Finance Trainee
sample.ca@example.com

PROFESSIONAL EXPERIENCE
Finance Article Trainee - Sample Audit Firm 2024 - 2025
- Completed industrial training and articleship assignments in accounting and audit.

EDUCATION
Pursuing CA, IPCC cleared - Professional Accounting Institute

CERTIFICATIONS
CA Intermediate
"""


ELIGIBILITY_JD = """
Financial Analyst Intern
Company: Example Finance

Requirements
- Must be pursuing CA.
- Must have cleared IPCC.
- Must have completed 12-18 months of industrial training/articleship.
- Must have accounting and finance knowledge.
"""


LICENSE_JD = """
Compliance Analyst
Company: Example Compliance

Requirements
- Active professional license required.
"""


LICENSE_RESUME = """
Sample Compliance Analyst

CERTIFICATIONS
Active Professional License
"""


MEMBERSHIP_JD = """
Audit Associate
Company: Example Audit

Requirements
- Must be a registered member of the relevant professional body.
"""


MEMBERSHIP_RESUME = """
Sample Audit Associate

CERTIFICATIONS
Registered Member, Professional Accounting Body
"""


TRAINEE_JD = """
Graduate Trainee
Company: Example Group

Requirements
- Only candidates eligible for the company's graduate trainee program may apply.
"""


TRAINEE_RESUME = """
Sample Graduate

EXPERIENCE
Graduate trainee program participant - Example Group 2024 - 2025
"""


PREFERRED_QUALIFICATION_JD = """
Financial Analyst
Company: Example Finance

Preferred Qualifications
- CA qualification preferred.
"""


PROJECT_ONLY_ELIGIBILITY_RESUME = """
Sample Project Builder

PROJECTS
CA Eligibility Tracker
- Built a project that tracks pursuing CA candidates and IPCC status.
"""


SDE_FIDELITY_RESUME = """
Sample SDE Candidate
sample.sde@example.com

SKILLS
Python, Java, JavaScript, React, MySQL, GCP, Git, DSA, OOP, DBMS, Operating Systems, Computer Networks, SDLC, Machine Learning, NLP, Pandas

PROFESSIONAL EXPERIENCE
SDET Intern | Example QA Lab | 2024
- Built automated testing and CI/CD workflows for software services.
AI Developer Intern | Example Learning | 2025
- Developed Python and JavaScript applications with REST APIs.

PROJECTS
AI Call Auditor
- Built a Python backend API with automated testing.
AI Assistant / JARVIS
- Developed a JavaScript software application.
Career Advisor
- Built a web application with Python APIs.

EDUCATION
Bachelor of Technology
CSE (Artificial Intelligence and Machine Learning)
Example Institute of Technology
2023-2027
"""


def parsed_resume(text: str) -> dict:
    return ResumeParser().parse_text(text)


def parsed_jd(text: str) -> dict:
    return JobDescriptionParser().parse_text(text)
