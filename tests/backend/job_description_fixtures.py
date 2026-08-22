"""Sanitized job description fixtures for Phase 2A tests."""


SOFTWARE_ENGINEER_JD = """
Software Engineer
Company: Clearpath Labs
Location: Remote, United States
Employment Type: Full-time

Responsibilities
- Build REST APIs in Python and FastAPI for customer-facing workflows.
- Collaborate with product and design teams to deliver reliable services.

Required Qualifications
- 2+ years of software development experience.
- Proficient in Python, SQL, Git, and REST APIs.
- Bachelor's degree in Computer Science or a related field.

Preferred Qualifications
- Experience with Docker or AWS is a plus.
- React experience preferred.

Certifications
- AWS certification is a plus.
"""


DATA_ANALYST_JD = """
Data Analyst
Company: Northwind Insights
Location: Austin, TX
Job Type: Full-time

What You'll Do
- Analyze operational datasets with SQL and Excel.
- Create dashboards for business stakeholders.

Basic Qualifications
- 1+ years of data analysis experience.
- Must have strong SQL and Excel skills.
- Bachelor's degree in Analytics, Statistics, Mathematics, Computer Science, or related field.

Preferred
- Tableau, Power BI, and Python experience preferred.
"""


ML_ENGINEER_JD = """
Machine Learning Engineer
Company: ModelWorks AI
Location: Hybrid - Boston, MA
Employment Type: Full-time

Role Responsibilities
- Develop machine learning pipelines using Python.
- Evaluate model quality and production behavior.

Minimum Qualifications
- 3+ years of machine learning experience.
- Required experience with Python, Machine Learning, and Statistics.
- Master's degree in Computer Science, Statistics, or related field.

Nice to Have
- PyTorch, TensorFlow, and Docker experience would be a plus.
"""


DEVOPS_CLOUD_JD = """
DevOps Cloud Engineer
Company: PlatformForge
Location: Denver, CO
Employment Type: Contract

What You Will Do
- Manage cloud infrastructure and deployment automation.
- Improve CI/CD reliability across Linux services.

Requirements:
- 4+ years of cloud infrastructure experience.
- Must have AWS, Docker, Linux, and Git.

Desired Qualifications
- Kubernetes, Terraform, and CI/CD experience would be a plus.

Certifications
- CKA certification preferred.
"""


ENTRY_LEVEL_SOFTWARE_ENGINEER_JD = """
Entry-Level Software Engineer
Company: StarterStack
Location: Chicago, IL
Employment Type: Full-time

Required Skills: Python, Java, Git, data structures

Experience Requirements
- 0-2 years of software development experience.

Responsibilities
- Develop frontend features with mentorship from senior engineers.
- Participate in code reviews and unit testing.

Education Requirements
- Bachelor's degree in Computer Science, Software Engineering, or related field.

Preferred Skills
- React and Docker are preferred.
"""


MESSY_INLINE_HEADER_JD = """
### Position: Data Scientist
Company: SignalWorks
Location: Remote
Type: Full-time

1. WHAT YOU'LL DO: Build machine learning models and analyze datasets with Python.
* MUST HAVE - 2+ years of data science experience with SQL and Pandas.
- preferred skills: Tableau, Power BI
Technical Skills: Python, SQL, Pandas, Machine Learning
"""


REQUIRED_ONLY_JD = """
Backend Developer
Company: ServiceBeam
Location: Remote
Employment Type: Full-time

Requirements
- Must have Python and FastAPI experience.
- 2+ years of backend development experience.
"""


PREFERRED_ONLY_JD = """
Frontend Developer
Company: InterfaceHub
Location: Remote
Employment Type: Contract

Nice to Have
- React experience would be a plus.
- TypeScript preferred.

Responsibilities
- Build accessible UI components.
"""


NO_EXPLICIT_REQUIREMENT_HEADERS_JD = """
Software Engineer
Company: Compact Apps
Location: Remote
Employment Type: Full-time

We need someone proficient in Python and SQL.
Experience with Docker is a plus.
You will build REST APIs with the product engineering team.
A bachelor's degree in Computer Science is required.
"""


MISSING_OPTIONAL_SECTIONS_JD = """
QA Engineer
Company: QualityLoop
Location: Remote
Employment Type: Full-time

Responsibilities
- Test web services and document defects.

Requirements
- Must have Testing and Git experience.
"""


RESUME_CONTROL = """
Alex Morgan
alex.morgan@example.com | +1 555-234-5678

TECHNICAL SKILLS
Python, SQL, Docker, Git

WORK EXPERIENCE
Software Engineer at Example Co | 2021 - Present
- Built backend APIs with Python.

EDUCATION
Bachelor of Science in Computer Science
"""


COVER_LETTER_CONTROL = """
Dear Hiring Manager,

I am excited to apply for the Software Engineer position at your company.
My resume includes Python, SQL, and Docker projects that align with your team.

Sincerely,
Candidate
"""


N8N_INSTALL_GUIDE = """
n8n Windows Installation Guide

This setup guide explains how to install n8n on Windows using Node.js, npm, Docker, and PowerShell.

Step-by-step instructions
1. Install Node.js from the official website.
2. Open PowerShell as administrator.
3. Run the following command:
npm install n8n -g
docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n
"""


README_CONTROL = """
# Analytics API README

This repository contains a Python FastAPI service with Docker and PostgreSQL.

## Installation
pip install -r requirements.txt
docker compose up
"""


TECHNICAL_TUTORIAL_CONTROL = """
Deploying Kubernetes Workloads

This tutorial explains how to build a Docker image, push it to AWS, and deploy with kubectl.

kubectl apply -f deployment.yaml
kubectl get pods
"""


BLOG_ARTICLE_CONTROL = """
Why Python and Docker Changed Modern Development

This article discusses trends in cloud computing, containers, CI/CD, and developer workflows.
It is written for engineers learning how software teams deploy applications.
"""


RANDOM_PARAGRAPH_CONTROL = """
The quarterly planning meeting covered roadmap themes, team rituals, and customer feedback.
Several departments shared ideas for improving communication and reporting quality.
"""


TECH_KEYWORD_LIST_CONTROL = """
Python
Docker
AWS
Kubernetes
SQL
React
"""


REALISTIC_JDS = {
    "software_engineer": SOFTWARE_ENGINEER_JD,
    "data_analyst": DATA_ANALYST_JD,
    "ml_engineer": ML_ENGINEER_JD,
    "devops_cloud": DEVOPS_CLOUD_JD,
    "entry_level_software_engineer": ENTRY_LEVEL_SOFTWARE_ENGINEER_JD,
}


NEGATIVE_CONTROLS = {
    "resume": RESUME_CONTROL,
    "cover_letter": COVER_LETTER_CONTROL,
    "n8n_install_guide": N8N_INSTALL_GUIDE,
    "readme": README_CONTROL,
    "technical_tutorial": TECHNICAL_TUTORIAL_CONTROL,
    "blog_article": BLOG_ARTICLE_CONTROL,
    "random_paragraph": RANDOM_PARAGRAPH_CONTROL,
    "technology_keyword_list": TECH_KEYWORD_LIST_CONTROL,
}
