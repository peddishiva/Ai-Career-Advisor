"""
Upload Route
Handles resume file uploads and triggers analysis
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
import uuid
import json
from datetime import datetime

from services.parser_service import ResumeParser
from services.analysis_service import AnalysisService

router = APIRouter()

# Storage paths
UPLOAD_DIR = Path("uploads")
ANALYSIS_DIR = Path("uploads/analysis")
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize services
parser = ResumeParser()
analyzer = AnalysisService()

# Store latest analysis in memory (in production, use database)
latest_analysis = {}


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload resume file and trigger analysis
    
    Accepts: PDF or DOCX files
    Returns: Analysis results
    """
    
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ['.pdf', '.docx', '.doc']:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and DOCX files are supported."
        )
    
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{file_id}{file_ext}"
        
        # Save uploaded file
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Parse resume
        parsed_data = parser.parse_file(str(file_path))
        
        # Generate analysis
        analysis = analyzer.generate_analysis(parsed_data)
        
        # Add metadata
        analysis['metadata'] = {
            'file_id': file_id,
            'filename': file.filename,
            'upload_time': datetime.now().isoformat(),
            'file_type': file_ext
        }
        
        # Save analysis to file
        analysis_path = ANALYSIS_DIR / f"{file_id}.json"
        with analysis_path.open("w") as f:
            json.dump(analysis, f, indent=2)
        
        # Store in memory for quick access
        latest_analysis['current'] = analysis
        latest_analysis['file_id'] = file_id
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Resume uploaded and analyzed successfully",
                "file_id": file_id,
                "analysis": analysis
            }
        )
    
    except Exception as e:
        # Clean up file if analysis failed
        if file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing resume: {str(e)}"
        )
    
    finally:
        await file.close()


@router.get("/upload/status")
async def get_upload_status():
    """Get status of latest upload"""
    if not latest_analysis:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "No resume has been uploaded yet"
            }
        )
    
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "has_analysis": True,
            "file_id": latest_analysis.get('file_id')
        }
    )
