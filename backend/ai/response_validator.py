"""Strict response and future grounding validation contracts."""

from typing import Iterable, Protocol, Sequence, Set, runtime_checkable

from pydantic import ValidationError

from .contracts import AIContext, AIResponse


class AIResponseValidationError(ValueError):
    """Raised when an AI response is not safe for the enrichment boundary."""


class GroundingValidationError(AIResponseValidationError):
    """Raised when a claim references evidence that is not in the registry."""


@runtime_checkable
class GroundingValidator(Protocol):
    def validate_claim(
        self, claim: str, evidence_reference_ids: Sequence[str], context: AIContext
    ) -> bool:
        """Return whether a claim is linked to registered evidence."""


class EvidenceGroundingValidator:
    """Minimal Phase 3A grounding check; no semantic entailment is attempted."""

    def validate_claim(
        self, claim: str, evidence_reference_ids: Sequence[str], context: AIContext
    ) -> bool:
        if not claim.strip() or not evidence_reference_ids:
            return False
        registered = {item.evidence_id for item in context.evidence_registry}
        return all(reference_id in registered for reference_id in evidence_reference_ids)


class AIResponseValidator:
    """Validate schema, evidence references, and deterministic-field separation."""

    _FORBIDDEN_DETERMINISTIC_KEYS: Set[str] = {
        "score",
        "job_match_score",
        "fit_score",
        "skill_coverage",
        "readiness",
        "required_skill_statuses",
        "experience_years",
        "education_match",
        "certification_match",
        "eligibility_match",
    }

    def __init__(self, grounding_validator: GroundingValidator | None = None):
        self.grounding_validator = grounding_validator or EvidenceGroundingValidator()

    def validate(self, response: AIResponse | dict, context: AIContext) -> AIResponse:
        try:
            parsed = AIResponse.model_validate(response)
        except ValidationError as error:
            raise AIResponseValidationError("AI response schema validation failed.") from error

        registered = {item.evidence_id for item in context.evidence_registry}
        response_ids = set(parsed.evidence_references)
        self._validate_evidence_ids(response_ids, registered)

        for insight in [*parsed.strengths, *parsed.priority_gaps]:
            self._validate_claim(insight.text, insight.evidence_reference_ids, registered, context)
        for action in [*parsed.learning_actions, *parsed.resume_actions, *parsed.interview_actions]:
            self._validate_claim(action.text, action.evidence_reference_ids, registered, context)

        self._reject_deterministic_mutation(parsed.model_dump(mode="json"))
        if parsed.status in {"unavailable", "abstained", "disabled", "invalid"} and not parsed.refusal_or_abstention_reason:
            raise AIResponseValidationError("Unavailable or abstained responses require a reason.")
        return parsed

    def _validate_claim(
        self,
        claim: str,
        reference_ids: Sequence[str],
        registered: Set[str],
        context: AIContext,
    ) -> None:
        self._validate_evidence_ids(set(reference_ids), registered)
        if not self.grounding_validator.validate_claim(claim, reference_ids, context):
            raise GroundingValidationError("AI claim is not grounded by registered evidence.")

    def _validate_evidence_ids(self, ids: Iterable[str], registered: Set[str]) -> None:
        for evidence_id in ids:
            if evidence_id not in registered:
                raise GroundingValidationError(f"Unknown evidence reference: {evidence_id}")

    def _reject_deterministic_mutation(self, value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if key in self._FORBIDDEN_DETERMINISTIC_KEYS:
                    raise AIResponseValidationError(
                        f"AI response cannot contain deterministic field: {key}"
                    )
                self._reject_deterministic_mutation(nested)
        elif isinstance(value, list):
            for item in value:
                self._reject_deterministic_mutation(item)

