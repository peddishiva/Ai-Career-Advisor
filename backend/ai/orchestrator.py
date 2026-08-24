"""Offline orchestration boundary for future AI enrichment."""

from copy import deepcopy
import hashlib
import re
from typing import Any, Iterable, Mapping, Optional
from uuid import uuid4

from config.ai_config import AI_SCHEMA_VERSION, PROMPT_VERSION, AIProviderConfig, load_ai_config
from .context_builder import AIContextBuilder
from .contracts import (
    AIOrchestrationResult,
    AIRequest,
    AIResponse,
    AIResponseStatus,
    DeterministicAIInput,
)
from .prompt_builder import PromptBuilder
from .provider import (
    AIProvider,
    AIProviderConfigurationError,
    AIProviderInvalidResponse,
    NullAIProvider,
    build_configured_provider,
    normalize_provider_error,
)
from .response_validator import AIResponseValidationError, AIResponseValidator, GroundingValidationError


class AIOrchestrator:
    """Compose the AI boundary without parsing or scoring anything."""

    def __init__(
        self,
        provider: Optional[AIProvider] = None,
        enabled: Optional[bool] = None,
        config: Optional[AIProviderConfig] = None,
        context_builder: Optional[AIContextBuilder] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        response_validator: Optional[AIResponseValidator] = None,
    ):
        self.config = config or load_ai_config()
        self.provider = provider or build_configured_provider(self.config)
        if not isinstance(self.provider, AIProvider):
            raise AIProviderConfigurationError("Configured AI provider does not implement AIProvider.")
        self.enabled = self.config.enabled if enabled is None else enabled
        self.context_builder = context_builder or AIContextBuilder()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.response_validator = response_validator or AIResponseValidator()

    def enrich(
        self,
        source: DeterministicAIInput,
        deterministic_result: Optional[Mapping[str, Any]] = None,
        retrieved_knowledge: Optional[Iterable[Mapping[str, Any]]] = None,
    ) -> AIOrchestrationResult:
        request_id = str(uuid4())
        preserved_result = deepcopy(dict(deterministic_result or {}))
        try:
            context = self.context_builder.build(source, retrieved_knowledge=retrieved_knowledge)
        except Exception as error:
            error_code = "context_too_large" if "exceeds" in str(error).casefold() else "context_invalid"
            return AIOrchestrationResult(
                request_id=request_id,
                flow_type=source.flow_type,
                session_id=source.session_id,
                context_hash=self._fallback_context_hash(source),
                ai_status=AIResponseStatus.UNAVAILABLE,
                deterministic_result=preserved_result,
                ai=None,
                error_code=error_code,
            )
        prompt = self.prompt_builder.build(context, source.task)
        request = AIRequest(
            request_id=request_id,
            flow_type=source.flow_type,
            session_id=source.session_id,
            resume_id=source.resume_id,
            jd_id=source.jd_id,
            task=source.task,
            context=context,
            prompt=prompt,
            prompt_version=PROMPT_VERSION,
            schema_version=AI_SCHEMA_VERSION,
        )

        if not self.enabled:
            return AIOrchestrationResult(
                request_id=request_id,
                flow_type=source.flow_type,
                session_id=source.session_id,
                context_hash=context.context_hash,
                ai_status=AIResponseStatus.DISABLED,
                deterministic_result=preserved_result,
                ai=None,
            )

        try:
            response = self.provider.generate(request)
            validated = self.response_validator.validate(response, context)
        except GroundingValidationError:
            return AIOrchestrationResult(
                request_id=request_id,
                flow_type=source.flow_type,
                session_id=source.session_id,
                context_hash=context.context_hash,
                ai_status=AIResponseStatus.ABSTAINED,
                deterministic_result=preserved_result,
                ai=None,
                error_code="grounding_failed",
            )
        except AIResponseValidationError:
            normalized = AIProviderInvalidResponse("AI provider returned an invalid structured response.")
            return AIOrchestrationResult(
                request_id=request_id,
                flow_type=source.flow_type,
                session_id=source.session_id,
                context_hash=context.context_hash,
                ai_status=AIResponseStatus.INVALID,
                deterministic_result=preserved_result,
                ai=None,
                error_code=normalized.code,
            )
        except Exception as error:
            normalized = normalize_provider_error(error)
            return AIOrchestrationResult(
                request_id=request_id,
                flow_type=source.flow_type,
                session_id=source.session_id,
                context_hash=context.context_hash,
                ai_status=AIResponseStatus.UNAVAILABLE,
                deterministic_result=preserved_result,
                ai=None,
                error_code=normalized.code,
            )

        return AIOrchestrationResult(
            request_id=request_id,
            flow_type=source.flow_type,
            session_id=source.session_id,
            context_hash=context.context_hash,
            ai_status=validated.status,
            deterministic_result=preserved_result,
            ai=validated,
        )

    def _fallback_context_hash(self, source: DeterministicAIInput) -> str:
        value = source.deterministic_result_hash
        if re.fullmatch(r"[a-f0-9]{64}", value):
            return value
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
