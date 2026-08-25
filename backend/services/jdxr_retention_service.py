"""Deterministic cleanup for filesystem-backed JDxR sessions."""

import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

from config.security_config import (
    JDXR_SESSION_RETENTION_SECONDS,
    JDXR_TEMP_FILE_RETENTION_SECONDS,
    JDXR_TEMP_FILE_SUFFIXES,
)


SESSION_ID_PATTERN = re.compile(r"^[a-fA-F0-9-]{36}$")


def cleanup_jdxr_storage(
    root_dir: Path | str,
    *,
    now: Optional[datetime] = None,
    retention_seconds: int = JDXR_SESSION_RETENTION_SECONDS,
    temp_retention_seconds: int = JDXR_TEMP_FILE_RETENTION_SECONDS,
    active_session_ids: Iterable[str] = (),
) -> dict[str, int]:
    """Remove only expired JDxR sessions and stale known temporary files.

    Unknown paths, malformed session metadata, symlinks, and explicitly active
    sessions are preserved so cleanup fails closed around unrelated storage.
    """
    requested_root = Path(root_dir)
    if requested_root.is_symlink():
        return {"expired_sessions": 0, "orphan_temp_files": 0, "skipped_entries": 1}
    root = requested_root.resolve()
    if not root.exists() or not root.is_dir():
        return {"expired_sessions": 0, "orphan_temp_files": 0, "skipped_entries": 0}

    current_time = _as_utc(now or datetime.now(timezone.utc))
    session_cutoff = current_time - timedelta(seconds=max(0, retention_seconds))
    temp_cutoff = current_time - timedelta(seconds=max(0, temp_retention_seconds))
    active_ids = {str(session_id) for session_id in active_session_ids if SESSION_ID_PATTERN.fullmatch(str(session_id))}
    result = {"expired_sessions": 0, "orphan_temp_files": 0, "skipped_entries": 0}

    for entry in root.iterdir():
        if entry.is_symlink():
            result["skipped_entries"] += 1
            continue
        if entry.is_file():
            if _is_stale_temp_file(entry, temp_cutoff) and _safe_child(root, entry):
                entry.unlink()
                result["orphan_temp_files"] += 1
            continue
        if not entry.is_dir() or not SESSION_ID_PATTERN.fullmatch(entry.name):
            result["skipped_entries"] += 1
            continue
        if entry.name in active_ids:
            result["skipped_entries"] += 1
            continue

        state = _read_state(entry / "session.json")
        updated_at = _state_timestamp(state)
        if updated_at is None:
            result["skipped_entries"] += 1
            continue
        if updated_at <= session_cutoff:
            if _safe_child(root, entry):
                shutil.rmtree(entry)
                result["expired_sessions"] += 1
            continue

        result["orphan_temp_files"] += _cleanup_session_temp_files(entry, temp_cutoff)

    return result


def _cleanup_session_temp_files(session_dir: Path, cutoff: datetime) -> int:
    removed = 0
    for section in ("jd", "resume"):
        directory = session_dir / section
        if not directory.is_dir() or directory.is_symlink():
            continue
        for path in directory.iterdir():
            if _is_stale_temp_file(path, cutoff) and _safe_child(directory, path):
                path.unlink()
                removed += 1
    return removed


def _is_stale_temp_file(path: Path, cutoff: datetime) -> bool:
    if not path.is_file() or path.is_symlink() or path.suffix.casefold() not in JDXR_TEMP_FILE_SUFFIXES:
        return False
    try:
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    except OSError:
        return False
    return modified_at <= cutoff


def _read_state(path: Path) -> Optional[dict]:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _state_timestamp(state: Optional[dict]) -> Optional[datetime]:
    if not state:
        return None
    for key in ("updated_at", "created_at"):
        value = state.get(key)
        if not isinstance(value, str):
            continue
        try:
            return _as_utc(datetime.fromisoformat(value))
        except ValueError:
            continue
    return None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _safe_child(parent: Path, child: Path) -> bool:
    try:
        parent_resolved = parent.resolve()
        child_resolved = child.resolve()
    except OSError:
        return False
    return child_resolved.parent == parent_resolved
