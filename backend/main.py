"""
AI Career Advisor - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from config.security_config import load_cors_origins
from services.jdxr_retention_service import cleanup_jdxr_storage
from routes.upload import router as upload_router
from routes.analysis import router as analysis_router
from routes.jobs import router as jobs_router
from routes.job_match import router as job_match_router
from routes.jdxr import router as jdxr_router

# Create FastAPI app
app = FastAPI(
    title="AI Career Advisor API",
    description="Backend API for resume analysis and career recommendations",
    version="1.0.0"
)

# Configure CORS from an explicit deployment allowlist.
app.add_middleware(
    CORSMiddleware,
    allow_origins=load_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
cleanup_jdxr_storage(UPLOAD_DIR / "jdxr")

# Include routers
app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(analysis_router, prefix="/api", tags=["Analysis"])
app.include_router(jobs_router, prefix="/api", tags=["Jobs"])
app.include_router(job_match_router, prefix="/api", tags=["Job Match"])
app.include_router(jdxr_router, prefix="/api", tags=["JDxR"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Career Advisor API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "AI Career Advisor Backend"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True
    )
