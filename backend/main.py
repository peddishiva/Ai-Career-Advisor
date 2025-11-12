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

from routes.upload import router as upload_router
from routes.analysis import router as analysis_router
from routes.jobs import router as jobs_router

# Create FastAPI app
app = FastAPI(
    title="AI Career Advisor API",
    description="Backend API for resume analysis and career recommendations",
    version="1.0.0"
)

# Configure CORS - Allow all localhost ports for development
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",  # Allow any localhost port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Include routers
app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(analysis_router, prefix="/api", tags=["Analysis"])
app.include_router(jobs_router, prefix="/api", tags=["Jobs"])

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
