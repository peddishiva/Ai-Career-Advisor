"""
Route-level regression tests for the resume validation gate on /api/upload.
"""

import asyncio
import json
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from docx import Document
from starlette.datastructures import UploadFile

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from routes import upload as upload_route


class TestUploadValidationGate(unittest.TestCase):
    """Verify upload route behavior at the validation boundary."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_root = Path(self.temp_dir.name)
        self.upload_dir = temp_root / "uploads"
        self.analysis_dir = self.upload_dir / "analysis"
        self.analysis_dir.mkdir(parents=True)

        self.previous_latest_analysis = dict(upload_route.latest_analysis)
        upload_route.latest_analysis.clear()

        self.upload_dir_patch = patch.object(upload_route, "UPLOAD_DIR", self.upload_dir)
        self.analysis_dir_patch = patch.object(upload_route, "ANALYSIS_DIR", self.analysis_dir)
        self.upload_dir_patch.start()
        self.analysis_dir_patch.start()

    def tearDown(self):
        self.analysis_dir_patch.stop()
        self.upload_dir_patch.stop()
        upload_route.latest_analysis.clear()
        upload_route.latest_analysis.update(self.previous_latest_analysis)
        self.temp_dir.cleanup()

    def _docx_upload(self, filename: str, text: str) -> UploadFile:
        document = Document()
        for line in text.strip().splitlines():
            document.add_paragraph(line.strip())

        payload = BytesIO()
        document.save(payload)
        payload.seek(0)
        return UploadFile(file=payload, filename=filename)

    def _call_upload(self, file: UploadFile) -> tuple[int, dict]:
        response = asyncio.run(upload_route.upload_resume(file))
        return response.status_code, json.loads(response.body.decode("utf-8"))

    def test_valid_resume_upload_returns_200_with_analysis(self):
        file = self._docx_upload(
            "valid_resume.docx",
            """
            Sample Candidate
            sample.candidate@example.com | +1 555-123-4567

            SUMMARY
            Software engineer with experience building APIs and data products.

            TECHNICAL SKILLS
            Python, FastAPI, React, SQL, Docker, Git

            PROFESSIONAL EXPERIENCE
            Software Engineer at Sample Labs | 2022 - Present
            - Built backend APIs with Python and FastAPI.
            - Developed dashboards with React and SQL.

            EDUCATION
            Bachelor of Science in Computer Science

            PROJECTS
            Resume Analyzer
            - Built a resume analysis tool using Python and React.
            """,
        )

        status_code, body = self._call_upload(file)

        self.assertEqual(status_code, 200, body)
        self.assertTrue(body["success"])
        self.assertIn("file_id", body)
        self.assertIn("analysis", body)
        self.assertIn("overall_insights", body["analysis"])
        self.assertIn("metrics", body["analysis"])
        self.assertIn("role_matches", body["analysis"])
        self.assertIn("next_actions", body["analysis"])

    def test_non_resume_upload_returns_422_and_stops_before_analysis(self):
        file = self._docx_upload(
            "technical_document.docx",
            """
            n8n Windows Installation Guide

            This setup guide explains how to install n8n on Windows using Node.js,
            npm, Docker, and PowerShell.

            Step-by-step instructions
            1. Install Node.js.
            2. Open PowerShell as administrator.
            3. Run the following command:
            npm install n8n -g
            docker run -p 5678:5678 n8nio/n8n

            Troubleshooting
            Check PATH configuration if commands fail.
            """,
        )

        with patch.object(upload_route.parser, "parse_text", wraps=upload_route.parser.parse_text) as parse_text, \
             patch.object(upload_route.analyzer, "generate_analysis", wraps=upload_route.analyzer.generate_analysis) as generate_analysis:
            status_code, body = self._call_upload(file)

        self.assertEqual(status_code, 422, body)
        self.assertFalse(body["success"])
        self.assertEqual(body["error"], "resume_validation_failed")
        self.assertIn("validation", body)
        self.assertFalse(body["validation"]["valid"])
        self.assertNotIn("analysis", body)
        parse_text.assert_not_called()
        generate_analysis.assert_not_called()
        self.assertEqual([], list(self.analysis_dir.glob("*.json")))
        self.assertEqual({}, upload_route.latest_analysis)


if __name__ == "__main__":
    unittest.main()
