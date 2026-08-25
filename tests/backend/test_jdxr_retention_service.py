"""Regression tests for deterministic JDxR retention cleanup."""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
import sys
sys.path.insert(0, str(backend_path))

from services.jdxr_retention_service import cleanup_jdxr_storage


class TestJdxrRetentionService(unittest.TestCase):
    NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "uploads" / "jdxr"
        self.root.mkdir(parents=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _session(self, session_id: str, *, updated_at: datetime) -> Path:
        directory = self.root / session_id
        (directory / "jd").mkdir(parents=True)
        (directory / "resume").mkdir()
        (directory / "session.json").write_text(
            json.dumps({
                "session_id": session_id,
                "created_at": updated_at.isoformat(),
                "updated_at": updated_at.isoformat(),
                "status": "ready",
            }),
            encoding="utf-8",
        )
        return directory

    def test_expired_session_is_removed(self):
        expired = self._session("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", updated_at=self.NOW - timedelta(days=8))
        result = cleanup_jdxr_storage(self.root, now=self.NOW)
        self.assertFalse(expired.exists())
        self.assertEqual(1, result["expired_sessions"])

    def test_active_and_unrelated_sessions_are_preserved(self):
        active = self._session("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", updated_at=self.NOW - timedelta(days=1))
        explicitly_active = self._session("cccccccc-cccc-cccc-cccc-cccccccccccc", updated_at=self.NOW - timedelta(days=30))
        unrelated = self.root / "not-a-session"
        unrelated.mkdir()
        (unrelated / "keep.txt").write_text("keep", encoding="utf-8")

        cleanup_jdxr_storage(self.root, now=self.NOW, active_session_ids=[explicitly_active.name])

        self.assertTrue(active.exists())
        self.assertTrue(explicitly_active.exists())
        self.assertTrue(unrelated.exists())

    def test_stale_orphan_temp_file_is_removed_but_resume_analysis_storage_is_untouched(self):
        session = self._session("dddddddd-dddd-dddd-dddd-dddddddddddd", updated_at=self.NOW - timedelta(days=1))
        orphan = session / "resume" / "abandoned.part"
        orphan.write_text("partial", encoding="utf-8")
        old_timestamp = (self.NOW - timedelta(days=2)).timestamp()
        os.utime(orphan, (old_timestamp, old_timestamp))

        resume_analysis = Path(self.temp_dir.name) / "uploads" / "analysis"
        resume_analysis.mkdir(parents=True)
        protected = resume_analysis / "resume.json"
        protected.write_text("protected", encoding="utf-8")

        result = cleanup_jdxr_storage(self.root, now=self.NOW)

        self.assertFalse(orphan.exists())
        self.assertTrue(protected.exists())
        self.assertEqual(1, result["orphan_temp_files"])

    def test_path_safety_preserves_symlink_and_traversal_named_entries(self):
        outside = Path(self.temp_dir.name) / "outside"
        outside.mkdir()
        protected = outside / "protected.txt"
        protected.write_text("protected", encoding="utf-8")
        link = self.root / "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable")

        cleanup_jdxr_storage(self.root, now=self.NOW)

        self.assertTrue(link.is_symlink())
        self.assertTrue(protected.exists())

    def test_malformed_session_metadata_is_preserved(self):
        malformed = self.root / "ffffffff-ffff-ffff-ffff-ffffffffffff"
        malformed.mkdir()
        (malformed / "session.json").write_text("not-json", encoding="utf-8")

        result = cleanup_jdxr_storage(self.root, now=self.NOW)

        self.assertTrue(malformed.exists())
        self.assertEqual(1, result["skipped_entries"])


if __name__ == "__main__":
    unittest.main()
