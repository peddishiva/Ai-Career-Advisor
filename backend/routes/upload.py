"""
Upload Route
Handles resume file uploads and triggers analysis
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import uuid
import json
from datetime import datetime

from services.parser_service import ResumeParser
from services.analysis_service import AnalysisService
from services.resume_validator import ResumeValidator
from services.file_upload_service import UploadTooLargeError, copy_upload_with_limit, uploaded_file_size
from config.upload_config import MAX_RESUME_FILE_SIZE_BYTES, UPLOAD_COPY_CHUNK_BYTES

router = APIRouter()

# Storage paths
UPLOAD_DIR = Path("uploads")
ANALYSIS_DIR = Path("uploads/analysis")
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize services
parser = ResumeParser()
analyzer = AnalysisService()
resume_validator = ResumeValidator()

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
    
    file_path = None

    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{file_id}{file_ext}"

        upload_size = _uploaded_file_size(file)
        if upload_size is not None and upload_size > MAX_RESUME_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Resume file is too large. Maximum file size is 5MB.")

        # Save uploaded file
        with file_path.open("wb") as buffer:
            _copy_upload_with_limit(file, buffer)
        
        # Extract text first, then validate before parsing/scoring.
        extracted_text = parser.extract_text(str(file_path))
        validation = resume_validator.validate_text(extracted_text)
        if not validation['valid']:
            if file_path.exists():
                file_path.unlink()
            return JSONResponse(
                status_code=422,
                content={
                    "success": False,
                    "error": "resume_validation_failed",
                    "validation": validation,
                    "message": validation.get("message", "Please upload a valid resume.")
                }
            )
        
        # Parse resume only after the validation gate passes.
        parsed_data = parser.parse_text(extracted_text)
        
        # Generate analysis
        analysis = analyzer.generate_analysis(parsed_data)
        
        # Add metadata
        analysis['metadata'] = {
            'file_id': file_id,
            'filename': file.filename,
            'upload_time': datetime.now().isoformat(),
            'file_type': file_ext
        }

        parsed_resume_for_matching = dict(parsed_data)
        parsed_resume_for_matching.pop('raw_text', None)
        stored_analysis = dict(analysis)
        stored_analysis['parsed_resume'] = parsed_resume_for_matching
        
        # Save analysis to file
        analysis_path = ANALYSIS_DIR / f"{file_id}.json"
        with analysis_path.open("w") as f:
            json.dump(stored_analysis, f, indent=2)
        
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
    
    except HTTPException:
        if file_path and file_path.exists():
            file_path.unlink()
        raise
    except Exception:
        # Clean up file if analysis failed
        if file_path and file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=500,
            detail="Error processing resume. Please try again."
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


def _uploaded_file_size(file: UploadFile):
    return uploaded_file_size(file)


def _copy_upload_with_limit(file: UploadFile, destination) -> None:
    try:
        copy_upload_with_limit(
            file,
            destination,
            MAX_RESUME_FILE_SIZE_BYTES,
            UPLOAD_COPY_CHUNK_BYTES,
        )
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail="Resume file is too large. Maximum file size is 5MB.") from exc
