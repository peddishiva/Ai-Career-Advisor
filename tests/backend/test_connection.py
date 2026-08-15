"""
Test connectivity between frontend and backend
"""
import sys
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def test_backend_health():
    """Test backend health endpoint"""
    try:
        response = requests.get('http://localhost:5000/health')
        print(f"Backend Health Check: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Backend Health Check Failed: {e}")
        return False

def test_backend_root():
    """Test backend root endpoint"""
    try:
        response = requests.get('http://localhost:5000/')
        print(f"Backend Root: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Backend Root Failed: {e}")
        return False

def test_cors_headers():
    """Test CORS headers"""
    try:
        response = requests.get(
            'http://localhost:5000/health',
            headers={'Origin': 'http://localhost:3000'}
        )
        cors_header = response.headers.get('Access-Control-Allow-Origin')
        print(f"CORS Header: {cors_header}")
        
        if cors_header and ('localhost' in cors_header or cors_header == '*'):
            print("   CORS configured correctly")
            return True
        else:
            print(f"   CORS warning: {cors_header}")
            return False
    except Exception as e:
        print(f"CORS Test Failed: {e}")
        return False

def test_frontend():
    """Test frontend server"""
    for port in [3000, 3001, 3002]:
        try:
            response = requests.get(f'http://localhost:{port}', timeout=3)
            print(f"Frontend Server (port {port}): {response.status_code}")
            if response.status_code == 200:
                return True
        except Exception:
            pass
    print("Frontend Server Failed on tested ports")
    return False

def main():
    print("=" * 60)
    print("  CONNECTIVITY TEST - Frontend <-> Backend")
    print("=" * 60)
    print()
    
    print("Testing Backend...")
    print("-" * 60)
    backend_health = test_backend_health()
    print()
    backend_root = test_backend_root()
    print()
    
    print("Testing CORS Configuration...")
    print("-" * 60)
    cors_ok = test_cors_headers()
    print()
    
    print("Testing Frontend...")
    print("-" * 60)
    frontend_ok = test_frontend()
    print()
    
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"Backend Health:     {'PASS' if backend_health else 'FAIL'}")
    print(f"Backend Root:       {'PASS' if backend_root else 'FAIL'}")
    print(f"CORS Configuration: {'PASS' if cors_ok else 'WARNING'}")
    print(f"Frontend Server:    {'PASS' if frontend_ok else 'FAIL'}")
    print()
    
    if all([backend_health, backend_root, frontend_ok]):
        print("All tests passed! Frontend and Backend are connected!")
    else:
        print("Some tests failed. Check the output above.")
    print("=" * 60)

if __name__ == "__main__":
    main()
