"""Authenticated resume document and analysis persistence API."""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import tempfile
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from auth.dependencies import require_authenticated_user
from auth.models import AuthenticatedUser
from config.security_config import MAX_FILENAME_LENGTH
from config.upload_config import MAX_RESUME_FILE_SIZE_BYTES, UPLOAD_COPY_CHUNK_BYTES
from db.repositories import ResumeRepository
from db.session import get_db
from services.analysis_service import AnalysisService
from services.file_upload_service import (
    InvalidUploadContentError,
    UploadTooLargeError,
    copy_upload_with_limit,
    sanitize_upload_filename,
    uploaded_file_size,
    validate_document_content,
)
from services.ownership_service import OwnershipError, ensure_user_scope
from services.parser_service import ResumeParser
from services.resume_validator import ResumeValidator
from services.storage_service import (
    StorageError,
    StorageService,
    build_storage_service,
)


router = APIRouter()
resume_repository = ResumeRepository()
parser = ResumeParser()
analyzer = AnalysisService()
resume_validator = ResumeValidator()


def get_storage_service() -> StorageService:
    """Dependency provider for the configured private storage service."""
    return build_storage_service()


def public_analysis_payload(analysis: dict) -> dict:
    """Return analysis data without backend-only resume evidence."""
    public_analysis = dict(analysis)
    public_analysis.pop("parsed_resume", None)
    return public_analysis


class ResumeSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    file_size_bytes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResumeDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    file_size_bytes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    analysis: dict | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
):
    """Authenticated multipart resume upload and deterministic analysis persistence."""
    display_filename = sanitize_upload_filename(file.filename or "", MAX_FILENAME_LENGTH)
    if not display_filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

    file_ext = Path(display_filename).suffix.lower()
    if file_ext not in [".pdf", ".docx", ".doc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF and DOCX files are supported.",
        )

    temp_dir = tempfile.mkdtemp()
    temp_file_path = Path(temp_dir) / f"{uuid.uuid4()}{file_ext}"

    try:
        upload_size = uploaded_file_size(file)
        if upload_size is not None and upload_size > MAX_RESUME_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Resume file is too large. Maximum file size is 5MB.",
            )

        with temp_file_path.open("wb") as buffer:
            try:
                copy_upload_with_limit(file, buffer, MAX_RESUME_FILE_SIZE_BYTES, UPLOAD_COPY_CHUNK_BYTES)
            except UploadTooLargeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Resume file is too large. Maximum file size is 5MB.",
                ) from exc

        validate_document_content(temp_file_path, file_ext)

        content_bytes = temp_file_path.read_bytes()
        content_hash = hashlib.sha256(content_bytes).hexdigest()

        extracted_text = parser.extract_text(str(temp_file_path))
        validation = resume_validator.validate_text(extracted_text)
        if not validation.get("valid"):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "success": False,
                    "error": "resume_validation_failed",
                    "validation": validation,
                    "message": validation.get("message", "Please upload a valid resume."),
                },
            )

        parsed_data = parser.parse_text(extracted_text)
        analysis = analyzer.generate_analysis(parsed_data)

        resume_id = str(uuid.uuid4())
        analysis["metadata"] = {
            "file_id": resume_id,
            "filename": display_filename,
            "upload_time": datetime.now(timezone.utc).isoformat(),
            "file_type": file_ext,
        }

        parsed_resume_for_matching = dict(parsed_data)
        for private_key in ("raw_text", "name", "email", "phone"):
            parsed_resume_for_matching.pop(private_key, None)
        stored_analysis = dict(analysis)
        stored_analysis["parsed_resume"] = parsed_resume_for_matching

        object_name = f"resumes/{resume_id}{file_ext}"

        # 1. Upload to private object storage
        try:
            storage_meta = storage_service.upload(
                owner_id=current_user.user_id,
                object_name=object_name,
                content=content_bytes,
                content_type=file.content_type or "application/octet-stream",
            )
        except StorageError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service is temporarily unavailable.",
            ) from exc

        # 2. Persist to database with compensating storage cleanup on failure
        try:
            resume = resume_repository.create_resume(
                db,
                user_id=current_user.user_id,
                filename=display_filename,
                file_type=file_ext,
                file_size_bytes=len(content_bytes),
                storage_path=storage_meta.storage_path,
                content_hash=content_hash,
                resume_id=resume_id,
                is_active=True,
            )
            resume_analysis = resume_repository.create_analysis(
                db,
                resume_id=resume.id,
                user_id=current_user.user_id,
                analysis_data=stored_analysis,
                analysis_id=str(uuid.uuid4()),
            )
            db.commit()
            db.refresh(resume)
            db.refresh(resume_analysis)
        except Exception as db_exc:
            db.rollback()
            try:
                storage_service.delete(current_user.user_id, object_name)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database persistence failed. Uploaded object has been cleaned up.",
            ) from db_exc

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "message": "Resume uploaded and analyzed successfully",
                "file_id": resume.id,
                "resume": {
                    "id": resume.id,
                    "filename": resume.filename,
                    "file_type": resume.file_type,
                    "file_size_bytes": resume.file_size_bytes,
                    "is_active": resume.is_active,
                    "created_at": resume.created_at.isoformat(),
                    "updated_at": resume.updated_at.isoformat(),
                },
                "analysis": public_analysis_payload(stored_analysis),
            },
        )
    except InvalidUploadContentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded resume contents do not match the selected document type.",
        ) from exc
    finally:
        if temp_file_path.exists():
            temp_file_path.unlink()
        try:
            Path(temp_dir).rmdir()
        except Exception:
            pass
        await file.close()


@router.get("", response_model=list[ResumeSummaryResponse])
def list_resumes(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> list[ResumeSummaryResponse]:
    """List all resumes belonging to the authenticated user."""
    resumes = resume_repository.list_by_user(db, user_id=current_user.user_id)
    return [ResumeSummaryResponse.model_validate(r) for r in resumes]


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
def get_resume(
    resume_id: str,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> ResumeDetailResponse:
    """Retrieve resume metadata and persisted analysis for the verified owner."""
    resume = resume_repository.get_by_id(db, resume_id=resume_id, user_id=current_user.user_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

    ensure_user_scope(current_user, resume.user_id)
    analysis = resume_repository.get_analysis_by_resume_id(db, resume_id=resume.id, user_id=current_user.user_id)

    return ResumeDetailResponse(
        id=resume.id,
        filename=resume.filename,
        file_type=resume.file_type,
        file_size_bytes=resume.file_size_bytes,
        is_active=resume.is_active,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
        analysis=public_analysis_payload(analysis.analysis_data) if analysis else None,
    )


@router.get("/{resume_id}/download")
def download_resume(
    resume_id: str,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
):
    """Retrieve a scoped, short-lived download URL for the verified owner's resume document."""
    resume = resume_repository.get_by_id(db, resume_id=resume_id, user_id=current_user.user_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

    ensure_user_scope(current_user, resume.user_id)

    prefix = f"users/{current_user.user_id}/"
    if resume.storage_path.startswith(prefix):
        object_name = resume.storage_path[len(prefix):]
    else:
        object_name = f"resumes/{resume.id}{resume.file_type}"

    try:
        signed_url = storage_service.download_signed(current_user.user_id, object_name, expires_in=300)
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume document not found in storage.",
        ) from exc

    return {
        "download_url": signed_url,
        "filename": resume.filename,
        "expires_in": 300,
    }


@router.delete("/{resume_id}")
def delete_resume(
    resume_id: str,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
):
    """Delete the verified owner's resume, cascading analysis record, and stored object."""
    resume = resume_repository.get_by_id(db, resume_id=resume_id, user_id=current_user.user_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

    ensure_user_scope(current_user, resume.user_id)

    prefix = f"users/{current_user.user_id}/"
    if resume.storage_path.startswith(prefix):
        object_name = resume.storage_path[len(prefix):]
    else:
        object_name = f"resumes/{resume.id}{resume.file_type}"

    # 1. Atomically record durable cleanup intent and delete resume in database transaction
    try:
        cleanup_job = resume_repository.delete_resume_with_cleanup_intent(
            db,
            resume_id=resume_id,
            user_id=current_user.user_id,
            object_name=object_name,
        )
        if cleanup_job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database deletion failed: {exc}",
        ) from exc

    # 2. Attempt storage deletion outside the database transaction
    try:
        storage_service.delete(current_user.user_id, object_name)
        resume_repository.mark_cleanup_completed(db, job_id=cleanup_job.id)
        db.commit()
    except Exception as exc:
        # Storage deletion failed: record error details so it can be retried without being lost
        try:
            resume_repository.record_cleanup_failure(db, job_id=cleanup_job.id, error_message=str(exc))
            db.commit()
        except Exception:
            pass

    return {
        "success": True,
        "message": f"Resume {resume_id} deleted successfully.",
    }


@router.post("/{resume_id}/activate", response_model=ResumeSummaryResponse)
def activate_resume(
    resume_id: str,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> ResumeSummaryResponse:
    """Safely switch the active resume for the authenticated user."""
    resume = resume_repository.set_active_resume(db, resume_id=resume_id, user_id=current_user.user_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

    db.commit()
    db.refresh(resume)
    return ResumeSummaryResponse.model_validate(resume)
