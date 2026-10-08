"""Small repository boundary for Phase 4A profile persistence."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Profile


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
