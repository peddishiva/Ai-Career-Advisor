"""Short-lived SQLAlchemy session lifecycle helpers."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.database_config import load_database_config


_database_config = load_database_config()
if _database_config.url.startswith("sqlite"):
    Path("uploads").mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        _database_config.url,
        echo=_database_config.echo,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        _database_config.url,
        echo=_database_config.echo,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield one request-scoped session and close it on every path."""

    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Commit a short unit of work or roll it back safely."""

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
