"""Provider abstraction and the intentionally offline Phase 3A provider."""

from typing import Protocol, runtime_checkable

from .contracts import AIRequest, AIResponse, AIResponseStatus


class AIProviderError(RuntimeError):
    code = "provider_error"
    retryable = False


class AIProviderUnavailable(AIProviderError):
    code = "provider_unavailable"


class AIProviderTimeout(AIProviderError):
    code = "provider_timeout"
    retryable = True


class AIProviderRateLimited(AIProviderError):
    code = "provider_rate_limited"
    retryable = True


class AIProviderInvalidResponse(AIProviderError):
    code = "provider_invalid_response"


class AIProviderConfigurationError(AIProviderError):
    code = "provider_configuration_error"


@runtime_checkable
class AIProvider(Protocol):
    def generate(self, request: AIRequest) -> AIResponse:
        """Generate a structured response without leaking provider exceptions."""

    def provider_name(self) -> str:
        """Return a stable provider identifier."""

    def model_name(self) -> str:
        """Return a stable model identifier."""


class NullAIProvider:
    """Offline provider used until a later phase explicitly enables AI."""

    def provider_name(self) -> str:
        return "null"

    def model_name(self) -> str:
        return "disabled"

    def generate(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            status=AIResponseStatus.UNAVAILABLE,
            summary="AI enrichment is not enabled.",
            confidence_notes=["Phase 3A uses an offline null provider."],
            refusal_or_abstention_reason="No external AI provider is configured.",
        )


def normalize_provider_error(error: Exception) -> AIProviderError:
    """Convert an unexpected provider exception into a safe internal error."""
    if isinstance(error, AIProviderError):
        return error
    return AIProviderUnavailable("AI provider failed without a normalized error.")

