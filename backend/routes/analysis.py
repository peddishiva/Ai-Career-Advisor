"""
Analysis Route
Provides analysis data for frontend display
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import json

router = APIRouter()

# Storage paths
ANALYSIS_DIR = Path("uploads/analysis")

# In-memory storage (shared with upload route)
from routes.upload import latest_analysis


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
            analysis_path = ANALYSIS_DIR / f"{file_id}.json"
            
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
                "data": analysis
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving analysis: {str(e)}"
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
    
    analysis_path = ANALYSIS_DIR / f"{file_id}.json"
    
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
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting analysis: {str(e)}"
        )
