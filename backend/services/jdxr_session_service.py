"""Filesystem-backed, isolated JDxR session orchestration."""

import json
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from config.job_description_config import MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES
from config.upload_config import MAX_RESUME_FILE_SIZE_BYTES, UPLOAD_COPY_CHUNK_BYTES
from services.file_upload_service import (
    UploadTooLargeError,
    copy_upload_with_limit,
    ensure_text_size,
    uploaded_file_size,
)
from services.job_description_parser import JobDescriptionParser
from services.job_description_validator import JobDescriptionValidator
from services.job_match_service import JobMatchService
from services.parser_service import ResumeParser
from services.resume_validator import ResumeValidator


class JdxrSessionError(Exception):
    """User-safe API error for JDxR session operations."""

    def __init__(self, status_code: int, error: str, message: str, **extra: Any):
        super().__init__(message)
        self.status_code = status_code
        self.payload = {
            "success": False,
            "error": error,
            "message": message,
            **extra,
        }


class JdxrSessionService:
    """Create and operate on independent JDxR sessions."""

    SESSION_ID_PATTERN = re.compile(r"^[a-fA-F0-9-]{36}$")
    SUPPORTED_RESUME_TYPES = {".pdf", ".docx", ".doc"}
    SUPPORTED_JD_TYPES = {".pdf", ".docx", ".doc"}

    def __init__(
        self,
        root_dir: Path | str = Path("uploads/jdxr"),
        resume_parser: Optional[ResumeParser] = None,
        resume_validator: Optional[ResumeValidator] = None,
        jd_parser: Optional[JobDescriptionParser] = None,
        jd_validator: Optional[JobDescriptionValidator] = None,
        matcher: Optional[JobMatchService] = None,
    ):
        self.root_dir = Path(root_dir)
        self.resume_parser = resume_parser or ResumeParser()
        self.resume_validator = resume_validator or ResumeValidator()
        self.jd_parser = jd_parser or JobDescriptionParser()
        self.jd_validator = jd_validator or JobDescriptionValidator()
        self.matcher = matcher or JobMatchService()

    def create_session(self) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        session_dir = self._session_dir(session_id, create=True)
        (session_dir / "resume").mkdir(parents=True, exist_ok=True)
        (session_dir / "jd").mkdir(parents=True, exist_ok=True)
        now = self._now()
        state = {
            "session_id": session_id,
            "created_at": now,
            "updated_at": now,
            "status": "created",
            "jd": {"status": "missing"},
            "resume": {"status": "missing"},
            "parsed_jd": None,
            "parsed_resume": None,
            "match_result": None,
        }
        self._write_state(session_dir, state)
        return self.public_state(state)

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return self.public_state(self._read_state(session_id))

    def submit_jd_text(self, session_id: str, text: str, filename: Optional[str] = None) -> Dict[str, Any]:
        state, session_dir = self._load_for_update(session_id)
        text = (text or "").strip()
        if not text:
            raise self._input_error("empty_job_description", "Please paste a job description or upload a JD document.")
        try:
            ensure_text_size(text, MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES)
        except UploadTooLargeError as exc:
            raise self._jd_too_large_error() from exc

        validation = self.jd_validator.validate_text(text)
        if not validation.get("valid"):
            self._clear_jd_state(state, session_dir)
            state["jd"] = {"status": "invalid", "validation": validation}
            self._save_updated_state(session_dir, state)
            classification = validation.get("classification")
            error = "uncertain_job_description" if classification == "uncertain" else "not_a_job_description"
            raise JdxrSessionError(422, error, validation.get("message", "This does not appear to be a valid job description."), session=self.public_state(state))

        parsed_jd = self.jd_parser.parse_text(text)
        parsed_jd.pop("raw_text", None)
        document_id = str(uuid.uuid4())
        source_path = session_dir / "jd" / f"{document_id}.txt"
        source_path.write_text(text, encoding="utf-8")
        self._clear_jd_files(session_dir, keep=source_path)
        state["parsed_jd"] = parsed_jd
        state["jd"] = self._jd_metadata(parsed_jd, validation, filename or "pasted-job-description.txt", document_id, len(text.encode("utf-8")))
        state["match_result"] = None
        state["status"] = self._session_status(state)
        self._save_updated_state(session_dir, state)
        return self.public_state(state)

    def submit_jd_upload(self, session_id: str, file) -> Dict[str, Any]:
        filename, suffix = self._validate_upload_name(file, self.SUPPORTED_JD_TYPES, "job description")
        state, session_dir = self._load_for_update(session_id)
        document_id = str(uuid.uuid4())
        destination = session_dir / "jd" / f"{document_id}{suffix}"
        try:
            size = uploaded_file_size(file)
            if size is not None and size > MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES:
                raise self._jd_too_large_error()
            with destination.open("wb") as handle:
                try:
                    bytes_written = copy_upload_with_limit(
                        file, handle, MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES, UPLOAD_COPY_CHUNK_BYTES
                    )
                except UploadTooLargeError as exc:
                    raise self._jd_too_large_error() from exc
            text = self.jd_parser.extract_text(str(destination))
        except JdxrSessionError:
            self._unlink(destination)
            raise
        except Exception as exc:
            self._unlink(destination)
            raise JdxrSessionError(400, "corrupted_job_description_document", "Unable to read this JD document. Please upload a valid PDF or DOCX file.") from exc

        try:
            ensure_text_size(text, MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES)
        except UploadTooLargeError as exc:
            self._unlink(destination)
            raise self._jd_too_large_error() from exc
        validation = self.jd_validator.validate_text(text)
        if not validation.get("valid"):
            self._clear_jd_state(state, session_dir)
            state["jd"] = {"status": "invalid", "validation": validation}
            self._save_updated_state(session_dir, state)
            self._unlink(destination)
            classification = validation.get("classification")
            error = "uncertain_job_description" if classification == "uncertain" else "not_a_job_description"
            raise JdxrSessionError(422, error, validation.get("message", "This does not appear to be a valid job description."), session=self.public_state(state))

        parsed_jd = self.jd_parser.parse_text(text)
        parsed_jd.pop("raw_text", None)
        self._clear_jd_files(session_dir, keep=destination)
        state["parsed_jd"] = parsed_jd
        state["jd"] = self._jd_metadata(parsed_jd, validation, filename, document_id, bytes_written)
        state["match_result"] = None
        state["status"] = self._session_status(state)
        self._save_updated_state(session_dir, state)
        return self.public_state(state)

    def submit_resume_upload(self, session_id: str, file) -> Dict[str, Any]:
        filename, suffix = self._validate_upload_name(file, self.SUPPORTED_RESUME_TYPES, "resume")
        state, session_dir = self._load_for_update(session_id)
        if state.get("jd", {}).get("status") != "valid" or not state.get("parsed_jd"):
            raise JdxrSessionError(409, "jd_required", "Validate a job description before uploading a resume for comparison.", session=self.public_state(state))
        document_id = str(uuid.uuid4())
        destination = session_dir / "resume" / f"{document_id}{suffix}"
        try:
            size = uploaded_file_size(file)
            if size is not None and size > MAX_RESUME_FILE_SIZE_BYTES:
                raise self._resume_too_large_error()
            with destination.open("wb") as handle:
                try:
                    bytes_written = copy_upload_with_limit(
                        file, handle, MAX_RESUME_FILE_SIZE_BYTES, UPLOAD_COPY_CHUNK_BYTES
                    )
                except UploadTooLargeError as exc:
                    raise self._resume_too_large_error() from exc
            text = self.resume_parser.extract_text(str(destination))
        except JdxrSessionError:
            self._unlink(destination)
            raise
        except Exception as exc:
            self._unlink(destination)
            raise JdxrSessionError(400, "corrupted_resume_document", "Unable to read this resume. Please upload a valid PDF or DOCX file.") from exc

        validation = self.resume_validator.validate_text(text)
        if not validation.get("valid"):
            self._clear_resume_state(state, session_dir)
            state["resume"] = {"status": "invalid", "validation": validation}
            self._save_updated_state(session_dir, state)
            self._unlink(destination)
            raise JdxrSessionError(422, "resume_validation_failed", validation.get("message", "Please upload a valid resume."), session=self.public_state(state))

        parsed_resume = self.resume_parser.parse_text(text)
        parsed_resume.pop("raw_text", None)
        self._clear_resume_files(session_dir, keep=destination)
        state["parsed_resume"] = parsed_resume
        state["resume"] = {
            "status": "valid",
            "filename": filename,
            "size_bytes": bytes_written,
            "document_id": document_id,
            "validation": validation,
            "experience_count": len(parsed_resume.get("experience", [])),
            "project_count": len(parsed_resume.get("projects", [])),
            "education_count": len(parsed_resume.get("education", [])),
            "certification_count": len(parsed_resume.get("certifications", [])),
        }
        state["match_result"] = None
        state["status"] = self._session_status(state)
        self._save_updated_state(session_dir, state)
        return self.public_state(state)

    def analyze(self, session_id: str) -> Dict[str, Any]:
        state, session_dir = self._load_for_update(session_id)
        if state.get("jd", {}).get("status") != "valid" or not state.get("parsed_jd"):
            raise JdxrSessionError(409, "jd_required", "Validate a job description before comparing a resume.", session=self.public_state(state))
        if state.get("resume", {}).get("status") != "valid" or not state.get("parsed_resume"):
            raise JdxrSessionError(409, "resume_required", "Upload and validate a resume before comparing it with the job.", session=self.public_state(state))

        match = self.matcher.match(state["parsed_resume"], state["parsed_jd"])
        state["match_result"] = match
        state["status"] = "analyzed"
        self._save_updated_state(session_dir, state)
        return self.result_payload(state)

    def result_payload(self, state: Dict[str, Any]) -> Dict[str, Any]:
        parsed_jd = state.get("parsed_jd") or {}
        return {
            "success": True,
            "session": self.public_state(state),
            "job": {
                "job_title": parsed_jd.get("job_title"),
                "company": parsed_jd.get("company"),
                "location": parsed_jd.get("location"),
                "employment_type": parsed_jd.get("employment_type"),
            },
            "match": state.get("match_result"),
        }

    def get_ai_source(self, session_id: str) -> Dict[str, Any]:
        """Return only the current session's deterministic AI input boundary."""
        state = self._read_state(session_id)
        if state.get("jd", {}).get("status") != "valid" or not state.get("parsed_jd"):
            raise JdxrSessionError(409, "jd_required", "Validate a job description before requesting AI guidance.")
        if state.get("resume", {}).get("status") != "valid" or not state.get("parsed_resume"):
            raise JdxrSessionError(409, "resume_required", "Upload and validate a resume before requesting AI guidance.")
        if not state.get("match_result"):
            raise JdxrSessionError(409, "analysis_required", "Compare the resume with the job before requesting AI guidance.")
        return {
            "resume_id": state["resume"].get("document_id") or session_id,
            "jd_id": state["jd"].get("document_id") or session_id,
            "parsed_resume": deepcopy(state["parsed_resume"]),
            "parsed_jd": deepcopy(state["parsed_jd"]),
            "deterministic_result": deepcopy(state["match_result"]),
        }

    def public_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        public = {
            "session_id": state["session_id"],
            "created_at": state["created_at"],
            "updated_at": state["updated_at"],
            "status": state.get("status"),
            "jd": dict(state.get("jd") or {}),
            "resume": dict(state.get("resume") or {}),
        }
        if state.get("match_result") is not None:
            public["has_match_result"] = True
        return public

    def _validate_upload_name(self, file, allowed_types: set[str], label: str) -> tuple[str, str]:
        filename = getattr(file, "filename", None) or ""
        suffix = Path(filename).suffix.lower()
        if not filename:
            raise JdxrSessionError(400, f"missing_{label.replace(' ', '_')}", f"Please upload a {label} document.")
        if suffix not in allowed_types:
            raise JdxrSessionError(400, f"unsupported_{label.replace(' ', '_')}_document", f"Unsupported {label} type. Please upload a PDF, DOCX, or DOC file.")
        return filename, suffix

    def _jd_metadata(self, parsed: Dict[str, Any], validation: Dict[str, Any], filename: str, document_id: str, size_bytes: int) -> Dict[str, Any]:
        required_count = len(parsed.get("required_qualifications", []))
        preferred_count = len(parsed.get("preferred_qualifications", []))
        return {
            "status": "valid",
            "filename": filename,
            "size_bytes": size_bytes,
            "document_id": document_id,
            "validation": validation,
            "job_title": parsed.get("job_title"),
            "company": parsed.get("company"),
            "required_count": required_count,
            "preferred_count": preferred_count,
            "required_skill_count": len(parsed.get("required_skills", [])),
            "preferred_skill_count": len(parsed.get("preferred_skills", [])),
            "capability_count": len(parsed.get("required_capability_requirements", [])) + len(parsed.get("preferred_capability_requirements", [])),
            "eligibility_count": len(parsed.get("required_eligibility_requirements", [])) + len(parsed.get("preferred_eligibility_requirements", [])),
            "availability_count": len(parsed.get("required_availability_requirements", [])) + len(parsed.get("preferred_availability_requirements", [])),
            "experience_count": len(parsed.get("experience_requirements", [])),
            "education_count": len(parsed.get("education_requirements", [])),
        }

    def _load_for_update(self, session_id: str) -> tuple[Dict[str, Any], Path]:
        session_dir = self._session_dir(session_id)
        state_path = session_dir / "session.json"
        if not state_path.exists():
            raise JdxrSessionError(404, "session_not_found", "JDxR session was not found.")
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise JdxrSessionError(500, "session_unreadable", "JDxR session could not be loaded.") from exc
        return state, session_dir

    def _read_state(self, session_id: str) -> Dict[str, Any]:
        return self._load_for_update(session_id)[0]

    def _session_dir(self, session_id: str, create: bool = False) -> Path:
        if not self.SESSION_ID_PATTERN.fullmatch(session_id or ""):
            raise JdxrSessionError(404, "invalid_session_id", "JDxR session was not found.")
        base = self.root_dir.resolve()
        if create:
            base.mkdir(parents=True, exist_ok=True)
        candidate = (base / session_id).resolve()
        if candidate.parent != base:
            raise JdxrSessionError(404, "invalid_session_id", "JDxR session was not found.")
        return candidate

    def _write_state(self, session_dir: Path, state: Dict[str, Any]) -> None:
        session_dir.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = self._now()
        (session_dir / "session.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _save_updated_state(self, session_dir: Path, state: Dict[str, Any]) -> None:
        self._write_state(session_dir, state)

    def _clear_jd_state(self, state: Dict[str, Any], session_dir: Path) -> None:
        state["parsed_jd"] = None
        state["match_result"] = None
        self._clear_jd_files(session_dir)
        state["status"] = self._session_status(state)

    def _clear_resume_state(self, state: Dict[str, Any], session_dir: Path) -> None:
        state["parsed_resume"] = None
        state["match_result"] = None
        self._clear_resume_files(session_dir)
        state["status"] = self._session_status(state)

    def _clear_jd_files(self, session_dir: Path, keep: Optional[Path] = None) -> None:
        self._clear_files(session_dir / "jd", keep)

    def _clear_resume_files(self, session_dir: Path, keep: Optional[Path] = None) -> None:
        self._clear_files(session_dir / "resume", keep)

    def _clear_files(self, directory: Path, keep: Optional[Path] = None) -> None:
        if not directory.exists():
            return
        keep_resolved = keep.resolve() if keep else None
        for path in directory.iterdir():
            if path.is_file() and (keep_resolved is None or path.resolve() != keep_resolved):
                self._unlink(path)

    def _session_status(self, state: Dict[str, Any]) -> str:
        jd_valid = state.get("jd", {}).get("status") == "valid"
        resume_valid = state.get("resume", {}).get("status") == "valid"
        if jd_valid and resume_valid:
            return "ready"
        if jd_valid:
            return "jd_valid"
        if resume_valid:
            return "resume_valid"
        return "created"

    def _input_error(self, error: str, message: str) -> JdxrSessionError:
        return JdxrSessionError(400, error, message)

    def _jd_too_large_error(self) -> JdxrSessionError:
        return JdxrSessionError(413, "job_description_file_too_large", "JD document is too large. Maximum file size is 5MB.")

    def _resume_too_large_error(self) -> JdxrSessionError:
        return JdxrSessionError(413, "resume_file_too_large", "Resume file is too large. Maximum file size is 5MB.")

    def _unlink(self, path: Path) -> None:
        if path.exists() and path.is_file():
            path.unlink()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
