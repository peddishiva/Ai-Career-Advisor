"""
Tests for ResumeParser Service
Validates section extraction, regex resilience, entity extraction, and docx/pdf handling.
"""

import sys
from pathlib import Path
import unittest

# Ensure backend root is in sys.path
backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from services.parser_service import ResumeParser


class TestResumeParser(unittest.TestCase):
    """Test suite for the resume parser service."""

    def setUp(self):
        self.parser = ResumeParser()
        self.sample_text = """
Alex Morgan
alex.morgan@example.com
+1 (555) 234-5678

TECHNICAL SKILLS
Languages & Frameworks: Python, JavaScript, TypeScript, React.js, FastAPI, Node.js
Databases & Cloud: PostgreSQL, MongoDB, Redis, AWS, Docker, Kubernetes, Git
Practices: Agile, CI/CD, Microservices, REST APIs, Unit Testing

PROFESSIONAL EXPERIENCE
Senior Software Engineer - CloudScale Solutions (2022 - Present)
- Architected and deployed microservices backend using FastAPI and PostgreSQL handling 5M daily requests.
- Optimized query latency by 40% using Redis caching and index refactoring.
- Led sprint planning in an Agile environment and mentored junior engineers.

Full Stack Developer - InnovateTech (2020 - 2022)
- Built interactive customer dashboard in React and TypeScript.
- Integrated automated CI/CD deployment pipelines on AWS using Docker containers.

KEY PROJECTS
Real-time Analytics Dashboard
- Developed live telemetry visualizer with React, Node.js, and WebSockets.

Distributed Task Queue
- Engineered high-throughput job queue worker with Python, Redis, and Docker.

EDUCATION
Master of Science in Computer Science - Stanford University
Bachelor of Technology in Information Technology
"""

    def test_extract_information_sections(self):
        """Verify that parser extracts all contact info, sections, and canonical skills."""
        data = self.parser._extract_information(self.sample_text)
        
        self.assertEqual(data['name'], 'Alex Morgan')
        self.assertEqual(data['email'], 'alex.morgan@example.com')
        self.assertIn('555', data['phone'])
        
        # Verify canonical skills extraction
        skills = data['skills']
        self.assertIn('Python', skills)
        self.assertIn('React', skills)  # 'React.js' normalized to 'React'
        self.assertIn('FastAPI', skills)
        self.assertIn('TypeScript', skills)
        self.assertIn('PostgreSQL', skills)
        self.assertIn('Docker', skills)
        self.assertIn('AWS', skills)
        self.assertIn('Kubernetes', skills)
        self.assertIn('CI/CD', skills)
        
        # Verify section evidence
        section_evidence = data['section_evidence']
        self.assertIn('skills_section', section_evidence)
        self.assertIn('experience_skills', section_evidence)
        self.assertIn('project_skills', section_evidence)
        
        # Experience and projects
        self.assertGreaterEqual(len(data['experience']), 2)
        self.assertGreaterEqual(len(data['projects']), 2)
        self.assertGreaterEqual(len(data['education']), 1)
        
    def test_phase_1_6_messy_section_headers(self):
        """Verify parser supports realistic messy section headers."""
        text = """
Taylor Reed
taylor.reed@example.com

**1. CORE COMPETENCIES:**
Python, SQL, Docker

### WORK HISTORY
Data Analyst - Insight Co
- Developed SQL reporting pipelines with Python.

* SELECTED PROJECTS:
Portfolio API
- Deployed services using Docker.

ACADEMICS:
Bachelor of Science in Computer Science

CERTIFICATIONS:
AWS Certified Cloud Practitioner
"""
        data = self.parser._extract_information(text)
        
        self.assertIn('Python', data['section_evidence']['skills_section'])
        self.assertIn('SQL', data['section_evidence']['experience_skills'])
        self.assertIn('Docker', data['section_evidence']['project_skills'])
        self.assertEqual(len(data['experience']), 1)
        self.assertEqual(len(data['projects']), 1)
        self.assertEqual(len(data['education']), 1)
        self.assertEqual(len(data['certifications']), 1)
        
    def test_phase_1_6_no_full_resume_fallback_skills_only(self):
        """Skills-only resumes should not fabricate structured section evidence."""
        text = """
Jordan Lee

TECH STACK:
Python, SQL, React, Docker
"""
        data = self.parser._extract_information(text)
        
        self.assertEqual(data['experience'], [])
        self.assertEqual(data['projects'], [])
        self.assertEqual(data['education'], [])
        self.assertEqual(data['certifications'], [])
        
    def test_phase_1_6_no_full_resume_fallback_projects_only(self):
        """Project text must not become experience or education."""
        text = """
Jordan Lee

SELECTED PROJECTS
Built a Data Analyst dashboard using Python and SQL.
"""
        data = self.parser._extract_information(text)
        
        self.assertEqual(data['experience'], [])
        self.assertEqual(data['education'], [])
        self.assertEqual(len(data['projects']), 1)
        
    def test_phase_1_6_no_full_resume_fallback_education_only(self):
        """Education text must not become experience or projects."""
        text = """
Jordan Lee

ACADEMICS
Bachelor of Arts in English Literature
"""
        data = self.parser._extract_information(text)
        
        self.assertEqual(data['experience'], [])
        self.assertEqual(data['projects'], [])
        self.assertEqual(len(data['education']), 1)
        
    def test_phase_1_6_certifications_do_not_become_experience(self):
        """Certification section evidence should remain isolated."""
        text = """
Jordan Lee

CERTIFICATIONS
AWS Certified Cloud Practitioner
"""
        data = self.parser._extract_information(text)
        
        self.assertEqual(data['experience'], [])
        self.assertEqual(data['projects'], [])
        self.assertEqual(data['education'], [])
        self.assertEqual(len(data['certifications']), 1)

    def test_letter_spaced_pdf_section_headers_are_segmented(self):
        """PDF-extracted letter-spaced headings should preserve parser section isolation."""
        text = """
Sample Candidate
sample.candidate@example.com
+1 555-123-4567

S U M M A R Y
Computer science undergraduate focused on applied NLP and full-stack development.

P R O F E S S I O N A L E X P E R I E N C E
AI Developer Intern - Sample Employer 2025
- Built an AI-powered auditing tool using Python and SQL.

E D U C A T I O N
B. Tech, Computer Science and Engineering (AI-ML) - Sample Institute 2023 - 2027

A C A D E M I C P R O J E C T S
Career Advisor
- Built a resume analysis dashboard using React and FastAPI.

S K I L L S
Python, React, SQL, FastAPI

C E R T I F I C A T I O N S & A C H I E V E M E N T S
AWS Certified Cloud Practitioner
"""
        data = self.parser._extract_information(text)

        self.assertGreaterEqual(len(data['experience']), 1)
        self.assertGreaterEqual(len(data['education']), 1)
        self.assertGreaterEqual(len(data['projects']), 1)
        self.assertGreaterEqual(len(data['certifications']), 1)
        self.assertIn('Python', data['section_evidence']['skills_section'])

    def test_phase_1_7_experience_section_splits_three_roles(self):
        """Experience entries should split on role headers without blank lines."""
        text = """
Jordan Lee
jordan.lee@example.com

PROFESSIONAL EXPERIENCE
AI Developer Intern - Infosys Springboard 2025
- Built an AI quality auditing workflow with Python.
- Automated scoring and reporting.
SDET Intern - ECNODEV 2025
- Tested API endpoints and UI flows.
- Reported defects before release.
Videography & Photography Lead - Campus Developer Group 2025 - 2026
- Led event coverage and coordinated student teams.

SKILLS
Python, REST APIs, Testing
"""
        data = self.parser._extract_information(text)

        self.assertEqual(len(data['experience']), 3)
        self.assertEqual(data['experience'][0]['title'], 'AI Developer Intern')
        self.assertEqual(data['experience'][1]['title'], 'SDET Intern')
        self.assertEqual(data['experience'][2]['title'], 'Videography & Photography Lead')
        self.assertEqual(data['experience'][1]['company'], 'ECNODEV')

    def test_phase_1_7_real_experience_header_still_splits(self):
        """Legitimate role headers should continue to create experience entries."""
        text = """
Jordan Lee
jordan.lee@example.com

PROFESSIONAL EXPERIENCE
Software Engineer - Sample Labs 2024 - Present
Built APIs with Python.
Data Analyst - Insight Co 2023 - 2024
Analyzed operational dashboards with SQL.
"""
        data = self.parser._extract_information(text)

        self.assertEqual(len(data['experience']), 2)
        self.assertEqual(data['experience'][0]['title'], 'Software Engineer')
        self.assertEqual(data['experience'][1]['title'], 'Data Analyst')

    def test_phase_1_7_action_verb_line_stays_inside_experience_entry(self):
        """Bulletless action lines should not become fake job headers."""
        text = """
Jordan Lee
jordan.lee@example.com

PROFESSIONAL EXPERIENCE
Videography & Photography Lead - Campus Developer Group 2025 - 2026
Led coverage and coordination for Cloud Computing and Tech-Sprint campus events run with developer programs.
Managed student teams during event execution.
"""
        data = self.parser._extract_information(text)

        self.assertEqual(len(data['experience']), 1)
        self.assertEqual(data['experience'][0]['title'], 'Videography & Photography Lead')
        self.assertIn('Led coverage and coordination', data['experience'][0]['description'])
        self.assertIn('Managed student teams', data['experience'][0]['description'])

    def test_phase_1_7_docx_like_bulletless_experience_block_does_not_over_split(self):
        """DOCX extraction can lose bullets; action lines should remain under the active role."""
        text = """
Jordan Lee
jordan.lee@example.com

PROFESSIONAL EXPERIENCE
AI Developer Intern - Sample Internship 2025
Built an AI auditing workflow with Python.
Automated scoring and reporting for support teams.
SDET Intern - Sample Company 2025
Developed API endpoint test cases.
Improved regression coverage across UI flows.
Community Lead - Sample Developer Group 2025 - 2026
Led event coordination for campus developer programs.
Created onboarding materials for student teams.
"""
        data = self.parser._extract_information(text)

        self.assertEqual(len(data['experience']), 3)
        self.assertIn('Automated scoring', data['experience'][0]['description'])
        self.assertIn('Improved regression coverage', data['experience'][1]['description'])
        self.assertIn('Created onboarding materials', data['experience'][2]['description'])

    def test_phase_1_7_project_section_splits_four_projects(self):
        """Project entries should split on title lines and keep bullet blocks together."""
        text = """
Jordan Lee
jordan.lee@example.com

ACADEMIC PROJECTS
AI Call Auditor
- Engineered an AI auditing pipeline with Python.
- Generated structured reports.
Career Advisor
- Built a resume analyzer with React and FastAPI.
- Produced role matches and recommendations.
JARVIS Assistant Bot
- Designed a voice assistant using Python.
- Integrated contact automation.
Financial Fraud Detector
- Built a fraud detection dashboard with SQL.
- Evaluated machine learning models.

SKILLS
Python, React, FastAPI, SQL, Machine Learning
"""
        data = self.parser._extract_information(text)

        self.assertEqual(len(data['projects']), 4)
        self.assertEqual(
            [project['title'] for project in data['projects']],
            ['AI Call Auditor', 'Career Advisor', 'JARVIS Assistant Bot', 'Financial Fraud Detector']
        )
        self.assertTrue(all(project['technologies'] for project in data['projects']))

    def test_phase_1_7_project_titles_strip_repository_link_markers(self):
        """Project titles should remove trailing GitHub/link text generically."""
        text = """
Jordan Lee
jordan.lee@example.com

ACADEMIC PROJECTS
AI Call Auditor - GitHub Link
- Built an AI auditing pipeline with Python.
Career Advisor — GitHub
- Built a career dashboard with React.
Financial Fraud Detector link
- Built a fraud model with SQL.
"""
        data = self.parser._extract_information(text)

        self.assertEqual(
            [project['title'] for project in data['projects']],
            ['AI Call Auditor', 'Career Advisor', 'Financial Fraud Detector']
        )

    def test_phase_1_7_certifications_are_extracted_generically(self):
        """Certification bullets should not require hard-coded provider keywords."""
        text = """
Jordan Lee
jordan.lee@example.com

CERTIFICATIONS & ACHIEVEMENTS
- Oracle AI Certification - link
- NPTEL - Python for Data Science; Natural Language Processing - link
- Google Arcade 2025, Cohort 2 - Legend Player - link
- Google Associate Cloud Engineer - Link
- Languages: English, Telugu, Hindi
"""
        data = self.parser._extract_information(text)
        names = [cert['name'] for cert in data['certifications']]

        self.assertIn('Oracle AI Certification', names)
        self.assertIn('NPTEL - Python for Data Science', names)
        self.assertIn('NPTEL - Natural Language Processing', names)
        self.assertIn('Google Arcade 2025, Cohort 2 - Legend Player', names)
        self.assertIn('Google Associate Cloud Engineer', names)
        self.assertFalse(any(name.lower().startswith('languages') for name in names))

    def test_phase_1_7_hyderabad_does_not_create_fake_education_entry(self):
        """Degree matching must not match partial text inside Hyderabad."""
        text = """
Jordan Lee
jordan.lee@example.com

EDUCATION
B.Tech Computer Science - Sample Institute, Hyderabad 2023 - 2027
- CGPA: 7.63 / 10
Hyderabad
2023 - 2027
"""
        data = self.parser._extract_information(text)

        self.assertEqual(len(data['education']), 1)
        self.assertEqual(data['education'][0]['degree'], 'B.Tech')
        self.assertEqual(data['education'][0]['field'], 'Computer Science')
        self.assertFalse(any('bad' in edu['degree'].lower() for edu in data['education']))

    def test_phase_1_7_valid_education_patterns_are_extracted(self):
        """Common degree patterns should still be accepted."""
        text = """
Jordan Lee
jordan.lee@example.com

EDUCATION
Bachelor of Science in Computer Science - Sample University
M.Tech in AI - Sample Institute
M.S. in Data Science - Example Graduate School
"""
        data = self.parser._extract_information(text)

        self.assertEqual(len(data['education']), 3)
        self.assertEqual(data['education'][0]['field'], 'Computer Science')
        self.assertEqual(data['education'][1]['field'], 'AI')
        self.assertEqual(data['education'][2]['field'], 'Data Science')

    def test_phase_1_7_section_isolation_after_entry_splitting(self):
        """Experience and project splitting must stay inside their own sections."""
        text = """
Jordan Lee
jordan.lee@example.com

PROFESSIONAL EXPERIENCE
Software Engineer - Sample Co 2024 - Present
- Built backend APIs with Python.

ACADEMIC PROJECTS
Portfolio Dashboard
- Built a React dashboard with SQL reports.
"""
        data = self.parser._extract_information(text)

        self.assertEqual(len(data['experience']), 1)
        self.assertEqual(len(data['projects']), 1)
        self.assertIn('Software Engineer', data['experience'][0]['description'])
        self.assertNotIn('Portfolio Dashboard', data['experience'][0]['description'])
        self.assertIn('Portfolio Dashboard', data['projects'][0]['description'])
        self.assertNotIn('Software Engineer', data['projects'][0]['description'])

    def test_phase_1_7_sanitized_real_world_resume_structure(self):
        """Sanitized real-world resume structure should preserve distinct entries."""
        text = """
Sample Candidate
sample.candidate@example.com
+1 555-123-4567

SUMMARY
Computer science undergraduate focused on applied AI and full-stack development.

PROFESSIONAL EXPERIENCE
AI Developer Intern - Sample Internship 2025
- Built an AI auditing tool using Python.
SDET Intern - Sample Company 2025
- Tested API endpoints and frontend flows.
Community Lead - Sample Developer Group 2025 - 2026
- Led campus technology event coordination.

EDUCATION
B.Tech Computer Science and Engineering - Sample Institute, Hyderabad 2023 - 2027
- CGPA: 7.63 / 10

ACADEMIC PROJECTS
AI Call Auditor
- Engineered an AI auditing pipeline.
Career Advisor
- Built a resume analysis workflow with React and FastAPI.
JARVIS Assistant Bot
- Designed a voice assistant using Python.
Financial Fraud Detector
- Built a machine learning fraud detector with SQL.

SKILLS
Python, JavaScript, React, FastAPI, SQL, Machine Learning, Git

CERTIFICATIONS & ACHIEVEMENTS
- Oracle AI Certification - link
- NPTEL - Python for Data Science; Natural Language Processing - link
- Google Associate Cloud Engineer - Link
"""
        data = self.parser._extract_information(text)

        self.assertEqual(len(data['experience']), 3)
        self.assertEqual(len(data['projects']), 4)
        self.assertGreaterEqual(len(data['certifications']), 4)
        self.assertEqual(len(data['education']), 1)

    def test_phase_1_7_letter_spaced_headings_do_not_inflate_global_skills(self):
        """Heading letters such as R/C should not become global skills by themselves."""
        text = """
Sample Candidate
sample.candidate@example.com

P R O F E S S I O N A L E X P E R I E N C E
Software Engineer - Sample Co 2024 - Present
- Built APIs with Python.

S K I L L S
Python
"""
        data = self.parser._extract_information(text)

        self.assertIn('Python', data['skills'])
        self.assertNotIn('R', data['skills'])
        self.assertNotIn('C', data['skills'])


if __name__ == '__main__':
    unittest.main()
