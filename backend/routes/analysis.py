"""
Analysis Route
Provides analysis data for frontend display
"""

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import json
import re
from pydantic import BaseModel, ConfigDict

from ai.contracts import AITaskType
from config.ai_config import AI_REQUEST_COOLDOWN_SECONDS
from services.ai_enrichment_service import AIEnrichmentError, AIEnrichmentService
from services.ai_request_guard import AIRequestGuard

router = APIRouter()

# Storage paths
ANALYSIS_DIR = Path("uploads/analysis")

# In-memory storage (shared with upload route)
from routes.upload import latest_analysis


FILE_ID_PATTERN = re.compile(r"^[a-fA-F0-9-]{36}$")
ai_enrichment_service = AIEnrichmentService()
ai_request_guard = AIRequestGuard(AI_REQUEST_COOLDOWN_SECONDS)


class AIAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: AITaskType = AITaskType.RESUME_CAREER_GUIDANCE


def public_analysis_payload(analysis: dict) -> dict:
    """Return analysis data without backend-only resume evidence."""
    public_analysis = dict(analysis)
    public_analysis.pop("parsed_resume", None)
    return public_analysis


@router.get("/analysis")
async def get_analysis(file_id: str = None):
    """
    Get analysis results

    An explicit file_id is required so one user's latest upload cannot be
    returned to another request in this unauthenticated deployment.
    """
    
    try:
        if not file_id:
            raise HTTPException(status_code=422, detail="An explicit file_id is required to retrieve an analysis.")

        analysis_path = _safe_analysis_path(file_id)

        if not analysis_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Analysis not found for file_id: {file_id}"
            )

        with analysis_path.open("r", encoding="utf-8") as f:
            analysis = json.load(f)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": public_analysis_payload(analysis)
            }
        )
    
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error retrieving analysis. Please try again."
        )


@router.get("/analysis/summary")
async def get_analysis_summary(file_id: str = None):
    """Get a summary for one explicit analysis."""
    if not file_id:
        raise HTTPException(status_code=422, detail="An explicit file_id is required to retrieve an analysis summary.")

    analysis_path = _safe_analysis_path(file_id)
    if not analysis_path.exists():
        raise HTTPException(status_code=404, detail="Analysis not found.")
    try:
        with analysis_path.open("r", encoding="utf-8") as handle:
            analysis = json.load(handle)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Error retrieving analysis summary.") from exc
    
    summary = {
        'fit_score': analysis['overall_insights']['fit_score'],
        'role_alignment': analysis['metrics']['role_alignment'],
        'top_role': analysis['role_matches'][0]['title'] if analysis['role_matches'] else None,
        'skills_count': analysis['candidate_info']['skills_count'],
        'upload_time': analysis['metadata']['upload_time']
    }
    
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "summary": summary
        }
    )


@router.post("/analysis/ai")
async def generate_analysis_ai(
    file_id: str | None = None,
    request: AIAnalysisRequest | None = Body(default=None),
):
    """Generate explicit, optional AI enrichment for one resume analysis."""
    if not file_id:
        raise HTTPException(status_code=422, detail="An explicit file_id is required for AI analysis.")
    selected_file_id = file_id
    try:
        task = request.task if request else AITaskType.RESUME_CAREER_GUIDANCE
        if task not in {AITaskType.RESUME_EXPLANATION, AITaskType.RESUME_CAREER_GUIDANCE}:
            raise AIEnrichmentError(422, "unsupported_ai_task", "This AI task is not supported for Resume Analysis.")
        if ai_enrichment_service.orchestrator.enabled and not ai_request_guard.allow(
            "resume_analysis", selected_file_id, task.value, ""
        ):
            return JSONResponse(
                status_code=429,
                content={"success": False, "error": "ai_request_cooldown", "message": "Please wait before requesting AI guidance again."},
            )
        result = ai_enrichment_service.enrich_resume(selected_file_id, task)
        return JSONResponse(status_code=200, content={"success": True, **result.model_dump(mode="json")})
    except AIEnrichmentError as exc:
        return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.error, "message": exc.message})


@router.post("/analysis/ai/improvements")
async def generate_analysis_improvements(file_id: str | None = None):
    """Generate explicit Phase 3D resume improvement guidance for one analysis."""
    if not file_id:
        raise HTTPException(status_code=422, detail="An explicit resume analysis file_id is required.")
    try:
        if ai_enrichment_service.orchestrator.enabled and not ai_request_guard.allow(
            "resume_analysis", file_id, AITaskType.RESUME_IMPROVEMENT.value, ""
        ):
            return JSONResponse(
                status_code=429,
                content={"success": False, "error": "ai_request_cooldown", "message": "Please wait before requesting resume improvements again."},
            )
        result = ai_enrichment_service.enrich_resume_improvements(file_id)
        return JSONResponse(status_code=200, content={"success": True, **result.model_dump(mode="json")})
    except AIEnrichmentError as exc:
        return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.error, "message": exc.message})


@router.delete("/analysis/{file_id}")
async def delete_analysis(file_id: str):
    """Delete a specific analysis"""
    
    analysis_path = _safe_analysis_path(file_id)
    
    if not analysis_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Analysis not found for file_id: {file_id}"
        )
    
    try:
        analysis_path.unlink()
        
        # Clear from memory if it's the current analysis
        if latest_analysis.get('file_id') == file_id:
            latest_analysis.clear()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Analysis {file_id} deleted successfully"
            }
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error deleting analysis. Please try again."
        )


def _safe_analysis_path(file_id: str) -> Path:
    if not FILE_ID_PATTERN.fullmatch(file_id or ""):
        raise HTTPException(status_code=404, detail="Analysis not found.")

    base = ANALYSIS_DIR.resolve()
    candidate = (base / f"{file_id}.json").resolve()
    if candidate.parent != base:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return candidate
