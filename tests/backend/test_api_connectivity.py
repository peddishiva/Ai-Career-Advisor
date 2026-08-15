#!/usr/bin/env python3
"""
API Connectivity Test Script
Tests all API keys and services used in the AI Career Advisor project
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

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

def test_environment_variables():
    """Test if all required environment variables are set"""
    print_status("Testing Environment Variables...", "INFO")
    
    # Load environment variables from backend/.env file
    backend_env_path = Path("backend/.env")
    if backend_env_path.exists():
        load_dotenv(backend_env_path)
        print_status("Loaded environment variables from backend/.env", "SUCCESS")
    else:
        print_status("backend/.env file not found", "WARNING")
    
    required_vars = {
        "GEMINI_API_KEY": "Google Gemini AI API Key",
        "FIREBASE_STORAGE_BUCKET": "Firebase Storage Bucket",
        "PORT": "Backend Port"
    }
    
    optional_vars = {
        "SWE1_KEY": "Windsurf API Key",
        "NODE_ENV": "Node Environment"
    }
    
    all_good = True
    
    print("\n--- Required Variables ---")
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value and value.strip() and value != f"your_{var.lower()}_here":
            # Mask API keys for security
            if "API_KEY" in var:
                masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print_status(f"✓ {var}: {description} ({masked_value})", "SUCCESS")
            else:
                print_status(f"✓ {var}: {description} ({value})", "SUCCESS")
        else:
            print_status(f"✗ {var}: {description} - MISSING OR DEFAULT VALUE", "ERROR")
            all_good = False
    
    print("\n--- Optional Variables ---")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value and value.strip() and value != f"your_{var.lower()}_here":
            if "API_KEY" in var:
                masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print_status(f"✓ {var}: {description} ({masked_value})", "SUCCESS")
            else:
                print_status(f"✓ {var}: {description} ({value})", "SUCCESS")
        else:
            print_status(f"⚠ {var}: {description} - Not set (optional)", "WARNING")
    
    return all_good

def test_gemini_api():
    """Test Gemini API connectivity"""
    print_status("\nTesting Gemini API Connectivity...", "INFO")
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or api_key == 'your_gemini_api_key_here':
        print_status("Gemini API key not properly configured", "ERROR")
        return False
    
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-001:generateContent"
        headers = {'Content-Type': 'application/json'}
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": "Respond with a simple JSON: {\"status\": \"ok\", \"message\": \"API test successful\"}"
                }]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 100
            }
        }
        
        response = requests.post(
            f"{url}?key={api_key}",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'candidates' in data and len(data['candidates']) > 0:
                print_status("✓ Gemini API is working correctly", "SUCCESS")
                return True
            else:
                print_status("✗ Gemini API returned unexpected response format", "ERROR")
                return False
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error_msg = error_data.get('error', {}).get('message', response.text)
            print_status(f"✗ Gemini API error: {error_msg}", "ERROR")
            return False
            
    except requests.exceptions.Timeout:
        print_status("✗ Gemini API request timed out", "ERROR")
        return False
    except requests.exceptions.RequestException as e:
        print_status(f"✗ Network error calling Gemini API: {str(e)}", "ERROR")
        return False
    except Exception as e:
        print_status(f"✗ Unexpected error testing Gemini API: {str(e)}", "ERROR")
        return False

def test_firebase_config():
    """Test Firebase configuration"""
    print_status("\nTesting Firebase Configuration...", "INFO")
    
    storage_bucket = os.getenv('FIREBASE_STORAGE_BUCKET')
    if not storage_bucket or storage_bucket == 'your-project-id.appspot.com':
        print_status("Firebase storage bucket not properly configured", "WARNING")
        return False
    
    # Check for service account key file
    service_account_path = Path("backend/src/config/serviceAccountKey.json")
    if service_account_path.exists():
        try:
            with open(service_account_path, 'r') as f:
                service_account = json.load(f)
            
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in service_account]
            
            if not missing_fields:
                print_status("✓ Firebase service account key is properly configured", "SUCCESS")
                return True
            else:
                print_status(f"✗ Firebase service account key missing fields: {', '.join(missing_fields)}", "ERROR")
                return False
                
        except json.JSONDecodeError:
            print_status("✗ Firebase service account key is not valid JSON", "ERROR")
            return False
        except Exception as e:
            print_status(f"✗ Error reading Firebase service account key: {str(e)}", "ERROR")
            return False
    else:
        print_status("✗ Firebase service account key file not found", "ERROR")
        return False

def test_backend_connectivity():
    """Test if backend is running and accessible"""
    print_status("\nTesting Backend Connectivity...", "INFO")
    
    port = os.getenv('PORT', '5000')
    backend_url = f"http://localhost:{port}"
    
    try:
        # Test root endpoint
        response = requests.get(f"{backend_url}/", timeout=5)
        if response.status_code == 200:
            print_status(f"✓ Backend is running at {backend_url}", "SUCCESS")
            
            # Test health endpoint
            health_response = requests.get(f"{backend_url}/health", timeout=5)
            if health_response.status_code == 200:
                print_status("✓ Backend health check passed", "SUCCESS")
                return True
            else:
                print_status("⚠ Backend health check failed", "WARNING")
                return True
        else:
            print_status(f"✗ Backend returned status code: {response.status_code}", "ERROR")
            return False
            
    except requests.exceptions.ConnectionError:
        print_status(f"✗ Backend is not running at {backend_url}", "ERROR")
        return False
    except requests.exceptions.Timeout:
        print_status("✗ Backend request timed out", "ERROR")
        return False
    except Exception as e:
        print_status(f"✗ Error connecting to backend: {str(e)}", "ERROR")
        return False

def test_nodejs_backend():
    """Test Node.js backend configuration"""
    print_status("\nTesting Node.js Backend Configuration...", "INFO")
    
    # Check if Node.js backend files exist
    nodejs_files = [
        "backend/src/index.js",
        "backend/package.json",
        "backend/.env"
    ]
    
    missing_files = []
    for file_path in nodejs_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print_status(f"✗ Missing Node.js backend files: {', '.join(missing_files)}", "ERROR")
        return False
    else:
        print_status("✓ Node.js backend files are present", "SUCCESS")
        
        # Check if dotenv is configured in Node.js backend
        try:
            with open("backend/src/index.js", 'r') as f:
                content = f.read()
                if 'dotenv.config()' in content:
                    print_status("✓ Node.js backend loads environment variables", "SUCCESS")
                    return True
                else:
                    print_status("⚠ Node.js backend may not load environment variables", "WARNING")
                    return True
        except Exception as e:
            print_status(f"✗ Error checking Node.js backend: {str(e)}", "ERROR")
            return False

def main():
    """Main test function"""
    print("=" * 60)
    print("🔍 AI Career Advisor - API Connectivity Test")
    print("=" * 60)
    
    # Change to project directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    results = {
        "Environment Variables": test_environment_variables(),
        "Gemini API": test_gemini_api(),
        "Firebase Configuration": test_firebase_config(),
        "Node.js Backend": test_nodejs_backend(),
        "Backend Connectivity": test_backend_connectivity()
    }
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        color = "\033[92m" if result else "\033[91m"
        print(f"{color}{status}{'\033[0m'} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print_status("🎉 All tests passed! Your project is properly configured.", "SUCCESS")
        sys.exit(0)
    else:
        print_status(f"⚠️ {total - passed} test(s) failed. Please check the configuration.", "WARNING")
        sys.exit(1)

if __name__ == "__main__":
    main()
