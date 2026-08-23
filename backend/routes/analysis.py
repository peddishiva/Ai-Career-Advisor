"""
Analysis Route
Provides analysis data for frontend display
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import json
import re

router = APIRouter()

# Storage paths
ANALYSIS_DIR = Path("uploads/analysis")

# In-memory storage (shared with upload route)
from routes.upload import latest_analysis


FILE_ID_PATTERN = re.compile(r"^[a-fA-F0-9-]{36}$")


def public_analysis_payload(analysis: dict) -> dict:
    """Return analysis data without backend-only resume evidence."""
    public_analysis = dict(analysis)
    public_analysis.pop("parsed_resume", None)
    return public_analysis


@router.get("/analysis")
async def get_analysis(file_id: str = None):
    """
    Get analysis results
    
    If file_id is provided, retrieves specific analysis
    Otherwise, returns the latest analysis
    """
    
    try:
        if file_id:
            # Load specific analysis from file
            analysis_path = _safe_analysis_path(file_id)
            
            if not analysis_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Analysis not found for file_id: {file_id}"
                )
            
            with analysis_path.open("r") as f:
                analysis = json.load(f)
        else:
            # Return latest analysis from memory
            if not latest_analysis or 'current' not in latest_analysis:
                raise HTTPException(
                    status_code=404,
                    detail="No analysis available. Please upload a resume first."
                )
            
            analysis = latest_analysis['current']
        
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
async def get_analysis_summary():
    """Get a summary of the latest analysis"""
    
    if not latest_analysis or 'current' not in latest_analysis:
        raise HTTPException(
            status_code=404,
            detail="No analysis available"
        )
    
    analysis = latest_analysis['current']
    
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
