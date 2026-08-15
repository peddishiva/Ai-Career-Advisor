"""
Test script to verify backend routes are registered correctly
"""

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / 'backend'))

from main import app

print("=" * 70)
print("  BACKEND ROUTES VERIFICATION")
print("=" * 70)
print()

paths = app.openapi().get('paths', {})

print("Registered routes:")
print("-" * 70)

for path, methods_dict in paths.items():
    methods = [m.upper() for m in methods_dict.keys()]
    print(f"  {', '.join(methods):12} {path}")

print()
print("=" * 70)
print("  VERIFICATION RESULTS")
print("=" * 70)
print()

expected_routes = {
    'health': '/health',
    'upload': '/api/upload',
    'analysis': '/api/analysis',
    'jobs': '/api/jobs/recommendations'
}

all_found = True
for name, expected_path in expected_routes.items():
    found = expected_path in paths
    if not found:
        all_found = False
    status = "✓" if found else "✗"
    print(f"  {status} {name.upper()} endpoint ({expected_path}): {'Found' if found else 'NOT FOUND'}")

print()

if all_found:
    print("✓ All required API routes are registered and verified!")
else:
    print("✗ Some routes are missing!")

print()
print("=" * 70)
