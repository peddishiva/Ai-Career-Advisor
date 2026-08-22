"""
Tests for the deterministic resume validation gate.
"""

import sys
from pathlib import Path
import unittest

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from services.resume_validator import NOT_A_RESUME, VALID_RESUME, ResumeValidator


class TestResumeValidator(unittest.TestCase):
    """Validate resume/non-resume classification before parsing and scoring."""

    def setUp(self):
        self.validator = ResumeValidator()

    def assert_valid_resume(self, text: str):
        result = self.validator.validate_text(text)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["document_type"], VALID_RESUME)

    def assert_not_resume(self, text: str):
        result = self.validator.validate_text(text)
        self.assertFalse(result["valid"], result)
        self.assertEqual(result["document_type"], NOT_A_RESUME)

    def test_valid_software_engineer_resume(self):
        self.assert_valid_resume("""
Alex Morgan
alex.morgan@example.com | +1 555-234-5678

TECHNICAL SKILLS
Python, JavaScript, React, FastAPI, Docker, Git

WORK EXPERIENCE
Software Engineer at CloudScale Solutions | 2021 - Present
- Built backend APIs with Python and FastAPI.
- Deployed services using Docker and Git workflows.

EDUCATION
Bachelor of Science in Computer Science
""")

    def test_valid_data_scientist_resume(self):
        self.assert_valid_resume("""
Dr. Elena Rostova
elena.rostova@example.com | +1 555-404-5050

SKILLS
Python, Machine Learning, Deep Learning, SQL, TensorFlow

EXPERIENCE
Data Scientist at NeuralTech Labs | 2020 - Present
- Developed and evaluated machine learning models.
- Analyzed datasets with Python and SQL.

EDUCATION
Ph.D. in Computer Science
""")

    def test_valid_fresher_resume_with_limited_experience(self):
        self.assert_valid_resume("""
Priya Shah
priya.shah@example.com | +1 555-111-2222

EDUCATION
Bachelor of Technology in Information Technology | 2026

TECHNICAL SKILLS
Python, SQL, React

PROJECTS
Student Placement Portal
- Built a web application using React and SQL.
""")

    def test_n8n_installation_setup_guide_is_not_resume(self):
        self.assert_not_resume("""
n8n Windows Installation Guide

This setup guide explains how to install n8n on Windows using Node.js, npm, Docker, and PowerShell.

Step-by-step instructions
1. Install Node.js from the official website.
2. Open PowerShell as administrator.
3. Run the following command:
npm install n8n -g
docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n

Troubleshooting
If the service fails, check your PATH configuration and restart the terminal.
""")

    def test_technical_documentation_with_many_technologies_is_not_resume(self):
        self.assert_not_resume("""
Kubernetes Deployment Documentation

This documentation covers Python services deployed with Docker, Kubernetes, AWS, Linux, Node.js, and PostgreSQL.

Configuration guide
kubectl apply -f deployment.yaml
docker build -t analytics-api .
aws eks update-kubeconfig --name production
""")

    def test_random_article_blog_is_not_resume(self):
        self.assert_not_resume("""
Why Python and Docker Changed Modern Development

This article discusses trends in cloud computing, containers, CI/CD, and developer workflows.
It is written for engineers learning how software teams deploy applications.
""")

    def test_empty_document_is_not_resume(self):
        self.assert_not_resume("")

    def test_technical_keywords_only_are_not_resume(self):
        self.assert_not_resume("""
Python
Docker
AWS
Kubernetes
""")

    def test_minimal_legitimate_resume_is_valid(self):
        self.assert_valid_resume("""
Sam Rivera
sam.rivera@example.com

EDUCATION
Bachelor of Science in Computer Science

SKILLS
Python, SQL

PROJECTS
Inventory Dashboard
- Built a dashboard using Python and SQL.
""")

    def test_unusual_section_names_are_valid(self):
        self.assert_valid_resume("""
Taylor Reed
taylor.reed@example.com | +1 555-222-3333

CORE COMPETENCIES
Python, SQL, Docker

WORK HISTORY
Data Analyst at Insight Co | 2022 - Present
- Developed reporting dashboards using SQL.

SELECTED PROJECTS
Portfolio API
- Built an API with Python.

ACADEMICS
Bachelor of Science in Data Analytics
""")

    def test_command_heavy_technical_tutorial_is_not_resume(self):
        self.assert_not_resume("""
Python Docker Kubernetes AWS Linux Tutorial

Follow this tutorial to deploy a Python app.

pip install fastapi
docker build -t app .
docker run -p 8000:8000 app
kubectl create namespace demo
kubectl apply -f deployment.yaml
aws configure
sudo systemctl restart docker
""")
        
    def test_inline_sparse_fresher_resume_is_valid(self):
        self.assert_valid_resume("""
Anika Rao
anika.rao@example.com
SKILLS: Python, SQL, Git
EDUCATION: B.Tech Computer Science
""")
        
    def test_inline_fresher_resume_with_project_is_valid(self):
        self.assert_valid_resume("""
Rohan Mehta
rohan.mehta@example.com
SKILLS: Python, SQL
PROJECTS: AI Resume Analyzer
EDUCATION: B.Tech CSE
""")
        
    def test_inline_mixed_case_headers_are_valid_for_resume(self):
        self.assert_valid_resume("""
Maya Singh
maya.singh@example.com
1. sKiLlS: Python, SQL, Git
- pRoJeCtS: Portfolio Dashboard
* eDuCaTiOn: B.Tech Computer Science
""")
        
    def test_normal_fresher_resume_without_experience_is_valid(self):
        self.assert_valid_resume("""
Neha Patel
neha.patel@example.com

SKILLS
Python, SQL, Git

EDUCATION
B.Tech Computer Science

PROJECTS
AI Resume Analyzer
- Built a parser and dashboard using Python.
""")

    def test_letter_spaced_pdf_resume_structure_is_valid(self):
        self.assert_valid_resume("""
Sample Candidate
sample.candidate@example.com | +1 555-123-4567

S U M M A R Y
Computer science undergraduate focused on applied NLP and full-stack development.

P R O F E S S I O N A L E X P E R I E N C E
AI Developer Intern - Sample Internship 2025
- Built an AI-powered auditing tool with Python.

E D U C A T I O N
B. Tech, Computer Science and Engineering (AI-ML) - Sample Institute 2023 - 2027

A C A D E M I C P R O J E C T S
AI Call Auditor
- Engineered a pipeline using machine learning and SQL.

S K I L L S
Python, React, SQL, Machine Learning

C E R T I F I C A T I O N S & A C H I E V E M E N T S
- Cloud Engineer certification
""")
        
    def test_installation_guide_title_is_not_candidate_name(self):
        self.assertFalse(self.validator._looks_like_candidate_name(["Installation Guide"]))
        self.assertFalse(self.validator._looks_like_candidate_name(["Installation Guide: Docker Setup"]))
        self.assertFalse(self.validator._looks_like_candidate_name(["n8n on Windows 11"]))
        self.assertFalse(self.validator._looks_like_candidate_name(["API Documentation"]))
        self.assertFalse(self.validator._looks_like_candidate_name(["Troubleshooting Guide"]))
        self.assertFalse(self.validator._looks_like_candidate_name(["Resume Analysis Report"]))
        
    def test_installation_guide_with_title_colon_is_not_resume(self):
        self.assert_not_resume("""
Installation Guide: Docker Setup

This setup guide explains Docker installation on Windows.
docker pull postgres
docker run -p 5432:5432 postgres
""")
        
    def test_n8n_windows_title_is_not_resume(self):
        self.assert_not_resume("""
n8n on Windows 11

Setup guide for running n8n with Node.js and Docker.
npm install n8n -g
docker run n8nio/n8n
""")


if __name__ == "__main__":
    unittest.main()
