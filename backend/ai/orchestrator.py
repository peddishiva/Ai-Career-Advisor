"""Offline orchestration boundary for future AI enrichment."""

from copy import deepcopy
from typing import Any, Dict, Mapping, Optional
from uuid import uuid4

from config.ai_config import AI_ENABLED, AI_SCHEMA_VERSION, PROMPT_VERSION
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
    normalize_provider_error,
)
from .response_validator import AIResponseValidationError, AIResponseValidator


class AIOrchestrator:
    """Compose the AI boundary without parsing or scoring anything."""

    def __init__(
        self,
        provider: Optional[AIProvider] = None,
        enabled: bool = AI_ENABLED,
        context_builder: Optional[AIContextBuilder] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        response_validator: Optional[AIResponseValidator] = None,
    ):
        self.provider = provider or NullAIProvider()
        if not isinstance(self.provider, NullAIProvider):
            raise AIProviderConfigurationError(
                "Phase 3A only permits the offline NullAIProvider."
            )
        self.enabled = enabled
        self.context_builder = context_builder or AIContextBuilder()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.response_validator = response_validator or AIResponseValidator()

    def enrich(
        self,
        source: DeterministicAIInput,
        deterministic_result: Optional[Mapping[str, Any]] = None,
    ) -> AIOrchestrationResult:
        context = self.context_builder.build(source)
        prompt = self.prompt_builder.build(context, source.task)
        request_id = str(uuid4())
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

        preserved_result = deepcopy(dict(deterministic_result or {}))
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
        except AIResponseValidationError as error:
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
