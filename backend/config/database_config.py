"""Database configuration with a local SQLite fallback for development."""

from dataclasses import dataclass
import os


DEFAULT_LOCAL_DATABASE_URL = "sqlite:///./uploads/phase4a.db"


@dataclass(frozen=True)
class DatabaseConfig:
    url: str = DEFAULT_LOCAL_DATABASE_URL
    echo: bool = False


def load_database_config() -> DatabaseConfig:
    url = os.getenv("DATABASE_URL", DEFAULT_LOCAL_DATABASE_URL).strip() or DEFAULT_LOCAL_DATABASE_URL
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return DatabaseConfig(
        url=url,
        echo=os.getenv("DATABASE_ECHO", "false").strip().lower() in {"1", "true", "yes"},
    )
