"""Operational worker for processing pending and failed storage cleanup jobs.

Usage:
    python -m workers.storage_cleanup_worker [--limit N] [--user-id UUID] [--dry-run] [--json]

This worker reads durably staged StorageCleanupJob records from the database
and executes their deferred object deletion against the configured storage service.

Guarantees:
- Tenant isolation: Jobs are always processed scoped to the user_id recorded at job creation.
- Error sanitization: No credentials, tokens, or signed URLs leaked into logs or error fields.
- Idempotency: Re-running against already deleted objects succeeds safely without raising errors.
- No arbitrary path deletion: Object names and paths are strictly read from verified DB rows.
- Concurrency & crash recovery: In-progress/failed jobs can be safely retried.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any
import uuid

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from sqlalchemy.orm import Session

from db.repositories import ResumeRepository
from db.session import SessionLocal
from services.storage_service import StorageService, build_storage_service

logger = logging.getLogger("storage_cleanup_worker")


def validate_user_id(user_id: str | None) -> str | None:
    """Validate that the optional user_id is a valid UUID."""
    if user_id is None:
        return None
    user_id_clean = user_id.strip()
    if not user_id_clean:
        return None
    try:
        uuid.UUID(user_id_clean)
        return user_id_clean
    except ValueError as exc:
        raise ValueError(f"Invalid user_id format (must be a valid UUID): {user_id}") from exc


def run_storage_cleanup_worker(
    *,
    user_id: str | None = None,
    limit: int = 50,
    dry_run: bool = False,
    session: Session | None = None,
    storage_service: StorageService | None = None,
    repository: ResumeRepository | None = None,
) -> dict[str, Any]:
    """Execute or simulate storage cleanup queue processing.

    Returns a dictionary summarizing execution counts and statuses.
    """
    validated_user_id = validate_user_id(user_id)
    repo = repository or ResumeRepository()

    owns_session = session is None
    db: Session = session or SessionLocal()

    try:
        initial_counts = repo.get_cleanup_job_counts(db, user_id=validated_user_id)

        if dry_run:
            pending_jobs = repo.get_pending_storage_cleanups(db, user_id=validated_user_id, limit=limit)
            return {
                "dry_run": True,
                "user_id_scope": validated_user_id,
                "limit": limit,
                "counts": initial_counts,
                "queued_for_processing": len(pending_jobs),
                "processed": 0,
                "succeeded": 0,
                "failed": 0,
            }

        svc = storage_service or build_storage_service()
        results = repo.retry_pending_storage_cleanups(
            db,
            svc,
            user_id=validated_user_id,
            limit=limit,
        )

        final_counts = repo.get_cleanup_job_counts(db, user_id=validated_user_id)

        return {
            "dry_run": False,
            "user_id_scope": validated_user_id,
            "limit": limit,
            "counts": final_counts,
            "processed": results["processed"],
            "succeeded": results["succeeded"],
            "failed": results["failed"],
        }
    finally:
        if owns_session:
            db.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process pending and failed storage cleanup jobs.",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        help="Optional UUID to restrict cleanup execution to a single user's jobs.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of cleanup jobs to process in this run (default: 50).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect and report pending jobs without deleting storage objects.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for running storage cleanup."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    args = parse_args(argv)

    try:
        report = run_storage_cleanup_worker(
            user_id=args.user_id,
            limit=args.limit,
            dry_run=args.dry_run,
        )
    except ValueError as val_err:
        if args.json:
            print(json.dumps({"error": str(val_err), "status": "failed"}))
        else:
            print(f"Error: {val_err}", file=sys.stderr)
        return 1
    except Exception as exc:
        if args.json:
            print(json.dumps({"error": "Worker execution failed", "status": "failed"}))
        else:
            print(f"Error: Worker execution failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Storage Cleanup Worker Summary (dry_run={report['dry_run']}):")
        print(f"  User Scope: {report['user_id_scope'] or 'All Users'}")
        print(f"  Jobs Processed: {report['processed']}")
        print(f"  Succeeded:      {report['succeeded']}")
        print(f"  Failed:         {report['failed']}")
        print("  Current Job Counts:")
        for status, count in report["counts"].items():
            print(f"    {status:12s}: {count}")

    # Return exit code 1 if any job failed
    if report.get("failed", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
