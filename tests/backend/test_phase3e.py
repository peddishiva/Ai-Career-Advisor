"""Phase 3E release-hardening and security regression tests."""

import asyncio
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from docx import Document
from fastapi import HTTPException

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from config.ai_config import AIProviderConfig
from config.security_config import load_cors_origins
from routes import analysis as analysis_route
from routes import jobs as jobs_route
from services.analysis_service import AnalysisService
from services.file_upload_service import (
    InvalidUploadContentError,
    sanitize_upload_filename,
    validate_document_content,
)
from services.job_match_api_service import JobMatchAPIService, JobMatchAPIError
from services.ai_request_guard import AIRequestGuard


class TestPhase3ESecurity(unittest.TestCase):
    def test_filename_and_document_signatures_are_checked(self):
        self.assertEqual("resume.docx", sanitize_upload_filename(r"..\private\resume.docx"))
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid = Path(temp_dir) / "resume.docx"
            invalid.write_bytes(b"not a docx")
            with self.assertRaises(InvalidUploadContentError):
                validate_document_content(invalid, ".docx")

            valid = Path(temp_dir) / "valid.docx"
            document = Document()
            document.add_paragraph("Candidate resume")
            document.save(valid)
            validate_document_content(valid, ".docx")

    def test_docx_archive_paths_and_macros_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            unsafe = Path(temp_dir) / "unsafe.docx"
            with zipfile.ZipFile(unsafe, "w") as archive:
                archive.writestr("[Content_Types].xml", "content")
                archive.writestr("../outside.txt", "unsafe")
                archive.writestr("word/document.xml", "document")
            with self.assertRaises(InvalidUploadContentError):
                validate_document_content(unsafe, ".docx")

            macro = Path(temp_dir) / "macro.docx"
            with zipfile.ZipFile(macro, "w") as archive:
                archive.writestr("[Content_Types].xml", "content")
                archive.writestr("word/document.xml", "document")
                archive.writestr("word/vbaProject.bin", "macro")
            with self.assertRaises(InvalidUploadContentError):
                validate_document_content(macro, ".docx")

    def test_oversized_pasted_jd_is_rejected(self):
        with self.assertRaises(JobMatchAPIError) as error:
            JobMatchAPIService()._job_description_text("x" * (5 * 1024 * 1024 + 1), None)
        self.assertEqual(413, error.exception.status_code)
        self.assertEqual("job_description_too_large", error.exception.payload["error"])

    def test_analysis_reads_require_an_explicit_file_id(self):
        with self.assertRaises(HTTPException) as read_error:
            asyncio.run(analysis_route.get_analysis())
        with self.assertRaises(HTTPException) as summary_error:
            asyncio.run(analysis_route.get_analysis_summary())
        with self.assertRaises(HTTPException) as ai_error:
            asyncio.run(analysis_route.generate_analysis_ai())
        self.assertEqual(422, read_error.exception.status_code)
        self.assertEqual(422, summary_error.exception.status_code)
        self.assertEqual(422, ai_error.exception.status_code)

    def test_analysis_payload_does_not_retain_contact_fields(self):
        analysis = AnalysisService().generate_analysis(
            {
                "name": "Private Candidate",
                "email": "private@example.com",
                "phone": "+1 555 555 5555",
                "skills": [],
                "experience": [],
                "education": [],
                "projects": [],
            }
        )
        self.assertNotIn("name", analysis["candidate_info"])
        self.assertNotIn("email", analysis["candidate_info"])
        self.assertNotIn("phone", analysis["candidate_info"])

    def test_job_recommendations_keep_key_out_of_url_and_bound_output(self):
        config = AIProviderConfig(
            enabled=True,
            provider_name="gemini",
            max_output_tokens=4_000,
            timeout_seconds=30,
            api_key_env_var="PHASE3E_TEST_KEY",
        )
        response = Mock(status_code=200)
        response.json.return_value = {
            "candidates": [{
                "content": {"parts": [{"text": json.dumps([
                    {"title": "Engineer", "company": "Example", "location": "Remote", "salary": "N/A", "description": "Build systems"}
                    for _ in range(20)
                ])}]}
            }]
        }
        with patch.dict(os.environ, {"PHASE3E_TEST_KEY": "do-not-log"}, clear=False), patch(
            "routes.jobs.requests.post", return_value=response
        ) as post:
            jobs = asyncio.run(jobs_route.call_gemini_for_jobs("safe prompt", config=config))
        self.assertEqual(8, len(jobs))
        self.assertNotIn("key=", post.call_args.args[0])
        self.assertEqual("do-not-log", post.call_args.kwargs["headers"]["x-goog-api-key"])
        self.assertLessEqual(post.call_args.kwargs["timeout"], 15.0)

    def test_job_recommendations_fail_closed_without_ai(self):
        with patch.dict(os.environ, {"AI_ENABLED": "false", "GEMINI_API_KEY": "placeholder"}, clear=False):
            response = asyncio.run(jobs_route.get_job_recommendations())
        self.assertEqual(503, response.status_code)
        body = json.loads(response.body.decode("utf-8"))
        self.assertEqual("ai_unavailable", body["error"])
        self.assertNotIn("placeholder", response.body.decode("utf-8"))

    def test_request_guard_is_scoped_and_non_persistent(self):
        guard = AIRequestGuard(cooldown_seconds=60)
        self.assertTrue(guard.allow("resume_analysis", "resume-a", "resume_improvement", "hash"))
        self.assertFalse(guard.allow("resume_analysis", "resume-a", "resume_improvement", "hash"))
        self.assertTrue(guard.allow("resume_analysis", "resume-b", "resume_improvement", "hash"))
        self.assertTrue(guard.allow("jdxr", "resume-a", "resume_improvement", "hash"))

    def test_cors_is_an_explicit_allowlist(self):
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "http://localhost:3013,https://career.example"}, clear=False):
            self.assertEqual(
                ["http://localhost:3013", "https://career.example"],
                load_cors_origins(),
            )

    def test_public_test_page_does_not_inject_html(self):
        page = (Path(__file__).resolve().parents[2] / "frontend" / "public" / "test-connection.html").read_text(encoding="utf-8")
        self.assertNotIn("resultDiv.innerHTML", page)
        self.assertNotIn("dangerouslySetInnerHTML", page)


if __name__ == "__main__":
    unittest.main()
