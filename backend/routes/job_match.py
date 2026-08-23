"""Compatibility route for the legacy deterministic resume-to-job API.

The frontend JDxR workflow uses the isolated session API in ``routes.jdxr``.
This route remains available for existing API consumers.
"""

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from config.job_description_config import MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES
from services.file_upload_service import UploadTooLargeError, copy_upload_with_limit, uploaded_file_size
from services.job_match_api_service import JobMatchAPIError, JobMatchAPIService


router = APIRouter()

SUPPORTED_JD_FILE_TYPES = {".pdf", ".docx", ".doc"}
UPLOAD_COPY_CHUNK_BYTES = 1024 * 1024
job_match_api_service = JobMatchAPIService()


@router.post("/job-match")
async def match_resume_to_job(
    request: Request,
    resume_id: Optional[str] = Form(None),
    job_description: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """
    Match an existing analyzed resume against pasted JD text or one uploaded JD document.
    """
    temp_path: Optional[Path] = None

    try:
        if _is_json_request(request):
            payload = await request.json()
            resume_id = resume_id or payload.get("resume_id")
            job_description = job_description or payload.get("job_description")

        if file and file.filename:
            suffix = Path(file.filename).suffix.lower()
            if suffix not in SUPPORTED_JD_FILE_TYPES:
                raise JobMatchAPIError(
                    400,
                    "unsupported_job_description_document",
                    "Unsupported JD document type. Please upload a PDF, DOCX, or DOC file.",
                )
            temp_path = _save_temp_upload(file, suffix)

        response = job_match_api_service.match_resume_to_job(
            resume_id=resume_id,
            job_description_text=job_description,
            job_description_file_path=temp_path,
        )
        return JSONResponse(status_code=200, content=response)

    except JobMatchAPIError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.payload)
    except Exception:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "job_match_failed",
                "message": "Unable to analyze this job match. Please try again.",
            },
        )
    finally:
        if file:
            await file.close()
        if temp_path and temp_path.exists():
            temp_path.unlink()


def _is_json_request(request: Request) -> bool:
    return "application/json" in request.headers.get("content-type", "").lower()


def _save_temp_upload(file: UploadFile, suffix: str) -> Path:
    upload_size = _uploaded_file_size(file)
    if upload_size is not None and upload_size > MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES:
        raise _job_description_file_too_large_error()

    temp_path: Optional[Path] = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                copy_upload_with_limit(
                    file,
                    temp_file,
                    MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES,
                    UPLOAD_COPY_CHUNK_BYTES,
                )
            except UploadTooLargeError as exc:
                raise _job_description_file_too_large_error() from exc

        return temp_path
    except Exception:
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise


def _uploaded_file_size(file: UploadFile) -> Optional[int]:
    return uploaded_file_size(file)


def _job_description_file_too_large_error() -> JobMatchAPIError:
    max_mb = MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES // (1024 * 1024)
    return JobMatchAPIError(
        413,
        "job_description_file_too_large",
        f"JD document is too large. Maximum file size is {max_mb}MB.",
    )
