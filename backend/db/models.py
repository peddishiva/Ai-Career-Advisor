"""Phase 4A and Phase 4B database models."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class Profile(Base):
    __tablename__ = "profiles"

    # Supabase auth.users.id is UUID; keep string values at the Python/API boundary.
    # SQLite remains string-compatible for the repository's local test fixtures.
    user_id: Mapped[str] = mapped_column(
        String(255).with_variant(UUID(as_uuid=False), "postgresql"),
        primary_key=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )


class Resume(Base):
    """User-owned resume document metadata."""

    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(
        String(36).with_variant(UUID(as_uuid=False), "postgresql"),
        primary_key=True,
        default=_generate_uuid,
    )
    user_id: Mapped[str] = mapped_column(
        String(255).with_variant(UUID(as_uuid=False), "postgresql"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_resumes_id_user_id"),
        Index(
            "uq_resumes_user_active",
            "user_id",
            unique=True,
            postgresql_where=text("is_active IS TRUE"),
            sqlite_where=text("is_active = 1"),
        ),
    )

    analysis: Mapped["ResumeAnalysis | None"] = relationship(
        "ResumeAnalysis",
        back_populates="resume",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="[ResumeAnalysis.resume_id, ResumeAnalysis.user_id]",
    )


class ResumeAnalysis(Base):
    """Deterministic career analysis results for an uploaded resume."""

    __tablename__ = "resume_analyses"

    id: Mapped[str] = mapped_column(
        String(36).with_variant(UUID(as_uuid=False), "postgresql"),
        primary_key=True,
        default=_generate_uuid,
    )
    resume_id: Mapped[str] = mapped_column(
        String(36).with_variant(UUID(as_uuid=False), "postgresql"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(255).with_variant(UUID(as_uuid=False), "postgresql"),
        nullable=False,
        index=True,
    )
    fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_role: Mapped[str | None] = mapped_column(String(200), nullable=True)
    analysis_data: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["resume_id", "user_id"],
            ["resumes.id", "resumes.user_id"],
            ondelete="CASCADE",
            name="fk_resume_analyses_resume_user",
        ),
    )

    resume: Mapped["Resume"] = relationship(
        "Resume",
        back_populates="analysis",
        foreign_keys=[resume_id, user_id],
    )


class StorageCleanupJob(Base):
    """Durable cleanup intent for deleted or orphaned storage objects."""

    __tablename__ = "storage_cleanup_jobs"

    id: Mapped[str] = mapped_column(
        String(36).with_variant(UUID(as_uuid=False), "postgresql"),
        primary_key=True,
        default=_generate_uuid,
    )
    user_id: Mapped[str] = mapped_column(
        String(255).with_variant(UUID(as_uuid=False), "postgresql"),
        nullable=False,
        index=True,
    )
    resume_id: Mapped[str] = mapped_column(
        String(36).with_variant(UUID(as_uuid=False), "postgresql"),
        nullable=False,
        index=True,
    )
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    object_name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )
