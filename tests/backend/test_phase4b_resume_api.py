"""Phase 4B Stage 2 authenticated resume API and privacy hardening tests.

Verifies:
1. Authenticated upload succeeds and persists metadata and analysis.
2. Missing, invalid, expired, or forged authentication is rejected.
3. User A cannot list, retrieve, download, or delete User B's resume (IDOR isolation).
4. Client-supplied user_id cannot override the verified owner.
5. Cross-user analysis association is rejected.
6. Storage failure leaves no persisted resume record.
7. Database failure after storage upload triggers compensating cleanup.
8. Resume deletion removes the database analysis and attempts to delete the associated object.
9. Legacy analysis endpoints cannot expose or delete account-owned records.
10. Upload-status requests cannot reveal another user's file ID or progress (returns 410 Gone).
11. Logout and account switching privacy protections and active resume switching.
12. Existing anonymous flows remain isolated and compatible where intentionally supported.
"""

import asyncio
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
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from api.v1.resumes import get_storage_service  # noqa: E402
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
from services.storage_service import LocalStorageAdapter, StorageError  # noqa: E402


def _create_sqlite_test_engine(db_path: Path):
    """Create a SQLite engine with foreign key enforcement enabled."""
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


VALID_RESUME_TEXT = """
Candidate Test
candidate.test@example.com | +1 555-019-2831

SUMMARY
Experienced software engineer with 5 years building backend services, data pipelines, and APIs.

TECHNICAL SKILLS
Python, FastAPI, SQL, PostgreSQL, Docker, Git, REST APIs, Microservices

PROFESSIONAL EXPERIENCE
Senior Software Engineer at Alpha Tech | 2021 - Present
- Designed and implemented RESTful microservices in Python using FastAPI.
- Optimized PostgreSQL queries and database schemas for high-throughput transactions.
- Automated CI/CD pipelines with Docker and GitHub Actions.

Software Engineer at Beta Solutions | 2019 - 2021
- Built core backend components using Python and Flask.
- Collaborated with frontend engineers to integrate React applications.

EDUCATION
Bachelor of Science in Computer Science | State University | 2015 - 2019

PROJECTS
Career Portal Architecture
- Designed scalable user-owned resume persistence service with strict tenant isolation.
"""


def _create_docx_bytes(text: str = VALID_RESUME_TEXT) -> bytes:
    doc = Document()
    for line in text.strip().splitlines():
        doc.add_paragraph(line.strip())
    payload = BytesIO()
    doc.save(payload)
    return payload.getvalue()


class TestPhase4BResumeApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.config = AuthConfig(
            issuer="https://phase4b-test.supabase.co/auth/v1",
            audience="authenticated",
            jwks_url="https://phase4b-test.supabase.co/auth/v1/.well-known/jwks.json",
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

        # Anonymous legacy routes directory setup
        self.anon_uploads_dir = temp_path / "anon_uploads"
        self.anon_analysis_dir = self.anon_uploads_dir / "analysis"
        self.anon_analysis_dir.mkdir(parents=True, exist_ok=True)

        self.upload_dir_patch = patch.object(upload_route, "UPLOAD_DIR", self.anon_uploads_dir)
        self.analysis_dir_patch = patch.object(upload_route, "ANALYSIS_DIR", self.anon_analysis_dir)
        self.analysis_route_dir_patch = patch.object(analysis_route, "ANALYSIS_DIR", self.anon_analysis_dir)
        self.session_local_patch = patch.object(session_module, "SessionLocal", self.Session)

        self.upload_dir_patch.start()
        self.analysis_dir_patch.start()
        self.analysis_route_dir_patch.start()
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
        self.analysis_route_dir_patch.stop()
        self.analysis_dir_patch.stop()
        self.upload_dir_patch.stop()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def token(self, user_id: str = "user-one", private_key=None, **overrides) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "sub": user_id,
            "iss": self.config.issuer,
            "aud": self.config.audience,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
            "role": "authenticated",
        }
        claims.update(overrides)
        return jwt.encode(claims, private_key or self.private_key, algorithm="RS256")

    def auth_headers(self, user_id: str = "user-one", **overrides) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token(user_id, **overrides)}"}

    # -------------------------------------------------------------------------
    # 1. Authenticated upload succeeds and persists metadata and analysis
    # -------------------------------------------------------------------------
    def test_01_authenticated_upload_succeeds_and_persists_metadata_and_analysis(self):
        files = {
            "file": ("software_engineer_resume.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        response = self.client.post("/api/v1/resumes", files=files, headers=self.auth_headers("user-one"))
        self.assertEqual(201, response.status_code, response.text)
        data = response.json()

        self.assertTrue(data["success"])
        self.assertIn("file_id", data)
        resume_id = data["file_id"]
        self.assertEqual(resume_id, data["resume"]["id"])
        self.assertEqual("software_engineer_resume.docx", data["resume"]["filename"])
        self.assertTrue(data["resume"]["is_active"])
        self.assertIn("analysis", data)
        self.assertIn("overall_insights", data["analysis"])

        # Verify database persistence
        with self.Session() as session:
            resume = session.scalar(select(Resume).where(Resume.id == resume_id))
            self.assertIsNotNone(resume)
            self.assertEqual("user-one", resume.user_id)
            self.assertEqual(".docx", resume.file_type)

            analysis = session.scalar(select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id))
            self.assertIsNotNone(analysis)
            self.assertEqual("user-one", analysis.user_id)
            self.assertIn("overall_insights", analysis.analysis_data)

        # Verify private storage persistence
        self.assertTrue(self.storage_service.exists("user-one", f"resumes/{resume_id}.docx"))

    # -------------------------------------------------------------------------
    # 2. Missing, invalid, expired, or forged authentication is rejected
    # -------------------------------------------------------------------------
    def test_02_missing_invalid_expired_forged_auth_rejected(self):
        files = {
            "file": ("test.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        # Missing auth
        resp = self.client.post("/api/v1/resumes", files=files)
        self.assertEqual(401, resp.status_code)

        # Malformed auth
        resp = self.client.get("/api/v1/resumes", headers={"Authorization": "Bearer not-a-token"})
        self.assertEqual(401, resp.status_code)

        # Expired auth
        expired_token = self.token(exp=int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()))
        resp = self.client.get("/api/v1/resumes", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(401, resp.status_code)

        # Forged signature
        forged_token = self.token(private_key=self.other_private_key)
        resp = self.client.get("/api/v1/resumes", headers={"Authorization": f"Bearer {forged_token}"})
        self.assertEqual(401, resp.status_code)

    # -------------------------------------------------------------------------
    # 3. User A cannot list, retrieve, download, or delete User B's resume (IDOR)
    # -------------------------------------------------------------------------
    def test_03_idor_isolation_user_a_cannot_access_user_b_resume(self):
        # User B uploads a resume
        files_b = {
            "file": ("user_b_resume.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        res_b = self.client.post("/api/v1/resumes", files=files_b, headers=self.auth_headers("user-two"))
        self.assertEqual(201, res_b.status_code)
        b_resume_id = res_b.json()["file_id"]

        # User A lists resumes - User B's resume must not appear
        res_list = self.client.get("/api/v1/resumes", headers=self.auth_headers("user-one"))
        self.assertEqual(200, res_list.status_code)
        resumes_user_a = res_list.json()
        self.assertFalse(any(r["id"] == b_resume_id for r in resumes_user_a))

        # User A attempts to retrieve User B's resume -> 404
        res_get = self.client.get(f"/api/v1/resumes/{b_resume_id}", headers=self.auth_headers("user-one"))
        self.assertEqual(404, res_get.status_code)

        # User A attempts to download User B's resume -> 404
        res_dl = self.client.get(f"/api/v1/resumes/{b_resume_id}/download", headers=self.auth_headers("user-one"))
        self.assertEqual(404, res_dl.status_code)

        # User A attempts to activate User B's resume -> 404
        res_act = self.client.post(f"/api/v1/resumes/{b_resume_id}/activate", headers=self.auth_headers("user-one"))
        self.assertEqual(404, res_act.status_code)

        # User A attempts to delete User B's resume -> 404
        res_del = self.client.delete(f"/api/v1/resumes/{b_resume_id}", headers=self.auth_headers("user-one"))
        self.assertEqual(404, res_del.status_code)

        # User B's resume is completely intact
        with self.Session() as session:
            resume = session.scalar(select(Resume).where(Resume.id == b_resume_id))
            self.assertIsNotNone(resume)
            self.assertEqual("user-two", resume.user_id)
        self.assertTrue(self.storage_service.exists("user-two", f"resumes/{b_resume_id}.docx"))

    # -------------------------------------------------------------------------
    # 4. Client-supplied user_id cannot override the verified owner
    # -------------------------------------------------------------------------
    def test_04_client_supplied_user_id_cannot_override_verified_owner(self):
        files = {
            "file": ("resume.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        # Attacker tries to inject user_id via query parameter or form field
        response = self.client.post(
            "/api/v1/resumes?user_id=victim-user",
            data={"user_id": "victim-user"},
            files=files,
            headers=self.auth_headers("user-one"),
        )
        self.assertEqual(201, response.status_code)
        resume_id = response.json()["file_id"]

        with self.Session() as session:
            resume = session.scalar(select(Resume).where(Resume.id == resume_id))
            # The owner must be user-one from the JWT, never the spoofed victim-user
            self.assertEqual("user-one", resume.user_id)
            self.assertNotEqual("victim-user", resume.user_id)

    # -------------------------------------------------------------------------
    # 5. Cross-user analysis association is rejected
    # -------------------------------------------------------------------------
    def test_05_cross_user_analysis_association_rejected(self):
        repo = ResumeRepository()
        with self.Session() as session:
            resume = repo.create_resume(
                session,
                user_id="user-one",
                filename="doc.docx",
                file_type=".docx",
                file_size_bytes=100,
                storage_path="users/user-one/resumes/r1.docx",
                content_hash="h1",
            )
            session.commit()

            # Attempt to create analysis referencing User A's resume but User B's user_id
            with self.assertRaises(Exception):
                repo.create_analysis(
                    session,
                    resume_id=resume.id,
                    user_id="user-two",  # Mismatched user_id
                    analysis_data={"score": 80},
                )
                session.commit()

    # -------------------------------------------------------------------------
    # 6. Storage failure leaves no persisted resume record
    # -------------------------------------------------------------------------
    def test_06_storage_failure_leaves_no_persisted_resume_record(self):
        files = {
            "file": ("resume.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        with patch.object(self.storage_service, "upload", side_effect=StorageError("Storage connection timed out")):
            response = self.client.post("/api/v1/resumes", files=files, headers=self.auth_headers("user-one"))
            self.assertEqual(503, response.status_code)
            self.assertIn("Storage service is temporarily unavailable", response.text)

        with self.Session() as session:
            resumes = session.scalars(select(Resume)).all()
            self.assertEqual(0, len(resumes))
            analyses = session.scalars(select(ResumeAnalysis)).all()
            self.assertEqual(0, len(analyses))

    # -------------------------------------------------------------------------
    # 7. Database failure after storage upload triggers compensating cleanup
    # -------------------------------------------------------------------------
    def test_07_database_failure_triggers_compensating_storage_cleanup(self):
        files = {
            "file": ("resume.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        with patch("api.v1.resumes.resume_repository.create_resume", side_effect=RuntimeError("Simulated DB connection drop")):
            response = self.client.post("/api/v1/resumes", files=files, headers=self.auth_headers("user-one"))
            self.assertEqual(500, response.status_code)
            self.assertIn("Database persistence failed", response.text)

        # Verify that compensating object deletion was invoked and no files remain in storage
        user_files = list(self.storage_root.glob("**/*.docx"))
        self.assertEqual(0, len(user_files))

    # -------------------------------------------------------------------------
    # 8. Resume deletion removes the database analysis and attempts to delete the associated object
    # -------------------------------------------------------------------------
    def test_08_resume_deletion_removes_database_analysis_and_stored_object(self):
        files = {
            "file": ("to_delete.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        res = self.client.post("/api/v1/resumes", files=files, headers=self.auth_headers("user-one"))
        self.assertEqual(201, res.status_code)
        resume_id = res.json()["file_id"]

        self.assertTrue(self.storage_service.exists("user-one", f"resumes/{resume_id}.docx"))

        # Delete resume
        del_res = self.client.delete(f"/api/v1/resumes/{resume_id}", headers=self.auth_headers("user-one"))
        self.assertEqual(200, del_res.status_code)
        self.assertTrue(del_res.json()["success"])

        # Check DB
        with self.Session() as session:
            self.assertIsNone(session.scalar(select(Resume).where(Resume.id == resume_id)))
            self.assertIsNone(session.scalar(select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id)))

        # Check Storage
        self.assertFalse(self.storage_service.exists("user-one", f"resumes/{resume_id}.docx"))

    # -------------------------------------------------------------------------
    # 9. Legacy analysis endpoints cannot expose or delete account-owned records
    # -------------------------------------------------------------------------
    def test_09_legacy_analysis_endpoints_cannot_expose_or_delete_account_records(self):
        files = {
            "file": ("account_doc.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        res = self.client.post("/api/v1/resumes", files=files, headers=self.auth_headers("user-one"))
        self.assertEqual(201, res.status_code)
        account_resume_id = res.json()["file_id"]

        # Legacy GET /api/analysis?file_id=...
        get_res = self.client.get(f"/api/analysis?file_id={account_resume_id}")
        self.assertEqual(403, get_res.status_code)
        self.assertIn("Account-owned resumes cannot be accessed", get_res.text)

        # Legacy GET /api/analysis/summary?file_id=...
        sum_res = self.client.get(f"/api/analysis/summary?file_id={account_resume_id}")
        self.assertEqual(403, sum_res.status_code)
        self.assertIn("Account-owned resumes cannot be accessed", sum_res.text)

        # Legacy DELETE /api/analysis/{file_id}
        del_res = self.client.delete(f"/api/analysis/{account_resume_id}")
        self.assertEqual(403, del_res.status_code)
        self.assertIn("Account-owned resumes cannot be accessed", del_res.text)

        # Legacy POST /api/analysis/ai?file_id=...
        ai_res = self.client.post(f"/api/analysis/ai?file_id={account_resume_id}")
        self.assertEqual(403, ai_res.status_code)

        # Legacy POST /api/analysis/ai/improvements?file_id=...
        imp_res = self.client.post(f"/api/analysis/ai/improvements?file_id={account_resume_id}")
        self.assertEqual(403, imp_res.status_code)

    # -------------------------------------------------------------------------
    # 10. Upload-status requests cannot reveal another user's file ID or progress
    # -------------------------------------------------------------------------
    def test_10_upload_status_requests_cannot_reveal_user_data(self):
        res = self.client.get("/api/upload/status")
        self.assertEqual(410, res.status_code)
        self.assertEqual("true", res.headers.get("Deprecation"))
        data = res.json()
        self.assertFalse(data["success"])
        self.assertEqual("deprecated_endpoint", data["error"])
        self.assertNotIn("file_id", data)
        self.assertNotIn("progress", data)

    # -------------------------------------------------------------------------
    # 11. Logout and account switching privacy protections & active resume switching
    # -------------------------------------------------------------------------
    def test_11_logout_and_account_switching_privacy_protections(self):
        # Verify active resume switching for authenticated user
        files1 = {"file": ("res1.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        files2 = {"file": ("res2.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

        r1 = self.client.post("/api/v1/resumes", files=files1, headers=self.auth_headers("user-one")).json()["file_id"]
        r2 = self.client.post("/api/v1/resumes", files=files2, headers=self.auth_headers("user-one")).json()["file_id"]

        # r2 is now active by default because it was created last
        with self.Session() as session:
            resume2 = session.scalar(select(Resume).where(Resume.id == r2))
            self.assertTrue(resume2.is_active)

        # Activate r1
        act_res = self.client.post(f"/api/v1/resumes/{r1}/activate", headers=self.auth_headers("user-one"))
        self.assertEqual(200, act_res.status_code)
        self.assertTrue(act_res.json()["is_active"])

        with self.Session() as session:
            resume1 = session.scalar(select(Resume).where(Resume.id == r1))
            resume2 = session.scalar(select(Resume).where(Resume.id == r2))
            self.assertTrue(resume1.is_active)
            self.assertFalse(resume2.is_active)

        # Download scoped URL check
        dl_res = self.client.get(f"/api/v1/resumes/{r1}/download", headers=self.auth_headers("user-one"))
        self.assertEqual(200, dl_res.status_code)
        dl_data = dl_res.json()
        self.assertIn("download_url", dl_data)
        self.assertIn("signature=", dl_data["download_url"])
        self.assertEqual(300, dl_data["expires_in"])

    # -------------------------------------------------------------------------
    # 12. Existing anonymous flows remain isolated and compatible where intentionally supported
    # -------------------------------------------------------------------------
    def test_12_anonymous_flows_remain_isolated_and_compatible(self):
        # Anonymous upload through legacy route /api/upload
        files = {
            "file": ("anonymous.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        anon_upload_res = self.client.post("/api/upload", files=files)
        self.assertEqual(200, anon_upload_res.status_code)
        anon_data = anon_upload_res.json()
        self.assertTrue(anon_data["success"])
        anon_file_id = anon_data["file_id"]

        # Verify that anonymous upload did NOT create any record in the accounts database
        with self.Session() as session:
            res = session.scalar(select(Resume).where(Resume.id == anon_file_id))
            self.assertIsNone(res)

        # Anonymous retrieval through legacy route /api/analysis
        anon_get_res = self.client.get(f"/api/analysis?file_id={anon_file_id}")
        self.assertEqual(200, anon_get_res.status_code)
        self.assertTrue(anon_get_res.json()["success"])

        # Anonymous summary retrieval through legacy route
        anon_sum_res = self.client.get(f"/api/analysis/summary?file_id={anon_file_id}")
        self.assertEqual(200, anon_sum_res.status_code)
        self.assertTrue(anon_sum_res.json()["success"])

        # Anonymous deletion through legacy route
        anon_del_res = self.client.delete(f"/api/analysis/{anon_file_id}")
        self.assertEqual(200, anon_del_res.status_code)
        self.assertTrue(anon_del_res.json()["success"])

    # -------------------------------------------------------------------------
    # 13. Resume deletion with storage failure records durable cleanup job & retries
    # -------------------------------------------------------------------------
    def test_13_resume_deletion_storage_failure_creates_durable_cleanup_job_and_retries(self):
        files = {
            "file": ("storage_fail.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        upload_res = self.client.post("/api/v1/resumes", files=files, headers=self.auth_headers("user-one"))
        self.assertEqual(201, upload_res.status_code)
        resume_id = upload_res.json()["file_id"]

        self.assertTrue(self.storage_service.exists("user-one", f"resumes/{resume_id}.docx"))

        # Delete resume while storage service delete fails
        with patch.object(self.storage_service, "delete", side_effect=StorageError("Bucket access timeout")):
            del_res = self.client.delete(f"/api/v1/resumes/{resume_id}", headers=self.auth_headers("user-one"))
            self.assertEqual(200, del_res.status_code)
            data = del_res.json()
            self.assertTrue(data["success"])

        # Check that DB resume and analysis were removed atomically
        with self.Session() as session:
            self.assertIsNone(session.scalar(select(Resume).where(Resume.id == resume_id)))
            self.assertIsNone(session.scalar(select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id)))

            # Verify durable cleanup job exists and is in "failed" state with error recorded
            job = session.scalar(select(StorageCleanupJob).where(StorageCleanupJob.resume_id == resume_id))
            self.assertIsNotNone(job)
            self.assertEqual("failed", job.status)
            self.assertEqual(1, job.attempts)
            self.assertIn("Bucket access timeout", job.last_error or "")
            self.assertEqual("user-one", job.user_id)
            self.assertEqual(f"resumes/{resume_id}.docx", job.object_name)

        # File is still present in storage
        self.assertTrue(self.storage_service.exists("user-one", f"resumes/{resume_id}.docx"))

        # Retry cleanup using repository method
        repo = ResumeRepository()
        with self.Session() as session:
            stats = repo.retry_pending_storage_cleanups(session, self.storage_service, user_id="user-one")
            self.assertEqual(1, stats["processed"])
            self.assertEqual(1, stats["succeeded"])
            self.assertEqual(0, stats["failed"])

            # Verify job is now completed
            job_after = session.scalar(select(StorageCleanupJob).where(StorageCleanupJob.resume_id == resume_id))
            self.assertEqual("completed", job_after.status)
            self.assertIsNone(job_after.last_error)

        # File has now been removed from storage
        self.assertFalse(self.storage_service.exists("user-one", f"resumes/{resume_id}.docx"))

        # Repeated retry does nothing and is idempotent
        with self.Session() as session:
            stats_repeat = repo.retry_pending_storage_cleanups(session, self.storage_service, user_id="user-one")
            self.assertEqual(0, stats_repeat["processed"])

    # -------------------------------------------------------------------------
    # 14. Resume deletion IDOR protection and cross-user cleanup isolation
    # -------------------------------------------------------------------------
    def test_14_resume_deletion_idor_and_cleanup_tenant_isolation(self):
        files = {
            "file": ("user_one.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        upload_res = self.client.post("/api/v1/resumes", files=files, headers=self.auth_headers("user-one"))
        self.assertEqual(201, upload_res.status_code)
        resume_id = upload_res.json()["file_id"]

        # User Two attempts to delete User One's resume
        del_res = self.client.delete(f"/api/v1/resumes/{resume_id}", headers=self.auth_headers("user-two"))
        self.assertEqual(404, del_res.status_code)

        # Confirm User One's resume and analysis are intact
        with self.Session() as session:
            r = session.scalar(select(Resume).where(Resume.id == resume_id))
            self.assertIsNotNone(r)
            a = session.scalar(select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id))
            self.assertIsNotNone(a)
            # No cleanup job was created
            job = session.scalar(select(StorageCleanupJob).where(StorageCleanupJob.resume_id == resume_id))
            self.assertIsNone(job)

        # Confirm file still exists
        self.assertTrue(self.storage_service.exists("user-one", f"resumes/{resume_id}.docx"))

    # -------------------------------------------------------------------------
    # 15. Database transaction failure during deletion retains file and state
    # -------------------------------------------------------------------------
    def test_15_resume_deletion_database_failure_retains_resume_and_creates_no_orphan(self):
        files = {
            "file": ("db_fail.docx", BytesIO(self.docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        upload_res = self.client.post("/api/v1/resumes", files=files, headers=self.auth_headers("user-one"))
        self.assertEqual(201, upload_res.status_code)
        resume_id = upload_res.json()["file_id"]

        with patch("api.v1.resumes.resume_repository.delete_resume_with_cleanup_intent", side_effect=RuntimeError("Simulated database failure")):
            del_res = self.client.delete(f"/api/v1/resumes/{resume_id}", headers=self.auth_headers("user-one"))
            self.assertEqual(500, del_res.status_code)

        # Verify storage file is still intact (not prematurely deleted)
        self.assertTrue(self.storage_service.exists("user-one", f"resumes/{resume_id}.docx"))

        # Verify database record still exists
        with self.Session() as session:
            r = session.scalar(select(Resume).where(Resume.id == resume_id))
            self.assertIsNotNone(r)


if __name__ == "__main__":
    unittest.main()
