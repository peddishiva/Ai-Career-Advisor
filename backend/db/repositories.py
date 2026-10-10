from datetime import datetime, timezone
import re
from typing import Any
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .models import Profile, Resume, ResumeAnalysis, StorageCleanupJob


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sanitize_cleanup_error(error: str | None) -> str | None:
    if error is None:
        return None
    msg = str(error).strip()
    if not msg:
        return "Storage operation failed"
    # Redact URL query parameters (e.g. ?signature=... or ?token=...)
    msg = re.sub(r"\?[^ \t\n\r\"'>]+", "?token=[REDACTED]", msg)
    # Redact key/token/secret/password/signature assignments
    msg = re.sub(r"(?i)(token|key|secret|password|sig|signature)\s*[:=]\s*[^\s\"',;&]+", r"\1=[REDACTED]", msg)
    # Redact JWTs
    msg = re.sub(r"ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9_-]{10,})?", "[REDACTED_JWT]", msg)
    # Redact database connection strings
    msg = re.sub(r"(?:postgresql|postgres|mysql|sqlite)://[^ \t\n\r\"'>]+", "[REDACTED_DATABASE_URL]", msg)
    # Redact Bearer tokens
    msg = re.sub(r"(?i)Bearer\s+[A-Za-z0-9_.-]+", "Bearer [REDACTED_JWT]", msg)
    return msg[:500]


class ProfileRepository:
    def get(self, session: Session, user_id: str) -> Profile | None:
        return session.scalar(select(Profile).where(Profile.user_id == user_id))

    def get_or_create(self, session: Session, user_id: str) -> Profile:
        profile = self.get(session, user_id)
        if profile is None:
            profile = Profile(user_id=user_id)
            session.add(profile)
            session.flush()
        return profile

    def update_display_name(self, session: Session, user_id: str, display_name: str | None) -> Profile:
        profile = self.get_or_create(session, user_id)
        profile.display_name = display_name
        profile.updated_at = datetime.now(timezone.utc)
        session.flush()
        return profile


class ResumeRepository:
    """Repository operations for user-owned resumes and associated analysis results."""

    def create_resume(
        self,
        session: Session,
        *,
        user_id: str,
        filename: str,
        file_type: str,
        file_size_bytes: int,
        storage_path: str,
        content_hash: str,
        resume_id: str | None = None,
        is_active: bool = True,
    ) -> Resume:
        if is_active:
            # Mark existing active resumes for this user as inactive
            session.execute(
                update(Resume)
                .where(Resume.user_id == user_id, Resume.is_active.is_(True))
                .values(is_active=False, updated_at=_utc_now())
            )

        resume = Resume(
            id=resume_id or str(uuid.uuid4()),
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            storage_path=storage_path,
            content_hash=content_hash,
            is_active=is_active,
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        session.add(resume)
        session.flush()
        return resume

    def create_analysis(
        self,
        session: Session,
        *,
        resume_id: str,
        user_id: str,
        analysis_data: dict,
        fit_score: int | None = None,
        target_role: str | None = None,
        analysis_id: str | None = None,
    ) -> ResumeAnalysis:
        # Enforce that the parent resume exists and belongs to the verified user
        resume = self.get_by_id(session, resume_id=resume_id, user_id=user_id)
        if resume is None:
            raise ValueError(f"Resume {resume_id} not found for user {user_id}")

        if fit_score is None and isinstance(analysis_data, dict):
            fit_score = analysis_data.get("overall_insights", {}).get("fit_score")
        if target_role is None and isinstance(analysis_data, dict):
            role_matches = analysis_data.get("role_matches", [])
            if role_matches and isinstance(role_matches, list) and isinstance(role_matches[0], dict):
                target_role = role_matches[0].get("title")

        analysis = ResumeAnalysis(
            id=analysis_id or str(uuid.uuid4()),
            resume_id=resume.id,
            user_id=resume.user_id,  # enforce ownership consistency
            analysis_data=analysis_data,
            fit_score=fit_score,
            target_role=target_role,
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        session.add(analysis)
        session.flush()
        return analysis

    def get_by_id(self, session: Session, *, resume_id: str, user_id: str) -> Resume | None:
        return session.scalar(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        )

    def get_active(self, session: Session, *, user_id: str) -> Resume | None:
        return session.scalar(
            select(Resume)
            .where(Resume.user_id == user_id, Resume.is_active.is_(True))
            .order_by(Resume.created_at.desc())
        )

    def set_active_resume(
        self,
        session: Session,
        *,
        resume_id: str,
        user_id: str,
    ) -> Resume | None:
        """Safely switch the active resume for a user within a consistent session."""
        resume = self.get_by_id(session, resume_id=resume_id, user_id=user_id)
        if resume is None:
            return None
        if resume.is_active:
            return resume

        # Deactivate any currently active resume for this user first so uq_resumes_user_active is not violated
        session.execute(
            update(Resume)
            .where(Resume.user_id == user_id, Resume.is_active.is_(True))
            .values(is_active=False, updated_at=_utc_now())
        )
        resume.is_active = True
        resume.updated_at = _utc_now()
        session.flush()
        return resume

    def list_by_user(self, session: Session, *, user_id: str) -> list[Resume]:
        return list(
            session.scalars(
                select(Resume)
                .where(Resume.user_id == user_id)
                .order_by(Resume.created_at.desc())
            ).all()
        )

    def get_analysis_by_resume_id(self, session: Session, *, resume_id: str, user_id: str) -> ResumeAnalysis | None:
        return session.scalar(
            select(ResumeAnalysis).where(
                ResumeAnalysis.resume_id == resume_id,
                ResumeAnalysis.user_id == user_id,
            )
        )

    def delete_resume(self, session: Session, *, resume_id: str, user_id: str) -> bool:
        resume = self.get_by_id(session, resume_id=resume_id, user_id=user_id)
        if resume is None:
            return False
        session.delete(resume)
        session.flush()
        return True

    def create_storage_cleanup_job(
        self,
        session: Session,
        *,
        user_id: str,
        resume_id: str,
        storage_path: str,
        object_name: str,
    ) -> StorageCleanupJob:
        job = StorageCleanupJob(
            id=str(uuid.uuid4()),
            user_id=user_id,
            resume_id=resume_id,
            storage_path=storage_path,
            object_name=object_name,
            status="pending",
            attempts=0,
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        session.add(job)
        session.flush()
        return job

    def get_cleanup_job(self, session: Session, *, job_id: str, user_id: str | None = None) -> StorageCleanupJob | None:
        stmt = select(StorageCleanupJob).where(StorageCleanupJob.id == job_id)
        if user_id is not None:
            stmt = stmt.where(StorageCleanupJob.user_id == user_id)
        return session.scalar(stmt)

    def get_cleanup_job_by_resume_id(self, session: Session, *, resume_id: str, user_id: str | None = None) -> StorageCleanupJob | None:
        stmt = select(StorageCleanupJob).where(StorageCleanupJob.resume_id == resume_id)
        if user_id is not None:
            stmt = stmt.where(StorageCleanupJob.user_id == user_id)
        return session.scalar(stmt)

    def mark_cleanup_completed(self, session: Session, *, job_id: str) -> bool:
        job = session.get(StorageCleanupJob, job_id)
        if job is None:
            return False
        job.status = "completed"
        job.last_error = None
        job.updated_at = _utc_now()
        session.flush()
        return True

    def record_cleanup_failure(self, session: Session, *, job_id: str, error_message: str | None) -> bool:
        job = session.get(StorageCleanupJob, job_id)
        if job is None:
            return False
        job.status = "failed"
        job.attempts += 1
        job.last_error = _sanitize_cleanup_error(error_message)
        job.updated_at = _utc_now()
        session.flush()
        return True

    def get_pending_storage_cleanups(self, session: Session, *, user_id: str | None = None, limit: int = 50) -> list[StorageCleanupJob]:
        stmt = (
            select(StorageCleanupJob)
            .where(StorageCleanupJob.status.in_(["pending", "failed", "in_progress"]))
            .order_by(StorageCleanupJob.created_at.asc())
            .limit(limit)
        )
        if user_id is not None:
            stmt = stmt.where(StorageCleanupJob.user_id == user_id)
        return list(session.scalars(stmt).all())

    def get_cleanup_job_counts(self, session: Session, *, user_id: str | None = None) -> dict[str, int]:
        """Return counts of storage cleanup jobs grouped by status."""
        stmt = select(StorageCleanupJob.status, func.count(StorageCleanupJob.id))
        if user_id is not None:
            stmt = stmt.where(StorageCleanupJob.user_id == user_id)
        stmt = stmt.group_by(StorageCleanupJob.status)
        raw = dict(session.execute(stmt).all())
        return {
            "pending": raw.get("pending", 0),
            "in_progress": raw.get("in_progress", 0),
            "failed": raw.get("failed", 0),
            "completed": raw.get("completed", 0),
            "total": sum(raw.values()),
        }

    def delete_resume_with_cleanup_intent(
        self,
        session: Session,
        *,
        resume_id: str,
        user_id: str,
        object_name: str,
    ) -> StorageCleanupJob | None:
        """Atomically stage cleanup intent and remove resume from database."""
        resume = self.get_by_id(session, resume_id=resume_id, user_id=user_id)
        if resume is None:
            return None

        # 1. Create durable cleanup job in the same transaction
        job = self.create_storage_cleanup_job(
            session,
            user_id=user_id,
            resume_id=resume.id,
            storage_path=resume.storage_path,
            object_name=object_name,
        )

        # 2. Delete resume (cascades to ResumeAnalysis)
        session.delete(resume)
        session.flush()
        return job

    def retry_pending_storage_cleanups(
        self,
        session: Session,
        storage_service: Any,
        *,
        user_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, int]:
        """Idempotently process pending/failed storage cleanup jobs."""
        from typing import Any  # safe local typing
        jobs = self.get_pending_storage_cleanups(session, user_id=user_id, limit=limit)
        success_count = 0
        failure_count = 0

        for job in jobs:
            if job.status == "completed":
                continue
            try:
                job.status = "in_progress"
                job.updated_at = _utc_now()
                session.flush()

                storage_service.delete(job.user_id, job.object_name)
                job.status = "completed"
                job.last_error = None
                job.updated_at = _utc_now()
                success_count += 1
            except Exception as exc:
                job.status = "failed"
                job.attempts += 1
                job.last_error = _sanitize_cleanup_error(str(exc))
                job.updated_at = _utc_now()
                failure_count += 1
            session.flush()

        session.commit()
        return {"processed": len(jobs), "succeeded": success_count, "failed": failure_count}
