"""
Service orchestration for Phase 2C resume-to-job matching API.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from config.job_description_config import MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES, NOT_A_JOB_DESCRIPTION, UNCERTAIN
from services.file_upload_service import UploadTooLargeError, ensure_text_size
from services.job_description_parser import JobDescriptionParser
from services.job_description_validator import JobDescriptionValidator
from services.job_match_service import JobMatchService


class JobMatchAPIError(Exception):
    """User-safe API error for deterministic job matching."""

    def __init__(self, status_code: int, error: str, message: str, **extra: Any):
        super().__init__(message)
        self.status_code = status_code
        self.payload = {
            "success": False,
            "error": error,
            "message": message,
            **extra,
        }


class JobMatchAPIService:
    """Retrieve stored resume evidence, validate/parse a JD, and run Phase 2B matching."""

    RESUME_ID_PATTERN = re.compile(r"^[a-fA-F0-9-]{36}$")

    def __init__(
        self,
        analysis_dir: Path | str = Path("uploads/analysis"),
        validator: Optional[JobDescriptionValidator] = None,
        parser: Optional[JobDescriptionParser] = None,
        matcher: Optional[JobMatchService] = None,
    ):
        self.analysis_dir = Path(analysis_dir)
        self.validator = validator or JobDescriptionValidator()
        self.parser = parser or JobDescriptionParser()
        self.matcher = matcher or JobMatchService()

    def match_resume_to_job(
        self,
        resume_id: Optional[str],
        job_description_text: Optional[str] = None,
        job_description_file_path: Optional[Path | str] = None,
    ) -> Dict[str, Any]:
        """Return a stable API response for a stored resume and validated job description."""
        parsed_resume = self._load_parsed_resume(resume_id)
        jd_text = self._job_description_text(job_description_text, job_description_file_path)

        validation = self.validator.validate_text(jd_text)
        if not validation.get("valid"):
            classification = validation.get("classification")
            error = "uncertain_job_description" if classification == UNCERTAIN else "not_a_job_description"
            raise JobMatchAPIError(
                422,
                error,
                validation.get("message", "This file/text does not appear to be a valid job description."),
                validation=validation,
            )

        try:
            parsed_jd = self.parser.parse_text(jd_text)
            match = self.matcher.match(parsed_resume, parsed_jd)
        except JobMatchAPIError:
            raise
        except Exception as exc:
            raise JobMatchAPIError(
                500,
                "matching_failed",
                "Unable to analyze this job match. Please try again.",
            ) from exc

        return {
            "success": True,
            "message": "Job match analysis completed successfully",
            "resume_id": resume_id,
            "validation": validation,
            "job": {
                "job_title": parsed_jd.get("job_title"),
                "company": parsed_jd.get("company"),
                "location": parsed_jd.get("location"),
                "employment_type": parsed_jd.get("employment_type"),
            },
            "match": match,
        }

    def _load_parsed_resume(self, resume_id: Optional[str]) -> Dict[str, Any]:
        if not resume_id:
            raise JobMatchAPIError(
                400,
                "missing_resume",
                "Please analyze a resume before matching it against a job.",
            )
        if not self.RESUME_ID_PATTERN.fullmatch(resume_id):
            raise JobMatchAPIError(
                404,
                "invalid_resume_id",
                "Resume analysis was not found. Please analyze a resume before matching it against a job.",
            )

        analysis_path = self._safe_analysis_path(resume_id)
        if not analysis_path.exists():
            raise JobMatchAPIError(
                404,
                "resume_not_found",
                "Resume analysis was not found. Please analyze a resume before matching it against a job.",
            )

        try:
            with analysis_path.open("r", encoding="utf-8") as handle:
                analysis = json.load(handle)
        except Exception as exc:
            raise JobMatchAPIError(
                500,
                "missing_stored_resume_analysis",
                "Stored resume analysis could not be loaded. Please re-analyze the resume.",
            ) from exc

        parsed_resume = analysis.get("parsed_resume")
        if not isinstance(parsed_resume, dict):
            raise JobMatchAPIError(
                422,
                "resume_not_analyzed",
                "Stored resume evidence is missing. Please re-analyze the resume before job matching.",
            )
        return parsed_resume

    def _safe_analysis_path(self, resume_id: str) -> Path:
        base = self.analysis_dir.resolve()
        candidate = (base / f"{resume_id}.json").resolve()
        if base != candidate.parent:
            raise JobMatchAPIError(
                404,
                "invalid_resume_id",
                "Resume analysis was not found. Please analyze a resume before matching it against a job.",
            )
        return candidate

    def _job_description_text(
        self,
        job_description_text: Optional[str],
        job_description_file_path: Optional[Path | str],
    ) -> str:
        has_text = bool(job_description_text and job_description_text.strip())
        has_file = job_description_file_path is not None

        if has_text and has_file:
            raise JobMatchAPIError(
                400,
                "multiple_job_description_inputs",
                "Use either pasted job description text or one JD document, not both.",
            )
        if not has_text and not has_file:
            raise JobMatchAPIError(
                400,
                "missing_job_description",
                "Please paste a job description or upload a JD document.",
            )

        if has_text:
            try:
                ensure_text_size(job_description_text, MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES)
            except UploadTooLargeError as exc:
                raise JobMatchAPIError(
                    413,
                    "job_description_too_large",
                    "Job description text is too large. Please provide a shorter description.",
                ) from exc
            return job_description_text.strip()

        try:
            text = self.parser.extract_text(str(job_description_file_path))
        except Exception as exc:
            raise JobMatchAPIError(
                400,
                "corrupted_job_description_document",
                "Unable to read this JD document. Please upload a valid PDF or DOCX file.",
            ) from exc

        if not text or not text.strip():
            raise JobMatchAPIError(
                400,
                "empty_job_description",
                "The uploaded JD document did not contain readable text.",
            )
        return text.strip()
