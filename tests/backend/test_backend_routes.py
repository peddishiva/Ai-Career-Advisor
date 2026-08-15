"""
Test script to verify backend routes are registered correctly
"""

import sys
from pathlib import Path
import unittest

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / 'backend'))

from main import app


class TestBackendRoutes(unittest.TestCase):
    """Test verification of registered backend routes."""

    def test_required_routes_registered(self):
        paths = app.openapi().get('paths', {})
        expected_routes = {
            'health': '/health',
            'upload': '/api/upload',
            'analysis': '/api/analysis',
            'jobs': '/api/jobs/recommendations'
        }
        for name, expected_path in expected_routes.items():
            self.assertIn(expected_path, paths, f"Route '{name}' at {expected_path} is not registered")


if __name__ == '__main__':
    unittest.main()
