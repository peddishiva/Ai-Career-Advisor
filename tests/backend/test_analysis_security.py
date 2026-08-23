"""Security regressions for analysis file access."""

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from routes import analysis as analysis_route


class TestAnalysisSecurity(unittest.TestCase):
    def test_analysis_read_and_delete_reject_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            analysis_dir = root / "analysis"
            analysis_dir.mkdir()
            secret_path = root / "secret.json"
            secret_path.write_text(json.dumps({"private": "sentinel"}), encoding="utf-8")

            previous_dir = analysis_route.ANALYSIS_DIR
            analysis_route.ANALYSIS_DIR = analysis_dir
            try:
                with self.assertRaises(HTTPException) as read_error:
                    asyncio.run(analysis_route.get_analysis("../secret"))
                with self.assertRaises(HTTPException) as delete_error:
                    asyncio.run(analysis_route.delete_analysis("../secret"))

                self.assertEqual(404, read_error.exception.status_code)
                self.assertEqual(404, delete_error.exception.status_code)
                self.assertTrue(secret_path.exists())
            finally:
                analysis_route.ANALYSIS_DIR = previous_dir


if __name__ == "__main__":
    unittest.main()
