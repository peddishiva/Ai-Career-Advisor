"""
Job Recommendations Route
Generates AI-powered job recommendations using Gemini API
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import os
import json
import requests
from typing import Optional

router = APIRouter()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent'


@router.get("/jobs/recommendations")
async def get_job_recommendations(
    query: Optional[str] = Query(None, description="Search query for job recommendations"),
    skills: Optional[str] = Query(None, description="Comma-separated skills"),
    location: Optional[str] = Query(None, description="Preferred location")
):
    """
    Generate AI-powered job recommendations based on search query
    
    Query Parameters:
    - query: Job search query (e.g., "software engineer", "data analyst")
    - skills: User's skills (optional)
    - location: Preferred location (optional)
    
    Returns: List of job recommendations with details
    """
    
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Gemini API key not configured. Please set GEMINI_API_KEY environment variable."
        )
    
    try:
        # Build the prompt for Gemini
        prompt = build_job_search_prompt(query, skills, location)
        
        # Call Gemini API
        jobs = await call_gemini_for_jobs(prompt)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "query": query,
                "count": len(jobs),
                "jobs": jobs
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating job recommendations: {str(e)}"
        )


def build_job_search_prompt(query: Optional[str], skills: Optional[str], location: Optional[str]) -> str:
    """Build a prompt for Gemini to generate job recommendations"""
    
    base_prompt = """You are an AI job recommendation system. Generate realistic and relevant job postings based on the user's search criteria.

Search Query: {query}
User Skills: {skills}
Preferred Location: {location}

Generate 6-8 diverse job recommendations that match the search criteria. For each job, provide:

1. title: Job title (string)
2. company: Company name (string, make it realistic but fictional)
3. location: Location (string, include remote options if applicable)
4. salary: Salary range (string, e.g., "$90k - $120k")
5. posted: How long ago posted (string, e.g., "2 days ago", "1 week ago")
6. description: Brief job description (1-2 sentences)
7. tags: Array of 3-5 relevant skills/technologies (array of strings)
8. type: Employment type (string: "Full-time", "Part-time", "Contract")
9. experience: Required experience level (string: "Entry", "Mid", "Senior", "Lead")

Make the jobs diverse in terms of:
- Company size (startups, mid-size, enterprise)
- Location (mix of remote, hybrid, on-site)
- Experience levels
- Salary ranges appropriate for the role level

Return ONLY a valid JSON array of job objects. Do not include any markdown formatting or explanations.
"""
    
    return base_prompt.format(
        query=query or "software developer",
        skills=skills or "Not specified",
        location=location or "Any location"
    )


async def call_gemini_for_jobs(prompt: str) -> list:
    """Call Gemini API to generate job recommendations"""
    
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": 0.8,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 4096,
        }
    }
    
    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        if not response.ok:
            error_data = response.json()
            raise Exception(f"Gemini API error: {error_data.get('error', {}).get('message', response.text)}")
        
        data = response.json()
        
        # Extract the generated text
        generated_text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        
        if not generated_text:
            raise Exception("No response from Gemini API")
        
        # Parse the JSON response
        jobs = parse_gemini_response(generated_text)
        
        return jobs
    
    except requests.exceptions.Timeout:
        raise Exception("Gemini API request timed out")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error calling Gemini API: {str(e)}")
    except Exception as e:
        raise Exception(f"Error calling Gemini API: {str(e)}")


def parse_gemini_response(response_text: str) -> list:
    """Parse Gemini's response and extract job listings"""
    
    try:
        # Remove markdown code blocks if present
        cleaned_text = response_text.strip()
        
        # Remove ```json and ``` markers
        if cleaned_text.startswith('```'):
            # Find the actual JSON content
            lines = cleaned_text.split('\n')
            start_idx = 1 if lines[0].startswith('```') else 0
            end_idx = len(lines) - 1 if lines[-1].strip() == '```' else len(lines)
            cleaned_text = '\n'.join(lines[start_idx:end_idx])
        
        # Parse JSON
        jobs = json.loads(cleaned_text)
        
        # Validate structure
        if not isinstance(jobs, list):
            raise ValueError("Response is not a list")
        
        # Ensure each job has required fields
        required_fields = ['title', 'company', 'location', 'salary', 'description']
        validated_jobs = []
        
        for job in jobs:
            if all(field in job for field in required_fields):
                # Add default values for optional fields
                job.setdefault('posted', '1 day ago')
                job.setdefault('tags', [])
                job.setdefault('type', 'Full-time')
                job.setdefault('experience', 'Mid')
                job.setdefault('id', f"job-{len(validated_jobs) + 1}")
                validated_jobs.append(job)
        
        if not validated_jobs:
            raise ValueError("No valid jobs found in response")
        
        return validated_jobs
    
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse JSON response: {str(e)}")
    except Exception as e:
        raise Exception(f"Error parsing Gemini response: {str(e)}")
