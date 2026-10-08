"""Phase 4A database models."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
