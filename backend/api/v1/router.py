"""Phase 4A versioned API router."""

from fastapi import APIRouter

from .profile import router as profile_router


router = APIRouter()
router.include_router(profile_router, prefix="/profile", tags=["Profile"])
