"""Phase 4B database models, repository, composite constraints, and Alembic migration tests."""

from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from db.base import Base  # noqa: E402
from db.models import Resume, ResumeAnalysis, StorageCleanupJob  # noqa: E402
from db.repositories import ResumeRepository  # noqa: E402


def _create_sqlite_test_engine(db_path: Path):
    """Create a SQLite engine with foreign key enforcement enabled."""
    engine = create_engine(f"sqlite:///{db_path}")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


class TestPhase4BDatabase(unittest.TestCase):
    def test_migration_upgrade_and_downgrade(self):
        """Test Alembic upgrade to head (0005), downgrade to 0004, 0003, base, and re-upgrade."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "migration_test.db"
            url = f"sqlite:///{db_path}"
            config = Config(str(Path(__file__).resolve().parent.parent.parent / "alembic.ini"))
            previous_url = os.environ.get("DATABASE_URL")
            os.environ["DATABASE_URL"] = url
            engine = None
            try:
                # Upgrade to head (includes 0001, 0002, 0003, 0004, 0005)
                command.upgrade(config, "head")
                engine = _create_sqlite_test_engine(db_path)
                inspector = inspect(engine)
                table_names = inspector.get_table_names()
                self.assertIn("profiles", table_names)
                self.assertIn("resumes", table_names)
                self.assertIn("resume_analyses", table_names)
                self.assertIn("storage_cleanup_jobs", table_names)

                # Verify composite foreign key constraint exists from resume_analyses to resumes (id, user_id)
                fks = inspector.get_foreign_keys("resume_analyses")
                composite_fk = next((fk for fk in fks if fk["referred_table"] == "resumes"), None)
                self.assertIsNotNone(composite_fk)
                self.assertEqual(["resume_id", "user_id"], composite_fk["constrained_columns"])
                self.assertEqual(["id", "user_id"], composite_fk["referred_columns"])
                self.assertEqual("CASCADE", composite_fk.get("options", {}).get("ondelete"))

                # Verify unique constraint on resumes (id, user_id)
                unique_constraints = inspector.get_unique_constraints("resumes")
                has_composite_unique = any(
                    set(uc["column_names"]) == {"id", "user_id"} for uc in unique_constraints
                )
                self.assertTrue(has_composite_unique, f"Unique constraints found: {unique_constraints}")

                # Verify unique partial index uq_resumes_user_active exists
                indexes = inspector.get_indexes("resumes")
                active_idx = next((idx for idx in indexes if idx["name"] == "uq_resumes_user_active"), None)
                self.assertIsNotNone(active_idx)
                self.assertTrue(active_idx["unique"])

                # Verify storage_cleanup_jobs columns and indexes
                cleanup_indexes = inspector.get_indexes("storage_cleanup_jobs")
                cleanup_idx_names = {idx["name"] for idx in cleanup_indexes}
                self.assertIn("ix_storage_cleanup_jobs_status", cleanup_idx_names)
                self.assertIn("ix_storage_cleanup_jobs_user_id", cleanup_idx_names)
                self.assertIn("ix_storage_cleanup_jobs_resume_id", cleanup_idx_names)

                # Downgrade 0005 to 0004
                command.downgrade(config, "0004_create_resumes_and_analyses")
                inspector = inspect(engine)
                table_names = inspector.get_table_names()
                self.assertIn("profiles", table_names)
                self.assertIn("resumes", table_names)
                self.assertIn("resume_analyses", table_names)
                self.assertNotIn("storage_cleanup_jobs", table_names)

                # Downgrade 0004 to 0003
                command.downgrade(config, "0003_auth_grants")
                inspector = inspect(engine)
                table_names = inspector.get_table_names()
                self.assertIn("profiles", table_names)
                self.assertNotIn("resumes", table_names)
                self.assertNotIn("resume_analyses", table_names)
                self.assertNotIn("storage_cleanup_jobs", table_names)

                # Downgrade all the way to base
                command.downgrade(config, "base")
                inspector = inspect(engine)
                table_names = inspector.get_table_names()
                self.assertNotIn("profiles", table_names)
                self.assertNotIn("resumes", table_names)
                self.assertNotIn("resume_analyses", table_names)
                self.assertNotIn("storage_cleanup_jobs", table_names)

                # Re-upgrade to head
                command.upgrade(config, "head")
                inspector = inspect(engine)
                table_names = inspector.get_table_names()
                self.assertIn("profiles", table_names)
                self.assertIn("resumes", table_names)
                self.assertIn("resume_analyses", table_names)
                self.assertIn("storage_cleanup_jobs", table_names)
            finally:
                if engine is not None:
                    engine.dispose()
                if previous_url is None:
                    os.environ.pop("DATABASE_URL", None)
                else:
                    os.environ["DATABASE_URL"] = previous_url

    def test_models_creation_and_attributes(self):
        """Verify model instantiation, defaults upon flush, and timestamps."""
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = _create_sqlite_test_engine(Path(temp_dir) / "model_test.db")
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine, expire_on_commit=False)

            with Session() as session:
                resume = Resume(
                    user_id="user-123",
                    filename="my_resume.pdf",
                    file_type=".pdf",
                    file_size_bytes=1024,
                    storage_path="users/user-123/resumes/my_resume.pdf",
                    content_hash="abc123hash",
                )
                session.add(resume)
                session.flush()

                self.assertIsNotNone(resume.id)
                self.assertTrue(resume.is_active)
                self.assertIsInstance(resume.created_at, datetime)
                self.assertEqual(timezone.utc, resume.created_at.tzinfo)

                analysis = ResumeAnalysis(
                    resume_id=resume.id,
                    user_id="user-123",
                    analysis_data={"overall_insights": {"fit_score": 85}},
                    fit_score=85,
                    target_role="Software Engineer",
                )
                session.add(analysis)
                session.flush()

                self.assertIsNotNone(analysis.id)
                self.assertIsInstance(analysis.created_at, datetime)
                self.assertEqual(timezone.utc, analysis.created_at.tzinfo)

            engine.dispose()

    def test_cross_user_analysis_rejection_at_database_level(self):
        """Regression test: database must reject an analysis referencing another user's resume,

        even if the child row supplies the attacker's own user_id.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = _create_sqlite_test_engine(Path(temp_dir) / "ownership_test.db")
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine, expire_on_commit=False)

            with Session() as session:
                # Alice creates a legitimate resume
                alice_resume = Resume(
                    id="alice-resume-1",
                    user_id="user-alice",
                    filename="alice.pdf",
                    file_type=".pdf",
                    file_size_bytes=1000,
                    storage_path="users/alice/alice.pdf",
                    content_hash="alicehash",
                    is_active=True,
                )
                session.add(alice_resume)
                session.commit()

                # Legitimate analysis owned by Alice succeeds
                alice_analysis = ResumeAnalysis(
                    id="alice-analysis-1",
                    resume_id="alice-resume-1",
                    user_id="user-alice",
                    analysis_data={"score": 90},
                )
                session.add(alice_analysis)
                session.commit()

                # Attacker Bob attempts to create an analysis referencing Alice's resume
                # while supplying his own user_id ("user-bob").
                # The composite foreign key (resume_id, user_id) -> resumes (id, user_id)
                # MUST reject this at the database level.
                bob_rogue_analysis = ResumeAnalysis(
                    id="bob-rogue-1",
                    resume_id="alice-resume-1",
                    user_id="user-bob",
                    analysis_data={"score": 10},
                )
                session.add(bob_rogue_analysis)
                with self.assertRaises(IntegrityError):
                    session.commit()
                session.rollback()

                # Also verify that a non-existent (resume_id, user_id) pair is rejected
                ghost_analysis = ResumeAnalysis(
                    id="ghost-analysis-1",
                    resume_id="non-existent-resume",
                    user_id="user-alice",
                    analysis_data={"score": 50},
                )
                session.add(ghost_analysis)
                with self.assertRaises(IntegrityError):
                    session.commit()
                session.rollback()

            engine.dispose()

    def test_active_resume_exclusivity_and_safe_switching(self):
        """Verify:

        - Multiple inactive resumes allowed for one user.
        - One active resume allowed per user.
        - Rejecting a second active resume for the same user via unique partial index.
        - Allowing different users to each have an active resume concurrently.
        - Switching active resumes safely using repository.set_active_resume.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = _create_sqlite_test_engine(Path(temp_dir) / "active_test.db")
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine, expire_on_commit=False)
            repository = ResumeRepository()

            with Session() as session:
                # 1. Multiple inactive resumes for one user (user-1) are allowed
                inact1 = Resume(
                    id="inact-1",
                    user_id="user-1",
                    filename="old1.pdf",
                    file_type=".pdf",
                    file_size_bytes=100,
                    storage_path="p1",
                    content_hash="h1",
                    is_active=False,
                )
                inact2 = Resume(
                    id="inact-2",
                    user_id="user-1",
                    filename="old2.pdf",
                    file_type=".pdf",
                    file_size_bytes=100,
                    storage_path="p2",
                    content_hash="h2",
                    is_active=False,
                )
                session.add_all([inact1, inact2])
                session.commit()

                # 2. Add one active resume for user-1 (allowed)
                act1 = Resume(
                    id="act-1",
                    user_id="user-1",
                    filename="current.pdf",
                    file_type=".pdf",
                    file_size_bytes=100,
                    storage_path="p3",
                    content_hash="h3",
                    is_active=True,
                )
                session.add(act1)
                session.commit()

                # 3. Rejecting a second active resume for the same user directly at the database level
                act1_duplicate = Resume(
                    id="act-1-dup",
                    user_id="user-1",
                    filename="conflict.pdf",
                    file_type=".pdf",
                    file_size_bytes=100,
                    storage_path="p4",
                    content_hash="h4",
                    is_active=True,
                )
                session.add(act1_duplicate)
                with self.assertRaises(IntegrityError):
                    session.commit()
                session.rollback()

                # 4. Allowing different users to each have an active resume concurrently
                act2 = Resume(
                    id="act-2",
                    user_id="user-2",
                    filename="user2.pdf",
                    file_type=".pdf",
                    file_size_bytes=100,
                    storage_path="p5",
                    content_hash="h5",
                    is_active=True,
                )
                session.add(act2)
                session.commit()

                self.assertTrue(act1.is_active)
                self.assertTrue(act2.is_active)

                # 5. Switching active resume safely using repository.set_active_resume
                switched = repository.set_active_resume(session, resume_id="inact-1", user_id="user-1")
                self.assertIsNotNone(switched)
                self.assertEqual("inact-1", switched.id)
                session.commit()

                # Verify inact-1 is now active, act-1 is inactive, inact-2 remains inactive
                session.refresh(inact1)
                session.refresh(act1)
                session.refresh(inact2)
                self.assertTrue(inact1.is_active)
                self.assertFalse(act1.is_active)
                self.assertFalse(inact2.is_active)

                # Calling set_active_resume on the already-active resume is idempotent
                same = repository.set_active_resume(session, resume_id="inact-1", user_id="user-1")
                self.assertIsNotNone(same)
                self.assertTrue(same.is_active)

                # Attempting to activate a non-existent or other user's resume returns None
                other_user_res = repository.set_active_resume(session, resume_id="act-2", user_id="user-1")
                self.assertIsNone(other_user_res)
                # inact-1 is still the active resume for user-1
                session.refresh(inact1)
                self.assertTrue(inact1.is_active)

            engine.dispose()

    def test_resume_repository_create_and_scoping(self):
        """Test resume creation, active resume query, and owner-scoped retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = _create_sqlite_test_engine(Path(temp_dir) / "repo_test.db")
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine, expire_on_commit=False)
            repository = ResumeRepository()

            with Session() as session:
                r1 = repository.create_resume(
                    session,
                    user_id="user-alpha",
                    filename="resume_v1.pdf",
                    file_type=".pdf",
                    file_size_bytes=2048,
                    storage_path="users/user-alpha/resumes/r1.pdf",
                    content_hash="hash1",
                    is_active=True,
                )
                session.commit()

                # Verify creation
                self.assertEqual("user-alpha", r1.user_id)
                self.assertTrue(r1.is_active)

                # Verify owner-scoped retrieval
                fetched = repository.get_by_id(session, resume_id=r1.id, user_id="user-alpha")
                self.assertIsNotNone(fetched)
                self.assertEqual(r1.id, fetched.id)

                # Verify other user cannot retrieve
                unauthorized = repository.get_by_id(session, resume_id=r1.id, user_id="user-beta")
                self.assertIsNone(unauthorized)

                # Upload second resume for user-alpha with is_active=True
                r2 = repository.create_resume(
                    session,
                    user_id="user-alpha",
                    filename="resume_v2.pdf",
                    file_type=".pdf",
                    file_size_bytes=4096,
                    storage_path="users/user-alpha/resumes/r2.pdf",
                    content_hash="hash2",
                    is_active=True,
                )
                session.commit()

                # r1 should now be inactive, r2 active
                session.refresh(r1)
                self.assertFalse(r1.is_active)
                self.assertTrue(r2.is_active)

                active = repository.get_active(session, user_id="user-alpha")
                self.assertIsNotNone(active)
                self.assertEqual(r2.id, active.id)

                # List by user returns 2 resumes in descending order
                user_resumes = repository.list_by_user(session, user_id="user-alpha")
                self.assertEqual(2, len(user_resumes))
                self.assertEqual(r2.id, user_resumes[0].id)

                # User beta has 0 resumes
                beta_resumes = repository.list_by_user(session, user_id="user-beta")
                self.assertEqual([], beta_resumes)

            engine.dispose()

    def test_resume_analysis_association_and_cascade_delete(self):
        """Test creating analysis, ownership consistency, and cascade deletion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = _create_sqlite_test_engine(Path(temp_dir) / "cascade_test.db")
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine, expire_on_commit=False)
            repository = ResumeRepository()

            with Session() as session:
                resume = repository.create_resume(
                    session,
                    user_id="user-owner",
                    filename="test.docx",
                    file_type=".docx",
                    file_size_bytes=3000,
                    storage_path="users/user-owner/resumes/test.docx",
                    content_hash="hash_docx",
                )
                session.commit()

                # Attempting to create analysis for mismatched user raises ValueError in repo
                with self.assertRaises(ValueError):
                    repository.create_analysis(
                        session,
                        resume_id=resume.id,
                        user_id="user-impostor",
                        analysis_data={"metrics": {}},
                    )

                # Create analysis for correct owner
                analysis = repository.create_analysis(
                    session,
                    resume_id=resume.id,
                    user_id="user-owner",
                    analysis_data={
                        "overall_insights": {"fit_score": 92},
                        "role_matches": [{"title": "Cloud Architect", "match": 92}],
                    },
                )
                session.commit()

                self.assertEqual(92, analysis.fit_score)
                self.assertEqual("Cloud Architect", analysis.target_role)
                self.assertEqual("user-owner", analysis.user_id)

                # Retrieve analysis
                retrieved_analysis = repository.get_analysis_by_resume_id(
                    session, resume_id=resume.id, user_id="user-owner"
                )
                self.assertIsNotNone(retrieved_analysis)
                self.assertEqual(analysis.id, retrieved_analysis.id)

                # Unauthorized user cannot retrieve analysis
                self.assertIsNone(
                    repository.get_analysis_by_resume_id(
                        session, resume_id=resume.id, user_id="user-other"
                    )
                )

                # Delete resume and verify cascade deletion of analysis
                deleted = repository.delete_resume(session, resume_id=resume.id, user_id="user-owner")
                self.assertTrue(deleted)
                session.commit()

                self.assertIsNone(repository.get_by_id(session, resume_id=resume.id, user_id="user-owner"))
                self.assertIsNone(repository.get_analysis_by_resume_id(session, resume_id=resume.id, user_id="user-owner"))

            engine.dispose()

    def test_duplicate_resume_id_rejection(self):
        """Test primary key collision on resume creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = _create_sqlite_test_engine(Path(temp_dir) / "pk_test.db")
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine, expire_on_commit=False)
            fixed_id = str(uuid.uuid4())

            with Session() as session1:
                r1 = Resume(
                    id=fixed_id,
                    user_id="user-1",
                    filename="a.pdf",
                    file_type=".pdf",
                    file_size_bytes=100,
                    storage_path="path/a.pdf",
                    content_hash="h1",
                )
                session1.add(r1)
                session1.commit()

            with Session() as session2:
                r2 = Resume(
                    id=fixed_id,
                    user_id="user-2",
                    filename="b.pdf",
                    file_type=".pdf",
                    file_size_bytes=200,
                    storage_path="path/b.pdf",
                    content_hash="h2",
                )
                session2.add(r2)
                with self.assertRaises(IntegrityError):
                    session2.commit()

            engine.dispose()

    def test_storage_cleanup_queue_repository_operations(self):
        """Test StorageCleanupJob creation, failure recording, completion, and retries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = _create_sqlite_test_engine(Path(temp_dir) / "cleanup_test.db")
            try:
                Base.metadata.create_all(engine)
                Session = sessionmaker(bind=engine, expire_on_commit=False)
                repository = ResumeRepository()

                class MockStorageService:
                    def __init__(self):
                        self.deleted_calls = []
                        self.should_fail = False

                    def delete(self, owner_id: str, object_name: str) -> None:
                        if self.should_fail:
                            raise RuntimeError(f"Storage backend unavailable for {owner_id}/{object_name}")
                        self.deleted_calls.append((owner_id, object_name))

                mock_storage = MockStorageService()

                with Session() as session:
                    # 1. Test direct job creation
                    job = repository.create_storage_cleanup_job(
                        session,
                        user_id="user-1",
                        resume_id="res-1",
                        storage_path="users/user-1/resumes/res-1.pdf",
                        object_name="res-1.pdf",
                    )
                    session.commit()
                    self.assertEqual(job.status, "pending")
                    self.assertEqual(job.attempts, 0)
                    self.assertIsNone(job.last_error)

                    # 2. Record failure
                    success = repository.record_cleanup_failure(
                        session,
                        job_id=job.id,
                        error_message="Network timeout connecting to bucket",
                    )
                    session.commit()
                    self.assertTrue(success)
                    failed_job = repository.get_cleanup_job(session, job_id=job.id)
                    self.assertEqual(failed_job.status, "failed")
                    self.assertEqual(failed_job.attempts, 1)
                    self.assertIn("Network timeout", failed_job.last_error)

                    # 3. Mark completed
                    comp_success = repository.mark_cleanup_completed(session, job_id=job.id)
                    session.commit()
                    self.assertTrue(comp_success)
                    completed_job = repository.get_cleanup_job(session, job_id=job.id)
                    self.assertEqual(completed_job.status, "completed")
                    self.assertIsNone(completed_job.last_error)

                    # 4. Atomic delete_resume_with_cleanup_intent
                    resume = Resume(
                        id="res-atomic-1",
                        user_id="user-1",
                        filename="resume.pdf",
                        file_type=".pdf",
                        file_size_bytes=1024,
                        storage_path="users/user-1/resumes/res-atomic-1.pdf",
                        content_hash="hash-1",
                    )
                    session.add(resume)
                    session.flush()

                    analysis = ResumeAnalysis(
                        resume_id=resume.id,
                        user_id="user-1",
                        analysis_data={"score": 90},
                    )
                    session.add(analysis)
                    session.commit()

                    # Perform atomic delete with cleanup intent
                    cleanup_job = repository.delete_resume_with_cleanup_intent(
                        session,
                        resume_id=resume.id,
                        user_id="user-1",
                        object_name="res-atomic-1.pdf",
                    )
                    session.commit()

                    self.assertIsNotNone(cleanup_job)
                    self.assertEqual(cleanup_job.status, "pending")
                    self.assertEqual(cleanup_job.storage_path, "users/user-1/resumes/res-atomic-1.pdf")
                    # Resume and analysis should be deleted from DB
                    self.assertIsNone(repository.get_by_id(session, resume_id=resume.id, user_id="user-1"))
                    self.assertIsNone(repository.get_analysis_by_resume_id(session, resume_id=resume.id, user_id="user-1"))

                    # 5. Retry pending cleanup with transient failure
                    mock_storage.should_fail = True
                    stats = repository.retry_pending_storage_cleanups(session, mock_storage, user_id="user-1")
                    session.commit()
                    self.assertEqual(stats["processed"], 1)
                    self.assertEqual(stats["failed"], 1)
                    self.assertEqual(stats["succeeded"], 0)

                    retried_job = repository.get_cleanup_job(session, job_id=cleanup_job.id)
                    self.assertEqual(retried_job.status, "failed")
                    self.assertEqual(retried_job.attempts, 1)
                    self.assertIn("Storage backend unavailable", retried_job.last_error)

                    # 6. Retry after transient issue resolved
                    mock_storage.should_fail = False
                    stats_success = repository.retry_pending_storage_cleanups(session, mock_storage, user_id="user-1")
                    session.commit()
                    self.assertEqual(stats_success["processed"], 1)
                    self.assertEqual(stats_success["succeeded"], 1)
                    self.assertEqual(stats_success["failed"], 0)
                    self.assertIn(("user-1", "res-atomic-1.pdf"), mock_storage.deleted_calls)

                    final_job = repository.get_cleanup_job(session, job_id=cleanup_job.id)
                    self.assertEqual(final_job.status, "completed")

                    # 7. User isolation in cleanup retry
                    job_user2 = repository.create_storage_cleanup_job(
                        session,
                        user_id="user-2",
                        resume_id="res-u2",
                        storage_path="users/user-2/resumes/res-u2.pdf",
                        object_name="res-u2.pdf",
                    )
                    session.commit()
                    # Run cleanup scoped to user-1: should NOT touch user-2's job
                    stats_u1 = repository.retry_pending_storage_cleanups(session, mock_storage, user_id="user-1")
                    self.assertEqual(stats_u1["processed"], 0)
                    u2_job_check = repository.get_cleanup_job(session, job_id=job_user2.id)
                    self.assertEqual(u2_job_check.status, "pending")
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
