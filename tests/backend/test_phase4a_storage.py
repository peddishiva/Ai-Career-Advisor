"""Phase 4A private storage adapter tests."""

from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from config.storage_config import StorageConfig  # noqa: E402
from services.storage_service import InvalidStoragePath, LocalStorageAdapter, StorageError  # noqa: E402


class TestPhase4AStorage(unittest.TestCase):
    def test_local_adapter_is_owner_scoped_and_signed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = LocalStorageAdapter(StorageConfig(local_root=Path(temp_dir), max_object_bytes=32), signing_key=b"test-signing-key-0123456789012345")
            metadata = adapter.upload("user-one", "resume.pdf", BytesIO(b"resume evidence"), "application/pdf")
            self.assertTrue(adapter.exists("user-one", "resume.pdf"))
            self.assertFalse(adapter.exists("user-two", "resume.pdf"))
            self.assertTrue(metadata.storage_path.startswith("users/user-one/"))
            self.assertIn("signature=", adapter.download_signed("user-one", "resume.pdf"))
            self.assertEqual("application/pdf", adapter.metadata("user-one", "resume.pdf").content_type)
            adapter.delete("user-one", "resume.pdf")
            self.assertFalse(adapter.exists("user-one", "resume.pdf"))

    def test_local_adapter_rejects_traversal_and_large_objects(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = LocalStorageAdapter(StorageConfig(local_root=Path(temp_dir), max_object_bytes=4), signing_key=b"test-signing-key-0123456789012345")
            with self.assertRaises(InvalidStoragePath):
                adapter.upload("user-one", "../secret.txt", b"safe")
            with self.assertRaises(InvalidStoragePath):
                adapter.upload("../user-one", "resume.pdf", b"safe")
            with self.assertRaises(StorageError):
                adapter.upload("user-one", "resume.pdf", b"too large")
            with self.assertRaises(StorageError):
                adapter.download_signed("user-one", "missing.pdf")


if __name__ == "__main__":
    unittest.main()
