"""API and storage isolation tests for the Phase 2.5 JDxR workflow."""

import asyncio
import json
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from docx import Document
from starlette.datastructures import UploadFile

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
tests_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(tests_path))

from config.job_description_config import MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES
from config.upload_config import MAX_RESUME_FILE_SIZE_BYTES
from job_description_fixtures import DATA_ANALYST_JD, N8N_INSTALL_GUIDE, SOFTWARE_ENGINEER_JD
from job_match_fixtures import SOFTWARE_ENGINEER_RESUME
from routes import jdxr as jdxr_route
from services.jdxr_session_service import JdxrSessionService
from routes import upload as upload_route


class TestJdxrAPI(unittest.TestCase):
    """Verify JDxR sessions do not reuse Resume Analysis state or each other."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.temp_dir.name) / "jdxr"
        self.previous_service = jdxr_route.jdxr_session_service
        jdxr_route.jdxr_session_service = JdxrSessionService(root_dir=self.root_dir)
        self.previous_analysis = upload_route.latest_analysis

    def tearDown(self):
        upload_route.latest_analysis = self.previous_analysis
        jdxr_route.jdxr_session_service = self.previous_service
        self.temp_dir.cleanup()

    def _create(self) -> tuple[int, dict]:
        response = asyncio.run(jdxr_route.create_jdxr_session())
        return response.status_code, json.loads(response.body.decode("utf-8"))

    def _get(self, session_id: str) -> tuple[int, dict]:
        response = asyncio.run(jdxr_route.get_jdxr_session(session_id))
        return response.status_code, json.loads(response.body.decode("utf-8"))

    def _submit_jd_text(self, session_id: str, text: str) -> tuple[int, dict]:
        response = asyncio.run(
            jdxr_route.submit_jdxr_jd(
                session_id,
                _JSONRequest({"job_description": text}),
                job_description=None,
                file=None,
            )
        )
        return response.status_code, json.loads(response.body.decode("utf-8"))

    def _submit_jd_file(self, session_id: str, filename: str, content: bytes) -> tuple[int, dict]:
        upload = UploadFile(file=BytesIO(content), filename=filename)
        response = asyncio.run(
            jdxr_route.submit_jdxr_jd(
                session_id,
                _FormRequest(),
                job_description=None,
                file=upload,
            )
        )
        return response.status_code, json.loads(response.body.decode("utf-8"))

    def _submit_resume_file(self, session_id: str, filename: str, content: bytes) -> tuple[int, dict]:
        upload = UploadFile(file=BytesIO(content), filename=filename)
        response = asyncio.run(jdxr_route.submit_jdxr_resume(session_id, upload))
        return response.status_code, json.loads(response.body.decode("utf-8"))

    def _analyze(self, session_id: str) -> tuple[int, dict]:
        response = asyncio.run(jdxr_route.analyze_jdxr_session(session_id))
        return response.status_code, json.loads(response.body.decode("utf-8"))

    def _docx_bytes(self, text: str) -> bytes:
        document = Document()
        for line in text.strip().splitlines():
            document.add_paragraph(line.strip())
        payload = BytesIO()
        document.save(payload)
        return payload.getvalue()

    def test_create_session_persists_isolated_storage(self):
        status, body = self._create()

        self.assertEqual(201, status, body)
        self.assertTrue(body["success"])
        session_id = body["session"]["session_id"]
        session_dir = self.root_dir / session_id
        self.assertTrue((session_dir / "session.json").exists())
        self.assertTrue((session_dir / "jd").is_dir())
        self.assertTrue((session_dir / "resume").is_dir())
        self.assertEqual("created", body["session"]["status"])
        self.assertNotIn("parsed_resume", body["session"])
        self.assertNotIn("parsed_jd", body["session"])

    def test_jd_validation_is_sequential_and_rejects_non_jd(self):
        _, created = self._create()
        session_id = created["session"]["session_id"]

        before_resume_status, before_resume = self._analyze(session_id)
        self.assertEqual(409, before_resume_status, before_resume)
        self.assertEqual("jd_required", before_resume["error"])

        invalid_status, invalid = self._submit_jd_text(session_id, N8N_INSTALL_GUIDE)
        self.assertEqual(422, invalid_status, invalid)
        self.assertEqual("not_a_job_description", invalid["error"])
        self.assertEqual("invalid", invalid["session"]["jd"]["status"])
        self.assertEqual([], list((self.root_dir / session_id / "jd").iterdir()))

        valid_status, valid = self._submit_jd_text(session_id, SOFTWARE_ENGINEER_JD)
        self.assertEqual(200, valid_status, valid)
        self.assertEqual("valid", valid["session"]["jd"]["status"])
        self.assertEqual("Software Engineer", valid["session"]["jd"]["job_title"])
        self.assertGreater(valid["session"]["jd"]["required_count"], 0)

    def test_jd_docx_upload_successfully_validates_and_parses(self):
        _, created = self._create()
        session_id = created["session"]["session_id"]

        status, body = self._submit_jd_file(session_id, "software-engineer.docx", self._docx_bytes(SOFTWARE_ENGINEER_JD))

        self.assertEqual(200, status, body)
        self.assertEqual("valid", body["session"]["jd"]["status"])
        self.assertEqual("software-engineer.docx", body["session"]["jd"]["filename"])
        self.assertTrue(list((self.root_dir / session_id / "jd").iterdir()))

    def test_resume_validation_requires_valid_jd_and_rejects_non_resume(self):
        _, created = self._create()
        session_id = created["session"]["session_id"]
        resume_bytes = self._docx_bytes(SOFTWARE_ENGINEER_RESUME)

        missing_jd_status, missing_jd = self._submit_resume_file(session_id, "resume.docx", resume_bytes)
        self.assertEqual(409, missing_jd_status, missing_jd)
        self.assertEqual("jd_required", missing_jd["error"])

        self._submit_jd_text(session_id, SOFTWARE_ENGINEER_JD)
        invalid_status, invalid = self._submit_resume_file(session_id, "guide.docx", self._docx_bytes(N8N_INSTALL_GUIDE))
        self.assertEqual(422, invalid_status, invalid)
        self.assertEqual("resume_validation_failed", invalid["error"])
        self.assertEqual("invalid", invalid["session"]["resume"]["status"])

        valid_status, valid = self._submit_resume_file(session_id, "resume.docx", resume_bytes)
        self.assertEqual(200, valid_status, valid)
        self.assertEqual("valid", valid["session"]["resume"]["status"])
        self.assertGreaterEqual(valid["session"]["resume"]["experience_count"], 1)

    def test_full_compare_is_json_serializable_and_repeatable(self):
        _, created = self._create()
        session_id = created["session"]["session_id"]
        self._submit_jd_text(session_id, SOFTWARE_ENGINEER_JD)
        self._submit_resume_file(session_id, "resume.docx", self._docx_bytes(SOFTWARE_ENGINEER_RESUME))

        first_status, first = self._analyze(session_id)
        second_status, second = self._analyze(session_id)

        self.assertEqual(200, first_status, first)
        self.assertEqual(200, second_status, second)
        self.assertEqual(first["job"], second["job"])
        self.assertEqual(first["match"], second["match"])
        json.dumps(first)
        self.assertTrue(first["session"]["has_match_result"])
        self.assertIn("match", first)

    def test_sessions_keep_jd_resume_and_match_results_separate(self):
        _, first_created = self._create()
        _, second_created = self._create()
        first_id = first_created["session"]["session_id"]
        second_id = second_created["session"]["session_id"]

        self._submit_jd_text(first_id, SOFTWARE_ENGINEER_JD)
        self._submit_jd_text(second_id, DATA_ANALYST_JD)
        resume_bytes = self._docx_bytes(SOFTWARE_ENGINEER_RESUME)
        self._submit_resume_file(first_id, "software.docx", resume_bytes)
        self._submit_resume_file(second_id, "data.docx", resume_bytes)

        first_status, first = self._analyze(first_id)
        second_status, second = self._analyze(second_id)
        self.assertEqual(200, first_status, first)
        self.assertEqual(200, second_status, second)
        self.assertNotEqual(first["session"]["session_id"], second["session"]["session_id"])
        self.assertNotEqual(first["job"]["job_title"], second["job"]["job_title"])
        self.assertNotEqual(first["match"], second["match"])

        first_state_status, first_state = self._get(first_id)
        second_state_status, second_state = self._get(second_id)
        self.assertEqual(200, first_state_status, first_state)
        self.assertEqual(200, second_state_status, second_state)
        self.assertEqual("software.docx", first_state["session"]["resume"]["filename"])
        self.assertEqual("data.docx", second_state["session"]["resume"]["filename"])

    def test_resume_upload_does_not_replace_resume_analysis_state(self):
        previous = {"metadata": {"filename": "existing.pdf"}, "score": 81}
        upload_route.latest_analysis = previous
        _, created = self._create()
        session_id = created["session"]["session_id"]
        self._submit_jd_text(session_id, SOFTWARE_ENGINEER_JD)

        status, body = self._submit_resume_file(session_id, "resume.docx", self._docx_bytes(SOFTWARE_ENGINEER_RESUME))

        self.assertEqual(200, status, body)
        self.assertEqual(previous, upload_route.latest_analysis)

    def test_invalid_session_and_upload_limits_return_safe_errors(self):
        invalid_status, invalid = self._get("../escape")
        self.assertEqual(404, invalid_status, invalid)
        self.assertEqual("invalid_session_id", invalid["error"])

        _, created = self._create()
        session_id = created["session"]["session_id"]
        unsupported_status, unsupported = self._submit_jd_file(session_id, "job.txt", b"text")
        self.assertEqual(400, unsupported_status, unsupported)
        self.assertEqual("unsupported_job_description_document", unsupported["error"])

        oversized_jd_status, oversized_jd = self._submit_jd_file(
            session_id,
            "large.docx",
            b"x" * (MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES + 1),
        )
        self.assertEqual(413, oversized_jd_status, oversized_jd)
        self.assertEqual("job_description_file_too_large", oversized_jd["error"])

        self._submit_jd_text(session_id, SOFTWARE_ENGINEER_JD)
        oversized_resume_status, oversized_resume = self._submit_resume_file(
            session_id,
            "large.docx",
            b"x" * (MAX_RESUME_FILE_SIZE_BYTES + 1),
        )
        self.assertEqual(413, oversized_resume_status, oversized_resume)
        self.assertEqual("resume_file_too_large", oversized_resume["error"])


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
