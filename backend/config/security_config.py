"""Deployment-safe security settings with conservative local defaults."""

import os
from urllib.parse import urlparse


DEFAULT_CORS_ORIGINS = ("http://localhost:3000",)
MAX_FILENAME_LENGTH = 180
JDXR_SESSION_RETENTION_SECONDS = 7 * 24 * 60 * 60
JDXR_TEMP_FILE_RETENTION_SECONDS = 24 * 60 * 60
JDXR_TEMP_FILE_SUFFIXES = frozenset({".part", ".partial", ".tmp", ".upload"})


def load_cors_origins() -> list[str]:
    """Load an explicit allowlist; never combine credentials with wildcard CORS."""
    raw_value = os.getenv("CORS_ALLOWED_ORIGINS", ",".join(DEFAULT_CORS_ORIGINS))
    origins = []
    for raw_origin in raw_value.split(","):
        origin = raw_origin.strip().rstrip("/")
        parsed = urlparse(origin)
        if parsed.scheme in {"http", "https"} and parsed.netloc and origin not in origins:
            origins.append(origin)
    return origins or list(DEFAULT_CORS_ORIGINS)
