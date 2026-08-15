#!/usr/bin/env python3
"""
Complete Project Workflow Test
Tests the entire data flow from resume upload to AI analysis and job recommendations
"""

import os
import sys
import json
import requests
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path("backend/.env"))

def print_status(message, status="INFO"):
    """Print colored status messages"""
    colors = {
        "SUCCESS": "\033[92m",  # Green
        "ERROR": "\033[91m",    # Red
        "WARNING": "\033[93m",  # Yellow
        "INFO": "\033[94m",     # Blue
        "RESET": "\033[0m"      # Reset
    }
    
    color = colors.get(status, colors["INFO"])
    print(f"{color}[{status}]{colors['RESET']} {message}")

def test_backend_endpoints():
    """Test all backend API endpoints"""
    print_status("Testing Backend API Endpoints...", "INFO")
    
    base_url = "http://localhost:5000"
    
    endpoints = [
        ("/", "Root endpoint"),
        ("/health", "Health check"),
        ("/docs", "API documentation"),
    ]
    
    results = {}
    
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print_status(f"✓ {endpoint} - {description}", "SUCCESS")
                results[endpoint] = True
            else:
                print_status(f"✗ {endpoint} - Status: {response.status_code}", "ERROR")
                results[endpoint] = False
        except Exception as e:
            print_status(f"✗ {endpoint} - Error: {str(e)}", "ERROR")
            results[endpoint] = False
    
    return all(results.values())

def test_resume_upload_workflow():
    """Test resume upload and analysis workflow"""
    print_status("\nTesting Resume Upload Workflow...", "INFO")
    
    base_url = "http://localhost:5000"
    
    # Use an existing test PDF file
    test_pdf_path = Path("backend/node_modules/pdf-parse/test/data/04-valid.pdf")
    
    if not test_pdf_path.exists():
        print_status("✗ Test PDF file not found", "ERROR")
        return False
    
    try:
        # Test file upload
        print_status("Uploading test PDF resume...", "INFO")
        
        with open(test_pdf_path, "rb") as f:
            files = {"file": ("test_resume.pdf", f, "application/pdf")}
            response = requests.post(f"{base_url}/api/upload", files=files, timeout=30)
        
        if response.status_code == 200:
            upload_data = response.json()
            print_status("✓ Resume uploaded successfully", "SUCCESS")
            print(f"  Upload response: {json.dumps(upload_data, indent=2)}")
            
            # Test analysis retrieval
            print_status("Retrieving analysis results...", "INFO")
            analysis_response = requests.get(f"{base_url}/api/analysis", timeout=10)
            
            if analysis_response.status_code == 200:
                analysis_data = analysis_response.json()
                print_status("✓ Analysis retrieved successfully", "SUCCESS")
                
                # Validate analysis structure
                if "data" in analysis_data:
                    analysis = analysis_data["data"]
                    required_fields = ["overall_insights", "metrics", "candidate_info", "role_matches"]
                    
                    missing_fields = [field for field in required_fields if field not in analysis]
                    if not missing_fields:
                        print_status("✓ Analysis structure is valid", "SUCCESS")
                        
                        # Print key analysis results
                        fit_score = analysis.get("overall_insights", {}).get("fit_score", "N/A")
                        role_alignment = analysis.get("metrics", {}).get("role_alignment", "N/A")
                        
                        print(f"  Fit Score: {fit_score}")
                        print(f"  Role Alignment: {role_alignment}")
                        
                        return True
                    else:
                        print_status(f"✗ Analysis missing fields: {missing_fields}", "ERROR")
                        return False
                else:
                    print_status("✗ Invalid analysis response format", "ERROR")
                    return False
            else:
                print_status(f"✗ Analysis retrieval failed: {analysis_response.status_code}", "ERROR")
                return False
        else:
            print_status(f"✗ Resume upload failed: {response.status_code}", "ERROR")
            try:
                error_data = response.json()
                print(f"  Error: {error_data.get('detail', response.text)}")
            except:
                print(f"  Error: {response.text}")
            return False
            
    except Exception as e:
        print_status(f"✗ Upload workflow error: {str(e)}", "ERROR")
        return False
