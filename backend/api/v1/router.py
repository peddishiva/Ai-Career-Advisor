from fastapi import APIRouter

from .profile import router as profile_router
from .resumes import router as resumes_router


router = APIRouter()
router.include_router(profile_router, prefix="/profile", tags=["Profile"])
router.include_router(resumes_router, prefix="/resumes", tags=["Resumes"])
