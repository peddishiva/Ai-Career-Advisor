"""Phase 4C Authenticated AI Guidance and Grounded Resume Improvements tests.

Verifies:
1. Unauthenticated requests are rejected (401).
2. Invalid or expired tokens are rejected (401).
3. Nonexistent resume IDs return 404.
4. User A cannot access User B's AI guidance or improvements (IDOR isolation -> 404).
5. Client-supplied user_id or scope parameters cannot override the verified token subject.
6. Malformed requests and oversized inputs are rejected (422).
7. Provider disabled status returns safely without mutating deterministic analysis.
8. Valid structured guidance and improvements are accepted, validated, and persisted.
9. Grounding and evidence validation reject ungrounded claims.
10. Target job description alignment evaluates against provided JD without mutating deterministic scores.
11. Request guard enforces rate limiting / cooldown (429).
12. Provider unavailability / exceptions are safely normalized without leaking secrets.
13. Resume deletion cascades and removes persisted guidance.
"""

from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from docx import Document
from fastapi.testclient import TestClient
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from ai.contracts import (
    AIAction,
    AIInsight,
    AIResponse,
    AIResponseStatus,
    AITaskType,
    ImprovementActionType,
    ImprovementCategory,
    ImprovementFactStatus,
    ImprovementItem,
    ImprovementPriority,
)
from ai.provider import AIProvider
from api.v1.resumes import ai_enrichment_service, ai_request_guard, get_storage_service  # noqa: E402
from auth.dependencies import get_auth_verifier  # noqa: E402
from auth.jwt_verifier import JWTVerifier  # noqa: E402
from config.auth_config import AuthConfig  # noqa: E402
from config.storage_config import StorageConfig  # noqa: E402
from db.base import Base  # noqa: E402
from db.models import Resume, ResumeAnalysis, StorageCleanupJob  # noqa: E402
from db.repositories import ResumeRepository  # noqa: E402
from db.session import get_db  # noqa: E402
import db.session as session_module  # noqa: E402
from main import app  # noqa: E402
from routes import upload as upload_route  # noqa: E402
from routes import analysis as analysis_route  # noqa: E402
from services.storage_service import LocalStorageAdapter  # noqa: E402


def _create_sqlite_test_engine(db_path: Path):
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


VALID_RESUME_TEXT = """
Jane Doe
jane.doe@example.com | +1 555-019-2831

SUMMARY
Experienced software engineer with 5 years building backend services and APIs.

TECHNICAL SKILLS
Python, FastAPI, SQL, PostgreSQL, Docker, Git, REST APIs, Microservices

PROFESSIONAL EXPERIENCE
Senior Software Engineer at Acme Corp | 2021 - Present
- Designed and implemented RESTful microservices in Python using FastAPI.
- Optimized PostgreSQL queries and database schemas for high-throughput transactions.

Software Engineer at Tech Innovations | 2019 - 2021
- Built core backend components using Python and Flask.
- Collaborated with frontend engineers to integrate React applications.

EDUCATION
Bachelor of Science in Computer Science | State University | 2015 - 2019

PROJECTS
Cloud Portal Architecture
- Designed scalable user-owned resume persistence service with strict tenant isolation.
"""


def _create_docx_bytes(text: str = VALID_RESUME_TEXT) -> bytes:
    doc = Document()
    for line in text.strip().splitlines():
        doc.add_paragraph(line.strip())
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()


class MockAIProvider(AIProvider):
    def __init__(self, response_generator=None):
        self.response_generator = response_generator
        self.call_count = 0
        self.last_request = None

    def provider_name(self) -> str:
        return "mock"

    def model_name(self) -> str:
        return "mock-model"

    def generate(self, request):
        self.call_count += 1
        self.last_request = request
        if self.response_generator:
            return self.response_generator(request)
        return AIResponse(
            status=AIResponseStatus.COMPLETE,
            summary="Strong backend engineering profile with clear Python and database evidence.",
            strengths=[
                AIInsight(
                    text="Demonstrates Python capability.",
                    evidence_reference_ids=["RESUME-SKILL-001"],
                )
            ],
            priority_gaps=[],
            learning_actions=[],
            resume_actions=[],
            interview_actions=[],
            confidence_notes=["Based on verified resume content."],
        )


class TestPhase4CAIGuidance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.config = AuthConfig(
            issuer="https://phase4c-test.supabase.co/auth/v1",
            audience="authenticated",
            jwks_url="https://phase4c-test.supabase.co/auth/v1/.well-known/jwks.json",
            algorithms=("RS256",),
        )
        cls.verifier = JWTVerifier(
            config=cls.config,
            signing_key_resolver=lambda _token: cls.private_key.public_key(),
        )
        cls.docx_bytes = _create_docx_bytes()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)

        # Database setup
        self.db_path = temp_path / "test_resumes.db"
        self.engine = _create_sqlite_test_engine(self.db_path)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

        # Storage setup
        self.storage_root = temp_path / "private_storage"
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.storage_config = StorageConfig(
            local_root=self.storage_root,
            max_object_bytes=10 * 1024 * 1024,
        )
        self.storage_service = LocalStorageAdapter(
            self.storage_config,
            signing_key=b"test-secret-signing-key-0123456789",
        )

        self.session_local_patch = patch.object(session_module, "SessionLocal", self.Session)
        self.session_local_patch.start()

        def override_db():
            session = self.Session()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_auth_verifier] = lambda: self.verifier
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_storage_service] = lambda: self.storage_service

        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()
        self.session_local_patch.stop()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _issue_token(
        self,
        user_id: str,
        email: str = "user@example.com",
        expires_in: int = 3600,
        private_key=None,
    ) -> str:
        key = private_key or self.private_key
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "aud": "authenticated",
            "iss": "https://phase4c-test.supabase.co/auth/v1",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        }
        return jwt.encode(payload, key, algorithm="RS256")

    def _upload_resume(self, token: str, filename: str = "resume.docx") -> dict:
        response = self.client.post(
            "/api/v1/resumes",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (filename, self.docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_unauthenticated_requests_rejected(self):
        """Unauthenticated requests to AI endpoints must be rejected with 401."""
        resume_id = "00000000-0000-0000-0000-000000000001"
        res1 = self.client.post(f"/api/v1/resumes/{resume_id}/ai")
        self.assertEqual(res1.status_code, 401)
        self.assertIn("WWW-Authenticate", res1.headers)

        res2 = self.client.post(f"/api/v1/resumes/{resume_id}/ai/improvements")
        self.assertEqual(res2.status_code, 401)

        res3 = self.client.get(f"/api/v1/resumes/{resume_id}/ai")
        self.assertEqual(res3.status_code, 401)

    def test_invalid_or_expired_token_rejected(self):
        """Invalid or expired JWTs must be rejected with 401."""
        resume_id = "00000000-0000-0000-0000-000000000001"
        expired_token = self._issue_token("user-1", expires_in=-10)
        res = self.client.post(
            f"/api/v1/resumes/{resume_id}/ai",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        self.assertEqual(res.status_code, 401)

        forged_token = self._issue_token("user-1", private_key=self.other_private_key)
        res2 = self.client.post(
            f"/api/v1/resumes/{resume_id}/ai",
            headers={"Authorization": f"Bearer {forged_token}"},
        )
        self.assertEqual(res2.status_code, 401)

    def test_nonexistent_resume_returns_404(self):
        """Requesting AI guidance for a non-existent resume returns 404."""
        token = self._issue_token("user-owner")
        res = self.client.post(
            "/api/v1/resumes/nonexistent-resume-id/ai",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 404)
        self.assertIn("Resume not found", res.json()["detail"])

    def test_idor_isolation_cross_user_access_blocked(self):
        """User B cannot request or view User A's resume AI guidance (IDOR isolation)."""
        token_a = self._issue_token("user-a", email="a@example.com")
        token_b = self._issue_token("user-b", email="b@example.com")

        upload_data = self._upload_resume(token_a)
        resume_id_a = upload_data["file_id"]

        # User B attempts to trigger AI guidance on User A's resume
        res = self.client.post(
            f"/api/v1/resumes/{resume_id_a}/ai",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        self.assertEqual(res.status_code, 404)

        # User B attempts to trigger AI improvements on User A's resume
        res_imp = self.client.post(
            f"/api/v1/resumes/{resume_id_a}/ai/improvements",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        self.assertEqual(res_imp.status_code, 404)

        # User B attempts to read User A's persisted AI guidance
        res_get = self.client.get(
            f"/api/v1/resumes/{resume_id_a}/ai",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        self.assertEqual(res_get.status_code, 404)

    def test_client_supplied_user_id_ignored(self):
        """Client-supplied user_id in request payload or query cannot bypass authenticated user scope."""
        token_a = self._issue_token("user-a")
        upload_data = self._upload_resume(token_a)
        resume_id_a = upload_data["file_id"]

        # An attacker attempts to inject user_id or spoof ownership
        res = self.client.post(
            f"/api/v1/resumes/{resume_id_a}/ai",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"task": "resume_career_guidance", "user_id": "other-user"},
        )
        # Extra field "user_id" is forbidden by Pydantic model
        self.assertEqual(res.status_code, 422)

    def test_malformed_request_body_rejected(self):
        """Malformed task types or invalid request structures return 422."""
        token = self._issue_token("user-valid")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        res = self.client.post(
            f"/api/v1/resumes/{resume_id}/ai",
            headers={"Authorization": f"Bearer {token}"},
            json={"task": "invalid_nonexistent_task"},
        )
        self.assertEqual(res.status_code, 422)

        # Oversized target job description (>10,000 chars) rejected
        res2 = self.client.post(
            f"/api/v1/resumes/{resume_id}/ai",
            headers={"Authorization": f"Bearer {token}"},
            json={"target_job_description": "x" * 15_000},
        )
        self.assertEqual(res2.status_code, 422)

    def test_ai_guidance_disabled_mode(self):
        """When AI is disabled, returns ai_status='disabled' and preserves deterministic scores."""
        token = self._issue_token("user-disabled")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        # By default AI_ENABLED is False
        res = self.client.post(
            f"/api/v1/resumes/{resume_id}/ai",
            headers={"Authorization": f"Bearer {token}"},
            json={"task": "resume_career_guidance"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["ai_status"], "disabled")
        self.assertIsNone(data["ai"])
        self.assertIn("deterministic_result", data)
        # Deterministic fit_score is preserved intact
        self.assertIsNotNone(data["deterministic_result"]["overall_insights"]["fit_score"])

    def test_ai_guidance_success_and_persistence(self):
        """With enabled orchestrator and valid provider, AI guidance succeeds and persists."""
        token = self._issue_token("user-enabled")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        mock_provider = MockAIProvider()

        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            res = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
                json={"task": "resume_career_guidance"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["ai_status"], "complete")
            self.assertIsNotNone(data["ai"])
            self.assertEqual(mock_provider.call_count, 1)

            # Verify persisted in database
            with self.Session() as session:
                analysis = session.scalar(select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id))
                self.assertIsNotNone(analysis)
                assert analysis is not None
                self.assertIn("ai_guidance", analysis.analysis_data)
                self.assertEqual(analysis.analysis_data["ai_guidance"]["summary"], data["ai"]["summary"])

            # Verify GET /api/v1/resumes/{resume_id}/ai returns persisted guidance
            get_res = self.client.get(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(get_res.status_code, 200)
            get_data = get_res.json()
            self.assertTrue(get_data["success"])
            self.assertIsNotNone(get_data["ai_guidance"])
            self.assertEqual(get_data["ai_guidance"]["summary"], data["ai"]["summary"])

    def test_ai_improvements_success_and_persistence(self):
        """Resume improvements are validated against deterministic opportunities and persisted."""
        token = self._issue_token("user-imp")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        from ai.provider import MockAIProvider as DefaultMockAIProvider

        mock_provider = DefaultMockAIProvider()

        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            res = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai/improvements",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["ai_status"], "complete")
            self.assertIsNotNone(data["ai"])
            self.assertTrue(len(data["ai"]["improvements"]) > 0)

            # Check database persistence
            with self.Session() as session:
                analysis = session.scalar(select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id))
                self.assertIsNotNone(analysis)
                assert analysis is not None
                self.assertIn("ai_improvements", analysis.analysis_data)

    def test_ai_guidance_with_target_job_description(self):
        """Providing a target job description evaluates skill gaps under JDXR flow."""
        token = self._issue_token("user-target-jd")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        target_jd = """
        Job Title: Senior Python Architect
        Required Skills: Python, FastAPI, Kubernetes, GraphQL
        Experience: 5+ years backend systems
        """

        mock_provider = MockAIProvider()

        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            res = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "task": "resume_career_guidance",
                    "target_job_description": target_jd,
                },
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["ai_status"], "complete")
            # Verify the AI request was processed as JDXR flow
            self.assertIsNotNone(mock_provider.last_request)
            assert mock_provider.last_request is not None
            self.assertEqual(mock_provider.last_request.flow_type.value, "jdxr")

    def test_ai_request_guard_cooldown_returns_429(self):
        """Rapid duplicate AI requests within cooldown period return HTTP 429."""
        token = self._issue_token("user-guard")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        mock_provider = MockAIProvider()

        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            # First request succeeds
            res1 = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res1.status_code, 200)

            # Immediate second request triggers cooldown
            res2 = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res2.status_code, 429)
            data2 = res2.json()
            self.assertFalse(data2["success"])
            self.assertEqual(data2["error"], "ai_request_cooldown")

    def test_ai_provider_unavailable_handling(self):
        """When provider fails or times out, returns ai_status='unavailable' without leaking secrets."""
        token = self._issue_token("user-err")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        def failing_provider(request):
            raise TimeoutError("Connection to provider timed out.")

        mock_provider = MockAIProvider(response_generator=failing_provider)

        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            res = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["ai_status"], "unavailable")
            self.assertIn("deterministic_result", data)
            # Internal python tracebacks are not exposed
            self.assertNotIn("Traceback", str(data))

    def test_grounding_failure_handling(self):
        """Ungrounded claims or hallucinated evidence references trigger grounding_failed."""
        token = self._issue_token("user-hallucinate")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        def ungrounded_provider(request):
            return AIResponse(
                status=AIResponseStatus.COMPLETE,
                summary="Candidate has 10+ years of Kubernetes experience.",
                strengths=[
                    AIInsight(
                        text="Candidate has 10+ years of Kubernetes experience.",
                        evidence_reference_ids=["RESUME-SKILL-999"],  # non-existent evidence
                    )
                ],
            )

        mock_provider = MockAIProvider(response_generator=ungrounded_provider)

        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            res = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["ai_status"], "grounding_failed")
            self.assertEqual(data["error_code"], "grounding_failed")

    def test_resume_deletion_cascades_and_removes_guidance(self):
        """Deleting the resume removes the analysis record and any persisted AI guidance."""
        token = self._issue_token("user-delete")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        mock_provider = MockAIProvider()

        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )

        # Confirm analysis exists
        with self.Session() as session:
            analysis = session.scalar(select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id))
            self.assertIsNotNone(analysis)
            assert analysis is not None
            self.assertIn("ai_guidance", analysis.analysis_data)

        # Delete resume
        del_res = self.client.delete(
            f"/api/v1/resumes/{resume_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(del_res.status_code, 200)

        # Analysis is removed
        with self.Session() as session:
            analysis = session.scalar(select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id))
            self.assertIsNone(analysis)

        # Subsequent GET /ai returns 404
        get_res = self.client.get(
            f"/api/v1/resumes/{resume_id}/ai",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(get_res.status_code, 404)

    def test_ai_guidance_persistence_failure_triggers_rollback_and_sanitized_500(self):
        """Database commit failure triggers rollback and sanitized HTTP 500 error."""
        token = self._issue_token("user-db-err")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        mock_provider = MockAIProvider()

        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider), \
             patch("sqlalchemy.orm.Session.commit", side_effect=SQLAlchemyError("Simulated disk error")):
            res = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res.status_code, 500)
            data = res.json()
            self.assertIn("Database persistence failed for AI guidance", data["detail"])
            self.assertNotIn("Simulated disk error", str(data))

    def test_failed_regeneration_preserves_previously_valid_guidance(self):
        """Failed or timed out guidance regeneration preserves previously valid guidance."""
        token = self._issue_token("user-regen-guidance")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        mock_provider = MockAIProvider()

        # Step 1: Successful initial guidance generation
        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            res = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            initial_summary = data["ai"]["summary"]

        # Clear cooldown
        ai_request_guard._last_requests.clear()

        # Step 2: Failed second generation (timeout)
        def timeout_provider(request):
            raise TimeoutError("Provider timed out")

        failing_provider = MockAIProvider(response_generator=timeout_provider)
        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", failing_provider):
            res2 = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res2.status_code, 200)
            self.assertEqual(res2.json()["ai_status"], "unavailable")

        # Step 3: Verify original guidance in database is intact
        with self.Session() as session:
            analysis = session.scalar(select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id))
            self.assertIsNotNone(analysis)
            assert analysis is not None
            self.assertEqual(analysis.analysis_data["ai_guidance"]["summary"], initial_summary)

    def test_failed_regeneration_preserves_previously_valid_improvements(self):
        """Failed or ungrounded improvement regeneration preserves previously valid improvements."""
        token = self._issue_token("user-regen-improvements")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        from ai.provider import MockAIProvider as DefaultMockAIProvider
        mock_provider = DefaultMockAIProvider()

        # Step 1: Successful initial improvements generation
        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            res = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai/improvements",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            initial_count = len(data["ai"]["improvements"])

        # Clear cooldown
        ai_request_guard._last_requests.clear()

        # Step 2: Failed second generation (timeout)
        def timeout_provider(request):
            raise TimeoutError("Provider timed out")

        failing_provider = MockAIProvider(response_generator=timeout_provider)
        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", failing_provider):
            res2 = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai/improvements",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res2.status_code, 200)
            self.assertEqual(res2.json()["ai_status"], "unavailable")

        # Step 3: Verify improvements in database still intact
        with self.Session() as session:
            analysis = session.scalar(select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id))
            self.assertIsNotNone(analysis)
            assert analysis is not None
            self.assertEqual(len(analysis.analysis_data["ai_improvements"]["improvements"]), initial_count)

    def test_bad_improvement_priority_mutation_rejected_or_grounding_failed(self):
        """A mutated or partially grounded improvement item is rejected as grounding_failed."""
        token = self._issue_token("user-mutated-imp")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        def mutated_provider(request):
            return AIResponse(
                status=AIResponseStatus.COMPLETE,
                summary="Improvements summary.",
                improvements=[
                    ImprovementItem(
                        improvement_id="IMPROVEMENT-FAKE-999",
                        category=ImprovementCategory.SKILL_EVIDENCE,
                        priority=ImprovementPriority.HIGH,
                        title="Fake Recommendation",
                        action_type=ImprovementActionType.CLARIFY,
                        problem="Fake problem statement that was never analyzed.",
                        recommendation="Fake recommendation that was never grounded.",
                        evidence_reference_ids=["RESUME-SKILL-001"],
                        fact_status=ImprovementFactStatus.VERIFIED_FACT,
                    )
                ],
            )

        mock_provider = MockAIProvider(response_generator=mutated_provider)

        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            res = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai/improvements",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["ai_status"], "grounding_failed")
            self.assertEqual(data["error_code"], "grounding_failed")

    def test_target_job_description_improvements_evaluated_and_persisted(self):
        """Target job description improvements follow intended JDXR flow and persist task metadata."""
        token = self._issue_token("user-target-imp")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        target_jd = """
        Job Title: Cloud Architect
        Required Skills: Python, FastAPI, Docker, Kubernetes, AWS
        Experience: 5+ years building distributed cloud backends
        """

        from ai.provider import MockAIProvider as DefaultMockAIProvider
        mock_provider = DefaultMockAIProvider()

        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            res = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai/improvements",
                headers={"Authorization": f"Bearer {token}"},
                json={"target_job_description": target_jd},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["ai_status"], "complete")

            # Verify persisted metadata
            with self.Session() as session:
                analysis = session.scalar(select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id))
                self.assertIsNotNone(analysis)
                assert analysis is not None
                self.assertIn("ai_improvements", analysis.analysis_data)
                meta = analysis.analysis_data.get("ai_metadata")
                self.assertIsNotNone(meta)
                assert meta is not None
                self.assertEqual(meta["task"], AITaskType.JDXR_RESUME_IMPROVEMENT.value)
                self.assertTrue(meta["has_target_jd"])

    def test_ai_request_guard_cooldown_expiry_allows_subsequent_request(self):
        """Cooldown expiry permits a subsequent valid AI request."""
        token = self._issue_token("user-cooldown-expiry")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        mock_provider = MockAIProvider()

        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            # First request succeeds
            res1 = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res1.status_code, 200)

            # Immediate second request blocked by cooldown
            res2 = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res2.status_code, 429)

            # Manually reset cooldown window simulating expiry
            ai_request_guard._last_requests.clear()

            # Subsequent request succeeds
            res3 = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res3.status_code, 200)
            self.assertEqual(res3.json()["ai_status"], "complete")

    def test_get_resume_ai_retrieves_both_guidance_and_improvements(self):
        """GET /api/v1/resumes/{resume_id}/ai returns both persisted guidance and improvements."""
        token = self._issue_token("user-both-results")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        from ai.provider import MockAIProvider as DefaultMockAIProvider
        mock_provider = DefaultMockAIProvider()

        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            # 1. Generate guidance
            res1 = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res1.status_code, 200)

            # Clear cooldown
            ai_request_guard._last_requests.clear()

            # 2. Generate improvements
            res2 = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai/improvements",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res2.status_code, 200)

            # 3. Retrieve both via GET
            res_get = self.client.get(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res_get.status_code, 200)
            get_data = res_get.json()
            self.assertTrue(get_data["success"])
            self.assertIsNotNone(get_data["ai_guidance"])
            self.assertIsNotNone(get_data["ai_improvements"])
            self.assertIsNotNone(get_data["ai_metadata"])

    def test_fresh_db_session_json_persistence_verification(self):
        """Guidance persists correctly after loading the record in a fresh database session."""
        token = self._issue_token("user-fresh-session")
        upload_data = self._upload_resume(token)
        resume_id = upload_data["file_id"]

        mock_provider = MockAIProvider()

        with patch.object(ai_enrichment_service.orchestrator, "enabled", True), \
             patch.object(ai_enrichment_service.orchestrator, "provider", mock_provider):
            res = self.client.post(
                f"/api/v1/resumes/{resume_id}/ai",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res.status_code, 200)

        # Open completely fresh, independent session from engine
        fresh_session = self.Session()
        try:
            analysis = fresh_session.scalar(select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id))
            self.assertIsNotNone(analysis)
            assert analysis is not None
            self.assertIsInstance(analysis.analysis_data, dict)
            self.assertIn("ai_guidance", analysis.analysis_data)
            self.assertIn("summary", analysis.analysis_data["ai_guidance"])
            self.assertIn("ai_metadata", analysis.analysis_data)
            self.assertEqual(analysis.analysis_data["ai_metadata"]["task"], "resume_career_guidance")
        finally:
            fresh_session.close()


if __name__ == "__main__":
    unittest.main()
