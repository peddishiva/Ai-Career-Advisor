"""Dedicated JDxR session API."""

from typing import Optional

from fastapi import APIRouter, Body, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from ai.contracts import AITaskType
from services.ai_enrichment_service import AIEnrichmentError, AIEnrichmentService
from services.jdxr_session_service import JdxrSessionError, JdxrSessionService


router = APIRouter()
jdxr_session_service = JdxrSessionService()
ai_enrichment_service = AIEnrichmentService()


class JdxrAIRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: AITaskType = AITaskType.JDXR_MATCH_EXPLANATION


@router.post("/jdxr/session")
async def create_jdxr_session():
    return JSONResponse(status_code=201, content={"success": True, "session": jdxr_session_service.create_session()})


@router.get("/jdxr/session/{session_id}")
async def get_jdxr_session(session_id: str):
    try:
        return JSONResponse(status_code=200, content={"success": True, "session": jdxr_session_service.get_session(session_id)})
    except JdxrSessionError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.payload)
    except Exception:
        return JSONResponse(status_code=500, content={"success": False, "error": "jdxr_session_failed", "message": "Unable to load the JDxR session."})


@router.post("/jdxr/session/{session_id}/jd")
async def submit_jdxr_jd(
    session_id: str,
    request: Request,
    job_description: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    try:
        if "application/json" in request.headers.get("content-type", "").lower():
            payload = await request.json()
            job_description = job_description or payload.get("job_description")
        if file and job_description and job_description.strip():
            raise JdxrSessionError(400, "multiple_job_description_inputs", "Use either pasted job description text or one JD document, not both.")
        if file:
            session = jdxr_session_service.submit_jd_upload(session_id, file)
        else:
            session = jdxr_session_service.submit_jd_text(session_id, job_description or "")
        return JSONResponse(status_code=200, content={"success": True, "session": session})
    except JdxrSessionError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.payload)
    except Exception:
        return JSONResponse(status_code=500, content={"success": False, "error": "jdxr_jd_failed", "message": "Unable to process this job description."})
    finally:
        if file:
            await file.close()


@router.post("/jdxr/session/{session_id}/resume")
async def submit_jdxr_resume(session_id: str, file: Optional[UploadFile] = File(None)):
    if not file:
        return JSONResponse(status_code=400, content={"success": False, "error": "missing_resume", "message": "Please upload a resume for this JDxR session."})
    try:
        session = jdxr_session_service.submit_resume_upload(session_id, file)
        return JSONResponse(status_code=200, content={"success": True, "session": session})
    except JdxrSessionError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.payload)
    except Exception:
        return JSONResponse(status_code=500, content={"success": False, "error": "jdxr_resume_failed", "message": "Unable to process this resume."})
    finally:
        await file.close()


@router.post("/jdxr/session/{session_id}/analyze")
async def analyze_jdxr_session(session_id: str):
    try:
        return JSONResponse(status_code=200, content=jdxr_session_service.analyze(session_id))
    except JdxrSessionError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.payload)
    except Exception:
        return JSONResponse(status_code=500, content={"success": False, "error": "jdxr_analysis_failed", "message": "Unable to compare this resume with the job description."})


@router.post("/jdxr/session/{session_id}/ai")
async def generate_jdxr_ai(
    session_id: str,
    request: JdxrAIRequest | None = Body(default=None),
):
    """Generate explicit, optional AI enrichment for the current JDxR session."""
    task = request.task if request else AITaskType.JDXR_MATCH_EXPLANATION
    try:
        if task not in {
            AITaskType.JDXR_MATCH_EXPLANATION,
            AITaskType.JDXR_GAP_EXPLANATION,
            AITaskType.JDXR_RESUME_IMPROVEMENT,
            AITaskType.JDXR_INTERVIEW_GUIDANCE,
        }:
            raise AIEnrichmentError(422, "unsupported_ai_task", "This AI task is not supported for JDxR.")
        result = ai_enrichment_service.enrich_jdxr(
            session_id,
            task,
            session_service=jdxr_session_service,
        )
        return JSONResponse(status_code=200, content={"success": True, **result.model_dump(mode="json")})
    except JdxrSessionError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.payload)
    except AIEnrichmentError as exc:
        return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.error, "message": exc.message})
    except Exception:
        return JSONResponse(status_code=500, content={"success": False, "error": "jdxr_ai_failed", "message": "Unable to generate AI guidance for this session."})


@router.post("/jdxr/session/{session_id}/ai/improvements")
async def generate_jdxr_improvements(session_id: str):
    """Generate explicit Phase 3D resume improvements for the selected JDxR session."""
    try:
        result = ai_enrichment_service.enrich_jdxr_improvements(
            session_id,
            session_service=jdxr_session_service,
        )
        return JSONResponse(status_code=200, content={"success": True, **result.model_dump(mode="json")})
    except JdxrSessionError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.payload)
    except AIEnrichmentError as exc:
        return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.error, "message": exc.message})
    except Exception:
        return JSONResponse(status_code=500, content={"success": False, "error": "jdxr_improvements_failed", "message": "Unable to generate resume improvement guidance for this session."})
