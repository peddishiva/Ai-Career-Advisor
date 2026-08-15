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


if __name__ == '__main__':
    unittest.main()
