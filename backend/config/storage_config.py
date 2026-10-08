"""Provider-neutral private storage configuration."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class StorageConfig:
    provider: str = "local"
    local_root: Path = Path("uploads/private")
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_bucket: str = "career-private"
    max_object_bytes: int = 5 * 1024 * 1024


def load_storage_config() -> StorageConfig:
    return StorageConfig(
        provider=os.getenv("STORAGE_PROVIDER", "local").strip().lower() or "local",
        local_root=Path(os.getenv("LOCAL_STORAGE_ROOT", "uploads/private").strip() or "uploads/private"),
        supabase_url=os.getenv("SUPABASE_URL", "").strip().rstrip("/"),
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
        supabase_bucket=os.getenv("SUPABASE_STORAGE_BUCKET", "career-private").strip() or "career-private",
        max_object_bytes=max(1, int(os.getenv("STORAGE_MAX_OBJECT_BYTES", str(5 * 1024 * 1024)))),
    )
