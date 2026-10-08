"""Authenticated current-user profile endpoint."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from auth.dependencies import require_authenticated_user
from auth.models import AuthenticatedUser
from db.repositories import ProfileRepository
from db.session import get_db
from services.ownership_service import OwnershipError, ensure_user_scope


router = APIRouter()
profile_repository = ProfileRepository()


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    display_name: str | None
    created_at: datetime
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=200)


def _profile_service_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Profile service is temporarily unavailable.",
    )


@router.get("", response_model=ProfileResponse)
def get_profile(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    try:
        profile = profile_repository.get_or_create(db, current_user.user_id)
        ensure_user_scope(current_user, profile.user_id)
        db.commit()
        db.refresh(profile)
        return ProfileResponse.model_validate(profile)
    except OwnershipError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile access is not permitted.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise _profile_service_error(exc) from exc


@router.patch("", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    try:
        profile = profile_repository.update_display_name(db, current_user.user_id, payload.display_name)
        ensure_user_scope(current_user, profile.user_id)
        db.commit()
        db.refresh(profile)
        return ProfileResponse.model_validate(profile)
    except OwnershipError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile access is not permitted.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise _profile_service_error(exc) from exc
