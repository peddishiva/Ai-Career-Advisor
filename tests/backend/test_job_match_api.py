"""
API-level regression tests for Phase 2C deterministic job matching.
"""

import json
import asyncio
import sys
import tempfile
import unittest
import uuid
from io import BytesIO
from pathlib import Path

from docx import Document
from starlette.datastructures import UploadFile

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
tests_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(tests_path))

from config.job_description_config import MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES
from routes import job_match as job_match_route
from job_description_fixtures import N8N_INSTALL_GUIDE
from job_match_fixtures import (
    BACKEND_EXPERIENCE_JD,
    PROJECT_ONLY_BACKEND_RESUME,
    SOFTWARE_ENGINEER_JD,
    SOFTWARE_ENGINEER_RESUME,
    parsed_resume,
)


UNCERTAIN_JD = """
Software Engineer
Company: Example Corp
Location: Remote
Required: build internal tools.
"""


class TestJobMatchAPI(unittest.TestCase):
    """Verify the Phase 2C route uses stored resume evidence and the JD pipeline."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.analysis_dir = Path(self.temp_dir.name) / "analysis"
        self.analysis_dir.mkdir(parents=True)
        self.previous_analysis_dir = job_match_route.job_match_api_service.analysis_dir
        job_match_route.job_match_api_service.analysis_dir = self.analysis_dir

    def tearDown(self):
        job_match_route.job_match_api_service.analysis_dir = self.previous_analysis_dir
        self.temp_dir.cleanup()

    def _store_resume(self, resume_text: str) -> str:
        resume_id = str(uuid.uuid4())
        parsed = parsed_resume(resume_text)
        parsed.pop("raw_text", None)
        with (self.analysis_dir / f"{resume_id}.json").open("w", encoding="utf-8") as handle:
            json.dump({"parsed_resume": parsed}, handle)
        return resume_id

    def _post_json(self, payload: dict) -> tuple[int, dict]:
        response = asyncio.run(
            job_match_route.match_resume_to_job(
                _JSONRequest(payload),
                resume_id=None,
                job_description=None,
                file=None,
            )
        )
        return response.status_code, json.loads(response.body.decode("utf-8"))

    def _post_file(self, resume_id: str, filename: str, content: bytes, content_type: str) -> tuple[int, dict]:
        upload = UploadFile(file=BytesIO(content), filename=filename)
        response = asyncio.run(
            job_match_route.match_resume_to_job(
                _FormRequest(),
                resume_id=resume_id,
                job_description=None,
                file=upload,
            )
        )
        return response.status_code, json.loads(response.body.decode("utf-8"))

    def _post_text_and_file(self, resume_id: str, job_description: str, filename: str, content: bytes) -> tuple[int, dict]:
        upload = UploadFile(file=BytesIO(content), filename=filename)
        response = asyncio.run(
            job_match_route.match_resume_to_job(
                _FormRequest(),
                resume_id=resume_id,
                job_description=job_description,
                file=upload,
            )
        )
        return response.status_code, json.loads(response.body.decode("utf-8"))

    def _store_malformed_analysis(self) -> str:
        resume_id = str(uuid.uuid4())
        with (self.analysis_dir / f"{resume_id}.json").open("w", encoding="utf-8") as handle:
            json.dump({"analysis": {"score": 90}}, handle)
        return resume_id

    def _docx_bytes(self, text: str) -> bytes:
        document = Document()
        for line in text.strip().splitlines():
            document.add_paragraph(line.strip())

        payload = BytesIO()
        document.save(payload)
        return payload.getvalue()

    def test_valid_resume_and_valid_jd_returns_match(self):
        resume_id = self._store_resume(SOFTWARE_ENGINEER_RESUME)

        status_code, body = self._post_json({"resume_id": resume_id, "job_description": SOFTWARE_ENGINEER_JD})

        self.assertEqual(200, status_code, body)
        self.assertTrue(body["success"])
        self.assertEqual("Job match analysis completed successfully", body["message"])
        self.assertEqual("Software Engineer", body["job"]["job_title"])
        self.assertIn("match", body)
        self.assertGreaterEqual(body["match"]["score"], 75)
        self.assertEqual("HIGH", body["match"]["readiness"])

    def test_valid_resume_and_valid_multipart_jd_file_returns_match(self):
        resume_id = self._store_resume(SOFTWARE_ENGINEER_RESUME)
        content = self._docx_bytes(SOFTWARE_ENGINEER_JD)
        self.assertLess(len(content), MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES)

        status_code, body = self._post_file(
            resume_id,
            "software_engineer_jd.docx",
            content,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        self.assertEqual(200, status_code, body)
        self.assertTrue(body["success"])
        self.assertEqual(resume_id, body["resume_id"])
        self.assertEqual("Software Engineer", body["job"]["job_title"])

    def test_valid_resume_and_invalid_jd_returns_422_without_match(self):
        resume_id = self._store_resume(SOFTWARE_ENGINEER_RESUME)

        status_code, body = self._post_json({"resume_id": resume_id, "job_description": N8N_INSTALL_GUIDE})

        self.assertEqual(422, status_code, body)
        self.assertFalse(body["success"])
        self.assertEqual("not_a_job_description", body["error"])
        self.assertNotIn("match", body)

    def test_missing_resume_returns_400_without_matching(self):
        status_code, body = self._post_json({"job_description": SOFTWARE_ENGINEER_JD})

        self.assertEqual(400, status_code, body)
        self.assertFalse(body["success"])
        self.assertEqual("missing_resume", body["error"])
        self.assertNotIn("match", body)

    def test_missing_jd_returns_400_without_matching(self):
        resume_id = self._store_resume(SOFTWARE_ENGINEER_RESUME)

        status_code, body = self._post_json({"resume_id": resume_id})

        self.assertEqual(400, status_code, body)
        self.assertFalse(body["success"])
        self.assertEqual("missing_job_description", body["error"])
        self.assertNotIn("match", body)

    def test_text_and_file_together_returns_400_without_matching(self):
        resume_id = self._store_resume(SOFTWARE_ENGINEER_RESUME)

        status_code, body = self._post_text_and_file(
            resume_id,
            SOFTWARE_ENGINEER_JD,
            "software_engineer_jd.docx",
            self._docx_bytes(SOFTWARE_ENGINEER_JD),
        )

        self.assertEqual(400, status_code, body)
        self.assertFalse(body["success"])
        self.assertEqual("multiple_job_description_inputs", body["error"])
        self.assertNotIn("match", body)

    def test_invalid_resume_id_returns_404_without_matching(self):
        status_code, body = self._post_json({"resume_id": "../bad", "job_description": SOFTWARE_ENGINEER_JD})

        self.assertEqual(404, status_code, body)
        self.assertFalse(body["success"])
        self.assertEqual("invalid_resume_id", body["error"])
        self.assertNotIn("match", body)

    def test_missing_stored_analysis_returns_404_without_matching(self):
        missing_resume_id = str(uuid.uuid4())

        status_code, body = self._post_json({"resume_id": missing_resume_id, "job_description": SOFTWARE_ENGINEER_JD})

        self.assertEqual(404, status_code, body)
        self.assertFalse(body["success"])
        self.assertEqual("resume_not_found", body["error"])
        self.assertNotIn("match", body)

    def test_malformed_stored_analysis_returns_422_without_matching(self):
        resume_id = self._store_malformed_analysis()

        status_code, body = self._post_json({"resume_id": resume_id, "job_description": SOFTWARE_ENGINEER_JD})

        self.assertEqual(422, status_code, body)
        self.assertFalse(body["success"])
        self.assertEqual("resume_not_analyzed", body["error"])
        self.assertNotIn("match", body)

    def test_uncertain_jd_returns_422_without_match(self):
        resume_id = self._store_resume(SOFTWARE_ENGINEER_RESUME)

        status_code, body = self._post_json({"resume_id": resume_id, "job_description": UNCERTAIN_JD})

        self.assertEqual(422, status_code, body)
        self.assertFalse(body["success"])
        self.assertEqual("uncertain_job_description", body["error"])
        self.assertNotIn("match", body)

    def test_corrupted_or_unsupported_jd_file_returns_error(self):
        resume_id = self._store_resume(SOFTWARE_ENGINEER_RESUME)

        unsupported_status, unsupported_body = self._post_file(
            resume_id,
            "job.txt",
            b"not a supported jd document",
            "text/plain",
        )
        corrupted_status, corrupted_body = self._post_file(
            resume_id,
            "job.docx",
            b"not a real docx payload",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        self.assertEqual(400, unsupported_status, unsupported_body)
        self.assertEqual("unsupported_job_description_document", unsupported_body["error"])
        self.assertEqual(400, corrupted_status, corrupted_body)
        self.assertEqual("corrupted_job_description_document", corrupted_body["error"])

    def test_jd_file_size_limit_accepts_below_limit_and_rejects_above_limit(self):
        resume_id = self._store_resume(SOFTWARE_ENGINEER_RESUME)
        valid_content = self._docx_bytes(SOFTWARE_ENGINEER_JD)
        oversized_content = b"x" * (MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES + 1)

        accepted_status, accepted_body = self._post_file(
            resume_id,
            "software_engineer_jd.docx",
            valid_content,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        rejected_status, rejected_body = self._post_file(
            resume_id,
            "oversized_jd.docx",
            oversized_content,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        self.assertEqual(200, accepted_status, accepted_body)
        self.assertEqual(413, rejected_status, rejected_body)
        self.assertFalse(rejected_body["success"])
        self.assertEqual("job_description_file_too_large", rejected_body["error"])
        self.assertNotIn("match", rejected_body)

    def test_project_only_resume_preserves_professional_experience_gap(self):
        resume_id = self._store_resume(PROJECT_ONLY_BACKEND_RESUME)

        status_code, body = self._post_json({"resume_id": resume_id, "job_description": BACKEND_EXPERIENCE_JD})

        self.assertEqual(200, status_code, body)
        self.assertGreater(body["match"]["project_alignment"]["score"], 0)
        self.assertEqual("insufficient_evidence", body["match"]["experience_alignment"]["status"])
        self.assertTrue(any(gap["type"] == "experience" for gap in body["match"]["critical_gaps"]))

    def test_same_resume_and_jd_repeated_returns_identical_response(self):
        resume_id = self._store_resume(SOFTWARE_ENGINEER_RESUME)
        payload = {"resume_id": resume_id, "job_description": SOFTWARE_ENGINEER_JD}

        first_status, first_body = self._post_json(payload)
        second_status, second_body = self._post_json(payload)

        self.assertEqual(200, first_status, first_body)
        self.assertEqual(200, second_status, second_body)
        self.assertEqual(first_body, second_body)


class _JSONRequest:
    def __init__(self, payload: dict):
        self.headers = {"content-type": "application/json"}
        self.payload = payload

    async def json(self) -> dict:
        return self.payload


class _FormRequest:
    headers: dict = {}


if __name__ == "__main__":
    unittest.main()
