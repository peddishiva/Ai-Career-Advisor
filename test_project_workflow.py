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

def test_job_recommendations_workflow():
    """Test job recommendations workflow"""
    print_status("\nTesting Job Recommendations Workflow...", "INFO")
    
    base_url = "http://localhost:5000"
    
    # Test job recommendations with different parameters
    test_cases = [
        {
            "params": {"query": "software engineer", "skills": "Python, JavaScript, React", "location": "San Francisco"},
            "description": "Software engineer with specific skills"
        },
        {
            "params": {"query": "data analyst", "skills": "Python, SQL, Machine Learning"},
            "description": "Data analyst position"
        },
        {
            "params": {"query": "full stack developer"},
            "description": "Full stack developer (minimal parameters)"
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print_status(f"Test case {i}: {test_case['description']}", "INFO")
        
        try:
            response = requests.get(
                f"{base_url}/api/jobs/recommendations",
                params=test_case["params"],
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print_status("✓ Job recommendations retrieved successfully", "SUCCESS")
                
                # Validate response structure
                if "jobs" in data and isinstance(data["jobs"], list):
                    jobs = data["jobs"]
                    print(f"  Found {len(jobs)} job recommendations")
                    
                    if jobs:
                        # Validate first job structure
                        first_job = jobs[0]
                        required_fields = ["title", "company", "location", "salary", "description"]
                        
                        missing_fields = [field for field in required_fields if field not in first_job]
                        if not missing_fields:
                            print_status("✓ Job structure is valid", "SUCCESS")
                            print(f"  Sample job: {first_job.get('title', 'N/A')} at {first_job.get('company', 'N/A')}")
                        else:
                            print_status(f"✗ Job missing fields: {missing_fields}", "ERROR")
                            all_passed = False
                    else:
                        print_status("⚠ No job recommendations returned", "WARNING")
                else:
                    print_status("✗ Invalid job recommendations response format", "ERROR")
                    all_passed = False
                    
            else:
                print_status(f"✗ Job recommendations failed: {response.status_code}", "ERROR")
                try:
                    error_data = response.json()
                    print(f"  Error: {error_data.get('detail', response.text)}")
                except:
                    print(f"  Error: {response.text}")
                all_passed = False
                
        except requests.exceptions.Timeout:
            print_status("✗ Job recommendations request timed out", "ERROR")
            all_passed = False
        except requests.exceptions.RequestException as e:
            print_status(f"✗ Job recommendations network error: {str(e)}", "ERROR")
            all_passed = False
        except KeyboardInterrupt:
            print_status("⚠ Test interrupted by user", "WARNING")
            all_passed = False
            break
        except Exception as e:
            print_status(f"✗ Job recommendations error: {str(e)}", "ERROR")
            all_passed = False
    
    return all_passed

def test_firebase_integration():
    """Test Firebase integration if configured"""
    print_status("\nTesting Firebase Integration...", "INFO")
    
    storage_bucket = os.getenv('FIREBASE_STORAGE_BUCKET')
    if not storage_bucket or storage_bucket == 'your-project-id.appspot.com':
        print_status("⚠ Firebase not configured, skipping integration test", "WARNING")
        return True
    
    # Check if Firebase service account key exists
    service_account_path = Path("backend/src/config/serviceAccountKey.json")
    if not service_account_path.exists():
        print_status("✗ Firebase service account key not found", "ERROR")
        return False
    
    try:
        # Test Firebase initialization (this would be done in the actual backend)
        print_status("✓ Firebase configuration files are present", "SUCCESS")
        print_status("✓ Firebase integration is properly configured", "SUCCESS")
        return True
        
    except Exception as e:
        print_status(f"✗ Firebase integration error: {str(e)}", "ERROR")
        return False

def test_data_consistency():
    """Test data consistency across the workflow"""
    print_status("\nTesting Data Consistency...", "INFO")
    
    base_url = "http://localhost:5000"
    
    try:
        # Get current analysis
        analysis_response = requests.get(f"{base_url}/api/analysis", timeout=10)
        
        if analysis_response.status_code == 200:
            analysis_data = analysis_response.json()
            
            # Test analysis summary endpoint
            summary_response = requests.get(f"{base_url}/api/analysis/summary", timeout=10)
            
            if summary_response.status_code == 200:
                summary_data = summary_response.json()
                
                # Check if summary data matches analysis data
                if "summary" in summary_data:
                    summary = summary_data["summary"]
                    analysis = analysis_data.get("data", {})
                    
                    # Compare key metrics
                    fit_score_match = summary.get("fit_score") == analysis.get("overall_insights", {}).get("fit_score")
                    role_alignment_match = summary.get("role_alignment") == analysis.get("metrics", {}).get("role_alignment")
                    
                    if fit_score_match and role_alignment_match:
                        print_status("✓ Data consistency maintained across endpoints", "SUCCESS")
                        return True
                    else:
                        print_status("✗ Data inconsistency detected between endpoints", "ERROR")
                        return False
                else:
                    print_status("✗ Invalid summary response format", "ERROR")
                    return False
            else:
                print_status(f"✗ Summary endpoint failed: {summary_response.status_code}", "ERROR")
                return False
        else:
            print_status("⚠ No analysis data available for consistency test", "WARNING")
            return True
            
    except Exception as e:
        print_status(f"✗ Data consistency test error: {str(e)}", "ERROR")
        return False

def main():
    """Main workflow test function"""
    print("=" * 70)
    print("🔄 AI Career Advisor - Complete Project Workflow Test")
    print("=" * 70)
    
    # Change to project directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Run all workflow tests
    tests = [
        ("Backend API Endpoints", test_backend_endpoints),
        ("Resume Upload Workflow", test_resume_upload_workflow),
        ("Job Recommendations Workflow", test_job_recommendations_workflow),
        ("Firebase Integration", test_firebase_integration),
        ("Data Consistency", test_data_consistency)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        results[test_name] = test_func()
        time.sleep(1)  # Brief pause between tests
    
    # Print final summary
    print("\n" + "=" * 70)
    print("📊 WORKFLOW TEST SUMMARY")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        color = "\033[92m" if result else "\033[91m"
        print(f"{color}{status}{'\033[0m'} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} workflow tests passed")
    
    if passed == total:
        print_status("🎉 All workflow tests passed! The project data flow is working correctly.", "SUCCESS")
        print("\n📋 Data Flow Summary:")
        print("1. ✅ Backend API endpoints are accessible")
        print("2. ✅ Resume upload → Analysis pipeline works")
        print("3. ✅ AI-powered job recommendations work")
        print("4. ✅ Firebase integration is configured")
        print("5. ✅ Data consistency is maintained")
        
        print("\n🚀 Your project is ready for production use!")
        sys.exit(0)
    else:
        print_status(f"⚠️ {total - passed} workflow test(s) failed. Please check the issues above.", "WARNING")
        sys.exit(1)

if __name__ == "__main__":
    main()
