"""Tests for the operational storage cleanup worker and error sanitization."""

import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from db.base import Base  # noqa: E402
from db.models import StorageCleanupJob  # noqa: E402
from db.repositories import ResumeRepository, _sanitize_cleanup_error  # noqa: E402
from workers.storage_cleanup_worker import (  # noqa: E402
    main,
    run_storage_cleanup_worker,
    validate_user_id,
)


class MockStorageService:
    def __init__(self, should_fail: bool = False, fail_message: str = "Storage connection failed") -> None:
        self.should_fail = should_fail
        self.fail_message = fail_message
        self.deleted: list[tuple[str, str]] = []

    def delete(self, owner_id: str, object_name: str) -> None:
        if self.should_fail:
            raise RuntimeError(self.fail_message)
        self.deleted.append((owner_id, object_name))


class TestStorageCleanupWorker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "worker_test.db"
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.repo = ResumeRepository()

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_sanitize_cleanup_error(self):
        """Verify tokens, query parameters, credentials, and signatures are sanitized."""
        self.assertIsNone(_sanitize_cleanup_error(None))
        self.assertEqual(_sanitize_cleanup_error(""), "Storage operation failed")

        msg_with_token = "Failed fetching https://supabase.co/storage/v1/obj?token=secret123456789"
        sanitized = _sanitize_cleanup_error(msg_with_token)
        self.assertNotIn("secret123456789", sanitized)
        self.assertIn("token=[REDACTED]", sanitized)

        msg_with_bearer = "Authorization failed for Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID"
        sanitized_bearer = _sanitize_cleanup_error(msg_with_bearer)
        self.assertNotIn("eyJhbGciOi", sanitized_bearer)
        self.assertIn("Bearer [REDACTED_JWT]", sanitized_bearer)

        msg_with_db = "Connection error to postgresql://user:mysecretpassword@localhost:5432/career_advisor"
        sanitized_db = _sanitize_cleanup_error(msg_with_db)
        self.assertNotIn("mysecretpassword", sanitized_db)
        self.assertIn("[REDACTED_DATABASE_URL]", sanitized_db)

    def test_validate_user_id(self):
        valid_uuid = str(uuid.uuid4())
        self.assertEqual(validate_user_id(valid_uuid), valid_uuid)
        self.assertIsNone(validate_user_id(None))
        self.assertIsNone(validate_user_id("   "))

        with self.assertRaises(ValueError):
            validate_user_id("not-a-valid-uuid")

        with self.assertRaises(ValueError):
            validate_user_id("../../../path/traversal")

    def test_worker_dry_run(self):
        """Dry-run should report pending jobs without invoking storage delete."""
        user_id = str(uuid.uuid4())
        with self.Session() as session:
            self.repo.create_storage_cleanup_job(
                session,
                user_id=user_id,
                resume_id=str(uuid.uuid4()),
                storage_path=f"users/{user_id}/resumes/r1.pdf",
                object_name="r1.pdf",
            )
            session.commit()

        mock_storage = MockStorageService()
        with self.Session() as session:
            result = run_storage_cleanup_worker(
                dry_run=True,
                session=session,
                storage_service=mock_storage,
                repository=self.repo,
            )

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["queued_for_processing"], 1)
        self.assertEqual(result["processed"], 0)
        self.assertEqual(result["counts"]["pending"], 1)
        self.assertEqual(len(mock_storage.deleted), 0)

    def test_worker_successful_cleanup_and_idempotency(self):
        """Worker processes jobs to completion and handles repeated executions cleanly."""
        user_id = str(uuid.uuid4())
        resume_id = str(uuid.uuid4())
        with self.Session() as session:
            job = self.repo.create_storage_cleanup_job(
                session,
                user_id=user_id,
                resume_id=resume_id,
                storage_path=f"users/{user_id}/resumes/{resume_id}.pdf",
                object_name=f"{resume_id}.pdf",
            )
            session.commit()
            job_id = job.id

        mock_storage = MockStorageService()
        with self.Session() as session:
            result = run_storage_cleanup_worker(
                session=session,
                storage_service=mock_storage,
                repository=self.repo,
            )

        self.assertFalse(result["dry_run"])
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["succeeded"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(mock_storage.deleted, [(user_id, f"{resume_id}.pdf")])

        with self.Session() as session:
            job = self.repo.get_cleanup_job(session, job_id=job_id)
            self.assertEqual(job.status, "completed")
            self.assertIsNone(job.last_error)

        # Re-running worker idempotently: 0 pending jobs, 0 processed
        with self.Session() as session:
            second_result = run_storage_cleanup_worker(
                session=session,
                storage_service=mock_storage,
                repository=self.repo,
            )
        self.assertEqual(second_result["processed"], 0)
        self.assertEqual(second_result["counts"]["completed"], 1)

    def test_worker_storage_failure_and_subsequent_retry(self):
        """Worker handles storage failure, increments attempts, sanitizes error, and recovers upon retry."""
        user_id = str(uuid.uuid4())
        resume_id = str(uuid.uuid4())
        with self.Session() as session:
            job = self.repo.create_storage_cleanup_job(
                session,
                user_id=user_id,
                resume_id=resume_id,
                storage_path=f"users/{user_id}/resumes/{resume_id}.pdf",
                object_name=f"{resume_id}.pdf",
            )
            session.commit()
            job_id = job.id

        # 1. Run with failing storage
        mock_storage = MockStorageService(
            should_fail=True,
            fail_message="Connection error with token=mysecrettoken123",
        )
        with self.Session() as session:
            fail_result = run_storage_cleanup_worker(
                session=session,
                storage_service=mock_storage,
                repository=self.repo,
            )

        self.assertEqual(fail_result["processed"], 1)
        self.assertEqual(fail_result["succeeded"], 0)
        self.assertEqual(fail_result["failed"], 1)

        with self.Session() as session:
            job = self.repo.get_cleanup_job(session, job_id=job_id)
            self.assertEqual(job.status, "failed")
            self.assertEqual(job.attempts, 1)
            self.assertNotIn("mysecrettoken123", job.last_error)
            self.assertIn("token=[REDACTED]", job.last_error)

        # 2. Run again after storage is restored
        mock_storage.should_fail = False
        with self.Session() as session:
            recovery_result = run_storage_cleanup_worker(
                session=session,
                storage_service=mock_storage,
                repository=self.repo,
            )

        self.assertEqual(recovery_result["processed"], 1)
        self.assertEqual(recovery_result["succeeded"], 1)
        self.assertEqual(recovery_result["failed"], 0)

        with self.Session() as session:
            job = self.repo.get_cleanup_job(session, job_id=job_id)
            self.assertEqual(job.status, "completed")
            self.assertIsNone(job.last_error)

    def test_worker_user_id_tenant_isolation(self):
        """Worker with --user-id only processes the targeted user's jobs."""
        user_alice = str(uuid.uuid4())
        user_bob = str(uuid.uuid4())

        with self.Session() as session:
            job_alice = self.repo.create_storage_cleanup_job(
                session,
                user_id=user_alice,
                resume_id=str(uuid.uuid4()),
                storage_path=f"users/{user_alice}/resumes/alice.pdf",
                object_name="alice.pdf",
            )
            job_bob = self.repo.create_storage_cleanup_job(
                session,
                user_id=user_bob,
                resume_id=str(uuid.uuid4()),
                storage_path=f"users/{user_bob}/resumes/bob.pdf",
                object_name="bob.pdf",
            )
            session.commit()
            alice_id = job_alice.id
            bob_id = job_bob.id

        mock_storage = MockStorageService()

        # Run worker restricted to Alice
        with self.Session() as session:
            result = run_storage_cleanup_worker(
                user_id=user_alice,
                session=session,
                storage_service=mock_storage,
                repository=self.repo,
            )

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["succeeded"], 1)
        self.assertEqual(mock_storage.deleted, [(user_alice, "alice.pdf")])

        with self.Session() as session:
            check_alice = self.repo.get_cleanup_job(session, job_id=alice_id)
            check_bob = self.repo.get_cleanup_job(session, job_id=bob_id)
            self.assertEqual(check_alice.status, "completed")
            self.assertEqual(check_bob.status, "pending")  # Bob's job remained untouched

    def test_cli_main_exit_codes(self):
        """Test CLI main() with dry-run, json output, and error conditions."""
        with patch("workers.storage_cleanup_worker.SessionLocal", return_value=self.Session()):
            # 1. Dry run succeeds with exit code 0
            code = main(["--dry-run", "--json"])
            self.assertEqual(code, 0)

            # 2. Invalid user-id returns exit code 1
            code_invalid = main(["--user-id", "invalid-uuid-format"])
            self.assertEqual(code_invalid, 1)


if __name__ == "__main__":
    unittest.main()
