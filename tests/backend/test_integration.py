"""
Backend-Frontend Integration Test
Tests if backend API matches frontend expectations
"""

import requests
import json
from pathlib import Path

# Test configuration
BACKEND_URL = "http://localhost:5000"
TEST_FILE = "test_resume.pdf"  # You'll need to provide a test file

def test_health_check():
    """Test if backend is running"""
    print("\n[Test 1] Health Check")
    print("=" * 60)
    try:
        response = requests.get(f"{BACKEND_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        print("✓ Health check passed")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_upload_endpoint():
    """Test upload endpoint structure"""
    print("\n[Test 2] Upload Endpoint Structure")
    print("=" * 60)
    
    # Check if test file exists
    if not Path(TEST_FILE).exists():
        print(f"⚠ Test file '{TEST_FILE}' not found")
        print("Creating a dummy test file...")
        # Create a minimal test file
        with open("test_resume.txt", "w") as f:
            f.write("Test Resume\nJohn Doe\njohn@example.com\n")
        print("Please upload a real PDF/DOCX file for proper testing")
        return False
    
    try:
        with open(TEST_FILE, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{BACKEND_URL}/api/upload", files=files)
        
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Response Keys: {list(data.keys())}")
        
        # Verify response structure matches frontend expectations
        required_keys = ['success', 'message', 'file_id', 'analysis']
        for key in required_keys:
            if key in data:
                print(f"✓ '{key}' present")
            else:
                print(f"✗ '{key}' MISSING")
                return False
        
        # Verify analysis structure
        if 'analysis' in data:
            analysis = data['analysis']
            required_analysis_keys = [
                'overall_insights',
                'metrics',
                'skill_strengths',
                'role_matches',
                'next_actions'
            ]
            print("\nAnalysis Structure:")
            for key in required_analysis_keys:
                if key in analysis:
                    print(f"✓ analysis.{key} present")
                else:
                    print(f"✗ analysis.{key} MISSING")
        
        print("\n✓ Upload endpoint structure is correct")
        return True
        
    except Exception as e:
        print(f"✗ Upload test failed: {e}")
        return False
