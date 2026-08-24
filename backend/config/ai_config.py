"""Centralized configuration for the optional AI enrichment boundary."""

import os
from dataclasses import dataclass
from typing import Dict, Tuple


AI_ENABLED = False
SUPPORTED_FLOW_TYPES: Tuple[str, ...] = ("resume_analysis", "jdxr")

PROMPT_VERSION = "phase3d.prompt.v1"
AI_SCHEMA_VERSION = "phase3d.v1"

REDACT_PII_BY_DEFAULT = True
REDACT_CANDIDATE_NAME_BY_DEFAULT = True
REDACTED_CANDIDATE_LABEL = "Candidate"

MAX_CONTEXT_CHARS = 20_000
MAX_OUTPUT_CHARS = 12_000
PROVIDER_TIMEOUT_SECONDS = 10.0
MAX_PROVIDER_RETRIES = 0
AI_PROVIDER_NAME = "gemini"
AI_MODEL_NAME = "gemini-2.0-flash-001"
AI_API_KEY_ENV_VAR = "GEMINI_API_KEY"
AI_MAX_OUTPUT_TOKENS = 1_500
AI_TEMPERATURE = 0.2
AI_PROVIDER_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
AI_MAX_RETRIEVAL_RESULTS = 5

# Cache behavior is intentionally declarative only. No cache is implemented
# until a later phase defines ownership, TTL, and invalidation rules.
CACHE_POLICY: Dict[str, object] = {
    "enabled": False,
    "scope_required": True,
    "ttl_seconds": None,
}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    try:
        return max(int(os.getenv(name, str(default))), minimum)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    try:
        return max(float(os.getenv(name, str(default))), minimum)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class AIProviderConfig:
    """Runtime provider settings loaded without ever exposing secret values."""

    enabled: bool = AI_ENABLED
    provider_name: str = AI_PROVIDER_NAME
    model_name: str = AI_MODEL_NAME
    timeout_seconds: float = PROVIDER_TIMEOUT_SECONDS
    max_output_tokens: int = AI_MAX_OUTPUT_TOKENS
    retry_limit: int = MAX_PROVIDER_RETRIES
    temperature: float = AI_TEMPERATURE
    api_key_env_var: str = AI_API_KEY_ENV_VAR
    provider_url: str = AI_PROVIDER_URL


def load_ai_config() -> AIProviderConfig:
    """Load optional AI settings from environment variables at runtime."""

    provider_name = os.getenv("AI_PROVIDER", AI_PROVIDER_NAME).strip().casefold() or AI_PROVIDER_NAME
    model_name = os.getenv("AI_MODEL", AI_MODEL_NAME).strip() or AI_MODEL_NAME
    api_key_env_var = os.getenv("AI_API_KEY_ENV_VAR", AI_API_KEY_ENV_VAR).strip() or AI_API_KEY_ENV_VAR
    provider_url = os.getenv("AI_PROVIDER_URL", AI_PROVIDER_URL).strip() or AI_PROVIDER_URL
    return AIProviderConfig(
        enabled=_env_bool("AI_ENABLED", AI_ENABLED),
        provider_name=provider_name,
        model_name=model_name,
        timeout_seconds=_env_float("AI_PROVIDER_TIMEOUT_SECONDS", PROVIDER_TIMEOUT_SECONDS, 0.1),
        max_output_tokens=_env_int("AI_MAX_OUTPUT_TOKENS", AI_MAX_OUTPUT_TOKENS, 1),
        retry_limit=_env_int("AI_MAX_RETRIES", MAX_PROVIDER_RETRIES, 0),
        temperature=_env_float("AI_TEMPERATURE", AI_TEMPERATURE, 0.0),
        api_key_env_var=api_key_env_var,
        provider_url=provider_url,
    )
