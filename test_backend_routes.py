"""
Test script to verify backend routes are registered correctly
"""

import sys
sys.path.insert(0, 'backend')

from main import app

print("=" * 70)
print("  BACKEND ROUTES VERIFICATION")
print("=" * 70)
print()

print("Registered routes:")
print("-" * 70)

routes_found = {
    'health': False,
    'upload': False,
    'jobs': False
}

for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        path = route.path
        methods = list(route.methods) if route.methods else []
        
        print(f"  {', '.join(methods):8} {path}")
        
        # Check for specific routes
        if '/health' in path:
            routes_found['health'] = True
        if '/api/upload' in path:
            routes_found['upload'] = True
        if '/api/jobs' in path:
            routes_found['jobs'] = True

print()
print("=" * 70)
print("  VERIFICATION RESULTS")
print("=" * 70)
print()

for route_name, found in routes_found.items():
    status = "✓" if found else "✗"
    print(f"  {status} {route_name.upper()} endpoint: {'Found' if found else 'NOT FOUND'}")

print()

if all(routes_found.values()):
    print("✓ All required routes are registered!")
    print()
    print("The backend should work correctly.")
    print("If you're getting 404 errors:")
    print("  1. Make sure backend is running: python backend/main.py")
    print("  2. Restart the backend server")
    print("  3. Check the URL: http://localhost:5000/api/jobs/recommendations")
else:
    print("✗ Some routes are missing!")
    print()
    print("Please check:")
    print("  1. backend/routes/jobs.py exists")
    print("  2. backend/main.py imports jobs router")
    print("  3. No import errors in jobs.py")

print()
print("=" * 70)
