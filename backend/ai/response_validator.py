"""Strict response and future grounding validation contracts."""

import re
from typing import Iterable, Protocol, Sequence, Set, runtime_checkable

from pydantic import ValidationError

from .contracts import AIContext, AIResponse
from utils.normalization import extract_matched_skills


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
        "match_status",
        "required_skill_status",
    }

    def __init__(self, grounding_validator: GroundingValidator | None = None):
        self.grounding_validator = grounding_validator or EvidenceGroundingValidator()

    def validate(self, response: AIResponse | dict, context: AIContext) -> AIResponse:
        try:
            payload = response.model_dump(mode="json") if isinstance(response, AIResponse) else response
            parsed = AIResponse.model_validate(payload)
        except ValidationError as error:
            raise AIResponseValidationError("AI response schema validation failed.") from error

        registered = {item.evidence_id for item in context.evidence_registry}
        registered_knowledge = {item.knowledge_id for item in context.retrieved_knowledge}
        response_ids = set(parsed.evidence_references)
        self._validate_evidence_ids(response_ids, registered)
        self._validate_knowledge_ids(set(parsed.knowledge_references), registered_knowledge)
        if parsed.summary:
            self._reject_unsupported_candidate_claim(parsed.summary, context)

        for insight in [*parsed.strengths, *parsed.priority_gaps]:
            self._validate_claim(
                insight.text,
                insight.evidence_reference_ids,
                insight.knowledge_reference_ids,
                registered,
                registered_knowledge,
                context,
            )
        for action in [*parsed.learning_actions, *parsed.resume_actions, *parsed.interview_actions]:
            self._validate_claim(
                action.text,
                action.evidence_reference_ids,
                action.knowledge_reference_ids,
                registered,
                registered_knowledge,
                context,
            )

        self._reject_deterministic_mutation(parsed.model_dump(mode="json"))
        if parsed.status in {"unavailable", "abstained", "disabled", "invalid"} and not parsed.refusal_or_abstention_reason:
            raise AIResponseValidationError("Unavailable or abstained responses require a reason.")
        return parsed

    def _validate_claim(
        self,
        claim: str,
        evidence_reference_ids: Sequence[str],
        knowledge_reference_ids: Sequence[str],
        registered: Set[str],
        registered_knowledge: Set[str],
        context: AIContext,
    ) -> None:
        self._validate_evidence_ids(set(evidence_reference_ids), registered)
        self._validate_knowledge_ids(set(knowledge_reference_ids), registered_knowledge)
        if not evidence_reference_ids and not knowledge_reference_ids:
            raise GroundingValidationError("AI claim is not grounded by evidence or knowledge.")
        if evidence_reference_ids and not self.grounding_validator.validate_claim(claim, evidence_reference_ids, context):
            raise GroundingValidationError("AI claim is not grounded by registered evidence.")
        self._reject_unsupported_candidate_claim(claim, context)

    def _validate_evidence_ids(self, ids: Iterable[str], registered: Set[str]) -> None:
        for evidence_id in ids:
            if evidence_id not in registered:
                raise GroundingValidationError(f"Unknown evidence reference: {evidence_id}")

    def _validate_knowledge_ids(self, ids: Iterable[str], registered: Set[str]) -> None:
        for knowledge_id in ids:
            if knowledge_id not in registered:
                raise GroundingValidationError(f"Unknown knowledge reference: {knowledge_id}")

    def _reject_unsupported_candidate_claim(self, claim: str, context: AIContext) -> None:
        """Reject common factual hallucination shapes without attempting semantic scoring."""

        normalized_claim = claim.casefold()
        candidate_skills = self._candidate_skills(context)
        mentioned_skills = set(extract_matched_skills(claim))
        possession_language = re.search(
            r"\b(?:you|your|candidate|profile|resume)\b.{0,45}\b(?:have|has|demonstrate|demonstrates|show|shows|"
            r"experience|skilled|proficient|built|developed|worked)\b",
            normalized_claim,
        ) or re.search(
            r"\b(?:have|has|demonstrate|demonstrates|show|shows|skilled|proficient|built|developed|worked)\b.{0,45}\b"
            r"(?:you|your|candidate|profile|resume)\b",
            normalized_claim,
        )
        if possession_language and mentioned_skills - candidate_skills:
            unknown = sorted(mentioned_skills - candidate_skills)
            raise GroundingValidationError(f"AI claim presents unsupported candidate skills: {', '.join(unknown)}")

        duration_match = re.search(r"\b(\d+(?:\.\d+)?)\+?\s+years?\b", normalized_claim)
        duration_context = self._resume_context_text(context) if possession_language else self._context_text(context)
        if duration_match and duration_match.group(0) not in duration_context.casefold():
            raise GroundingValidationError("AI claim presents unsupported experience duration.")

        metric_match = re.search(r"\b(?:increased|reduced|improved|saved|grew|cut)\b[^.]{0,70}\b\d+(?:\.\d+)?%", normalized_claim)
        if metric_match and metric_match.group(0) not in self._context_text(context).casefold():
            raise GroundingValidationError("AI claim presents an unsupported metric.")

        if re.search(r"\b(?:you|your|candidate|profile)[^.]{0,60}\bcertif(?:ied|ication|ications)\b", normalized_claim):
            certifications = self._candidate_certifications(context)
            if not certifications or not any(value in normalized_claim for value in certifications):
                raise GroundingValidationError("AI claim presents an unsupported certification.")

        if context.flow_type.value == "jdxr" and re.search(r"\b(?:role|job|position)\b[^.]{0,45}\b(?:requires|requirement|must have|needs)\b", normalized_claim):
            jd_skills = self._job_skills(context)
            if mentioned_skills - jd_skills:
                unknown = sorted(mentioned_skills - jd_skills)
                raise GroundingValidationError(f"AI claim presents unsupported job requirements: {', '.join(unknown)}")

        project_match = re.search(
            r"\b(?:the\s+)?([A-Z][A-Za-z0-9.+#&/-]*(?:\s+[A-Z][A-Za-z0-9.+#&/-]*){0,5})\s+project\b",
            claim,
            re.IGNORECASE,
        )
        if project_match and re.search(r"\b(?:you|your|candidate|profile|resume|project)\b", normalized_claim):
            project_label = re.sub(r"^(?:the|your)\s+", "", project_match.group(1).strip(), flags=re.IGNORECASE).casefold()
            known_projects = {
                str(item.get("title", "")).casefold()
                for item in (context.deterministic.get("resume") or {}).get("projects", [])
                if isinstance(item, dict) and item.get("title")
            }
            if project_label and known_projects and not any(project_label == value or project_label in value or value in project_label for value in known_projects):
                raise GroundingValidationError("AI claim presents an unsupported project name.")

    def _candidate_skills(self, context: AIContext) -> Set[str]:
        resume = (context.deterministic.get("resume") or {})
        values: list[str] = []
        for item in resume.get("skills", []):
            values.append(item.get("value", "") if isinstance(item, dict) else str(item))
        for entry in [*resume.get("experience", []), *resume.get("projects", [])]:
            if isinstance(entry, dict):
                values.extend(entry.get("skills_applied", []))
                values.extend(entry.get("technologies", []))
        return set(extract_matched_skills(" ".join(str(value) for value in values)))

    def _candidate_certifications(self, context: AIContext) -> Set[str]:
        resume = (context.deterministic.get("resume") or {})
        return {
            str(item.get("name", "")).casefold()
            for item in resume.get("certifications", [])
            if isinstance(item, dict) and item.get("name")
        }

    def _job_skills(self, context: AIContext) -> Set[str]:
        job_description = context.deterministic.get("job_description") or {}
        values = []
        for key in ("required_skills", "preferred_skills"):
            for item in job_description.get(key, []):
                values.append(item.get("value", "") if isinstance(item, dict) else str(item))
        return set(extract_matched_skills(" ".join(values)))

    def _resume_context_text(self, context: AIContext) -> str:
        return str(context.deterministic.get("resume") or {})

    def _context_text(self, context: AIContext) -> str:
        return str(context.deterministic)

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
