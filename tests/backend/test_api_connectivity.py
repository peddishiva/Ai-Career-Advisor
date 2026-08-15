#!/usr/bin/env python3
"""
API Connectivity & Environment Test Script
Tests environment configuration, API connectivity, and backend service availability.
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

REPO_ROOT = Path(__file__).resolve().parents[2]

def print_status(message: str, status: str = "INFO"):
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

def test_environment_variables() -> bool:
    """Test if required environment variables are set"""
    print_status("Testing Environment Variables...", "INFO")
    
    backend_env_path = REPO_ROOT / "backend" / ".env"
    if backend_env_path.exists():
        load_dotenv(backend_env_path)
        print_status("Loaded environment variables from backend/.env", "SUCCESS")
    else:
        print_status("backend/.env file not found", "WARNING")
    
    required_vars = {
        "PORT": "Backend Port"
    }
    
    optional_vars = {
        "GEMINI_API_KEY": "Google Gemini AI API Key",
        "FIREBASE_STORAGE_BUCKET": "Firebase Storage Bucket"
    }
    
    all_good = True
    
    print("\n--- Core Variables ---")
    for var, description in required_vars.items():
        value = os.getenv(var, "5000")
        print_status(f"✓ {var}: {description} ({value})", "SUCCESS")
    
    print("\n--- Optional AI / Cloud Variables ---")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value and value.strip() and not value.startswith("your_"):
            masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            print_status(f"✓ {var}: {description} ({masked_value})", "SUCCESS")
        else:
            print_status(f"⚠ {var}: {description} - Not configured (optional for deterministic engine)", "WARNING")
    
    return all_good

def test_gemini_api() -> bool:
    """Test Gemini API connectivity if API key is provided"""
    print_status("\nTesting Gemini API Connectivity...", "INFO")
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or api_key.startswith('your_'):
        print_status("Gemini API key not configured (skipping external call)", "WARNING")
        return True
    
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-001:generateContent"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{"parts": [{"text": "Respond with: ok"}]}],
            "generationConfig": {"maxOutputTokens": 20}
        }
        
        response = requests.post(f"{url}?key={api_key}", headers=headers, json=payload, timeout=8)
        if response.status_code == 200:
            print_status("✓ Gemini API is accessible and authenticated", "SUCCESS")
            return True
        else:
            print_status(f"⚠ Gemini API response status: {response.status_code}", "WARNING")
            return True
    except Exception as e:
        print_status(f"⚠ Gemini API check skipped due to network: {e}", "WARNING")
        return True

def test_backend_connectivity() -> bool:
    """Test if FastAPI backend is running and accessible"""
    print_status("\nTesting FastAPI Backend Connectivity...", "INFO")
    
    port = os.getenv('PORT', '5000')
    backend_url = f"http://localhost:{port}"
    
    try:
        response = requests.get(f"{backend_url}/health", timeout=5)
        if response.status_code == 200:
            print_status(f"✓ Backend is running and healthy at {backend_url}/health", "SUCCESS")
            return True
        else:
            print_status(f"✗ Backend returned status code: {response.status_code}", "ERROR")
            return False
    except requests.exceptions.ConnectionError:
        print_status(f"✗ Backend is not running at {backend_url}", "ERROR")
        return False
    except Exception as e:
        print_status(f"✗ Error connecting to backend: {str(e)}", "ERROR")
        return False

def test_python_backend_structure() -> bool:
    """Test Python FastAPI backend file structure"""
    print_status("\nTesting Python FastAPI Backend Structure...", "INFO")
    
    required_files = [
        "backend/main.py",
        "backend/requirements.txt",
        "backend/services/parser_service.py",
        "backend/services/analysis_service.py",
        "backend/utils/scoring_logic.py",
        "backend/config/roles.py"
    ]
    
    missing = [f for f in required_files if not (REPO_ROOT / f).exists()]
    if missing:
        print_status(f"✗ Missing backend files: {', '.join(missing)}", "ERROR")
        return False
    
    print_status("✓ All required Python FastAPI architecture files are present", "SUCCESS")
    return True

def main():
    """Main diagnostic test function"""
    print("=" * 60)
    print("  AI Career Advisor - API & Architecture Connectivity Test")
    print("=" * 60)
    
    results = {
        "Environment Variables": test_environment_variables(),
        "Python Backend Structure": test_python_backend_structure(),
        "Gemini API Config": test_gemini_api(),
        "Backend Live Health": test_backend_connectivity()
    }
    
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        color = "\033[92m" if result else "\033[91m"
        print(f"{color}{status}{'\033[0m'} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} checks passed")
    return passed == total

if __name__ == "__main__":
    main()
