"""Configuration for the Phase 3A AI boundary.

Phase 3A deliberately keeps AI disabled and does not define provider secrets.
Later phases may replace these defaults without changing the deterministic
resume or JDxR services.
"""

from typing import Dict, Tuple


AI_ENABLED = False
SUPPORTED_FLOW_TYPES: Tuple[str, ...] = ("resume_analysis", "jdxr")

PROMPT_VERSION = "phase3a.prompt.v1"
AI_SCHEMA_VERSION = "phase3a.v1"

REDACT_PII_BY_DEFAULT = True
REDACT_CANDIDATE_NAME_BY_DEFAULT = True
REDACTED_CANDIDATE_LABEL = "Candidate"

MAX_CONTEXT_CHARS = 20_000
MAX_OUTPUT_CHARS = 12_000
PROVIDER_TIMEOUT_SECONDS = 10.0
MAX_PROVIDER_RETRIES = 0

# Cache behavior is intentionally declarative only. No cache is implemented
# until a later phase defines ownership, TTL, and invalidation rules.
CACHE_POLICY: Dict[str, object] = {
    "enabled": False,
    "scope_required": True,
    "ttl_seconds": None,
}

