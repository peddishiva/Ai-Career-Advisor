"""Whitelist deterministic workflow data for future AI tasks."""

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping, Tuple

from config.ai_config import (
    MAX_CONTEXT_CHARS,
    REDACT_CANDIDATE_NAME_BY_DEFAULT,
    REDACT_PII_BY_DEFAULT,
    REDACTED_CANDIDATE_LABEL,
)
from .contracts import (
    AIContext,
    AITaskType,
    DeterministicAIInput,
    EvidenceReference,
    FlowType,
)


class ContextScopeError(ValueError):
    """Raised when input contains data from another workflow or session."""


_RESUME_KEYS = {"resume", "parsed_resume", "analysis"}
_JDXR_KEYS = {"resume", "parsed_resume", "job_description", "parsed_jd", "match", "match_result"}
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d().\-\s]{7,}\d)(?!\w)")
_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|/)(?:[^\s\\/]+[\\/])+[^\s]+")
_SECRET_RE = re.compile(r"\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*[^\s,;]+", re.I)


class AIContextBuilder:
    """Build a minimal context without reading storage or serializing sessions."""

    def build(self, source: DeterministicAIInput) -> AIContext:
        facts = source.deterministic_facts or {}
        allowed_keys = _RESUME_KEYS if source.flow_type is FlowType.RESUME_ANALYSIS else _JDXR_KEYS
        foreign_keys = set(facts) - allowed_keys
        if foreign_keys:
            raise ContextScopeError(
                f"{source.flow_type.value} context contains unsupported or cross-flow keys: "
                f"{', '.join(sorted(foreign_keys))}"
            )

        self._validate_embedded_scope(facts, source)
        if source.flow_type is FlowType.RESUME_ANALYSIS:
            deterministic, untrusted, registry = self._build_resume_context(facts, source.task)
        else:
            deterministic, untrusted, registry = self._build_jdxr_context(facts, source.task)

        context_payload = {
            "flow_type": source.flow_type.value,
            "deterministic": deterministic,
            "untrusted_data": untrusted,
            "evidence_registry": [item.model_dump(mode="json") for item in registry],
        }
        serialized = json.dumps(context_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if len(serialized) > MAX_CONTEXT_CHARS:
            raise ContextScopeError("AI context exceeds the configured maximum size")
        context_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return AIContext(
            flow_type=source.flow_type,
            candidate_label=REDACTED_CANDIDATE_LABEL,
            source_result_hash=source.deterministic_result_hash,
            deterministic=deterministic,
            untrusted_data=untrusted,
            evidence_registry=registry,
            context_hash=context_hash,
        )

    def build_context(self, source: DeterministicAIInput) -> AIContext:
        """Explicit alias for callers that prefer verb-based service APIs."""
        return self.build(source)

    def _validate_embedded_scope(self, value: Any, source: DeterministicAIInput) -> None:
        """Reject known session/flow identifiers embedded in unrelated data."""
        if isinstance(value, Mapping):
            for key, nested in value.items():
                normalized_key = str(key).lower()
                if normalized_key == "flow_type" and nested != source.flow_type.value:
                    raise ContextScopeError("embedded flow_type does not match request flow")
                if normalized_key in {"session_id", "source_session_id"} and nested != source.session_id:
                    raise ContextScopeError("embedded session_id does not match request session")
                if normalized_key == "resume_id" and nested not in {None, source.resume_id}:
                    raise ContextScopeError("embedded resume_id does not match request resume")
                if normalized_key == "jd_id" and nested not in {None, source.jd_id}:
                    raise ContextScopeError("embedded jd_id does not match request JD")
                self._validate_embedded_scope(nested, source)
        elif isinstance(value, list):
            for item in value:
                self._validate_embedded_scope(item, source)

    def _build_resume_context(
        self, facts: Mapping[str, Any], task: AITaskType
    ) -> Tuple[Dict[str, Any], Dict[str, Any], List[EvidenceReference]]:
        resume = self._first_fact(facts, "resume", "parsed_resume")
        analysis = facts.get("analysis") or {}
        registry: List[EvidenceReference] = []
        safe_resume, resume_untrusted = self._safe_resume(resume, registry)

        deterministic = {
            "task": task.value,
            "resume": {
                "skills": safe_resume["skills"],
                "experience": safe_resume["experience"],
                "education": safe_resume["education"],
                "projects": safe_resume["projects"],
                "certifications": safe_resume["certifications"],
                "section_evidence": safe_resume["section_evidence"],
            },
            "analysis": self._safe_resume_analysis(analysis),
        }
        return deterministic, {"resume_data": resume_untrusted}, registry

    def _build_jdxr_context(
        self, facts: Mapping[str, Any], task: AITaskType
    ) -> Tuple[Dict[str, Any], Dict[str, Any], List[EvidenceReference]]:
        resume = self._first_fact(facts, "resume", "parsed_resume")
        jd = self._first_fact(facts, "job_description", "parsed_jd")
        match = self._first_fact(facts, "match", "match_result")
        registry: List[EvidenceReference] = []
        safe_resume, resume_untrusted = self._safe_resume(resume, registry)
        safe_jd, jd_untrusted = self._safe_job_description(jd, registry)

        deterministic = {
            "task": task.value,
            "job_description": {
                "job_title": safe_jd["job_title"],
                "required_skills": safe_jd["required_skills"],
                "preferred_skills": safe_jd["preferred_skills"],
                "experience_requirements": safe_jd["experience_requirements"],
                "education_requirements": safe_jd["education_requirements"],
                "certifications": safe_jd["certifications"],
            },
            "match": self._safe_match_result(match, registry),
        }
        untrusted = {
            "resume_data": resume_untrusted,
            "job_description_data": jd_untrusted,
        }
        return deterministic, untrusted, registry

    def _first_fact(self, facts: Mapping[str, Any], *keys: str) -> Mapping[str, Any]:
        present = [key for key in keys if key in facts and facts[key] is not None]
        if len(present) > 1:
            raise ContextScopeError(f"Provide only one deterministic source for: {', '.join(keys)}")
        value = facts.get(present[0], {}) if present else {}
        return value if isinstance(value, Mapping) else {}

    def _safe_resume(
        self, resume: Mapping[str, Any], registry: List[EvidenceReference]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        skills = self._safe_strings(resume.get("skills", []))
        safe_experience = []
        experience_untrusted = []
        for index, entry in enumerate(self._mapping_list(resume.get("experience"))):
            evidence_id = self._add_evidence(registry, "RESUME-EXP", "experience", "resume.experience", index, entry.get("title"))
            safe_entry = self._select_text_fields(entry, ("title", "company", "date"))
            safe_entry["evidence_id"] = evidence_id
            safe_entry["skills_applied"] = self._safe_strings(entry.get("skills_applied", []))
            safe_experience.append(safe_entry)
            experience_untrusted.append({
                "evidence_id": evidence_id,
                "description": self._safe_text(entry.get("description"), 700),
            })

        safe_projects = []
        project_untrusted = []
        for index, entry in enumerate(self._mapping_list(resume.get("projects"))):
            evidence_id = self._add_evidence(registry, "RESUME-PROJECT", "project", "resume.projects", index, entry.get("title"))
            safe_entry = self._select_text_fields(entry, ("title",))
            safe_entry["evidence_id"] = evidence_id
            safe_entry["technologies"] = self._safe_strings(entry.get("technologies", []))
            safe_projects.append(safe_entry)
            project_untrusted.append({
                "evidence_id": evidence_id,
                "description": self._safe_text(entry.get("description"), 700),
            })

        safe_education = []
        for index, entry in enumerate(self._mapping_list(resume.get("education"))):
            evidence_id = self._add_evidence(registry, "RESUME-EDU", "education", "resume.education", index, entry.get("degree"))
            safe_entry = self._select_text_fields(entry, ("degree", "field"))
            safe_entry["evidence_id"] = evidence_id
            safe_education.append(safe_entry)

        safe_certifications = []
        for index, entry in enumerate(self._mapping_list(resume.get("certifications"))):
            label = entry.get("name") if isinstance(entry, Mapping) else entry
            evidence_id = self._add_evidence(registry, "RESUME-CERT", "certification", "resume.certifications", index, label)
            safe_entry = self._select_text_fields(entry, ("name", "issuer", "date"))
            safe_entry["evidence_id"] = evidence_id
            safe_certifications.append(safe_entry)

        section_evidence = resume.get("section_evidence") or {}
        safe_section_evidence = {
            key: self._safe_strings(value)
            for key, value in section_evidence.items()
            if key in {"skills_section", "experience_skills", "project_skills", "sections_detected"}
        }

        safe_resume = {
            "skills": [self._with_evidence_id(item, self._add_evidence(registry, "RESUME-SKILL", "skill", "resume.skills", index, item)) for index, item in enumerate(skills)],
            "experience": safe_experience,
            "education": safe_education,
            "projects": safe_projects,
            "certifications": safe_certifications,
            "section_evidence": safe_section_evidence,
        }
        return safe_resume, {
            "experience_descriptions": experience_untrusted,
            "project_descriptions": project_untrusted,
        }

    def _safe_job_description(
        self, jd: Mapping[str, Any], registry: List[EvidenceReference]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        required_skills = self._safe_strings(jd.get("required_skills", []))
        preferred_skills = self._safe_strings(jd.get("preferred_skills", []))
        safe_required_skills = [
            self._with_evidence_id(item, self._add_evidence(registry, "JD-SKILL", "required_skill", "jd.required_skills", index, item))
            for index, item in enumerate(required_skills)
        ]
        safe_preferred_skills = [
            self._with_evidence_id(item, self._add_evidence(registry, "JD-PREF-SKILL", "preferred_skill", "jd.preferred_skills", index, item))
            for index, item in enumerate(preferred_skills)
        ]

        def safe_requirement_list(key: str, prefix: str) -> List[Dict[str, Any]]:
            items = []
            for index, item in enumerate(self._mapping_list(jd.get(key))):
                label = item.get("text") or item.get("raw_text") or item.get("name") or item.get("requirement")
                evidence_id = self._add_evidence(registry, prefix, key, f"jd.{key}", index, label)
                safe_item = self._select_text_fields(
                    item,
                    ("text", "raw_text", "name", "requirement", "years", "min_years", "max_years", "domain", "degree_level", "fields", "status", "requirement_type"),
                )
                safe_item["evidence_id"] = evidence_id
                items.append(safe_item)
            return items

        responsibilities = []
        for index, item in enumerate(self._safe_strings(jd.get("responsibilities", []))):
            evidence_id = self._add_evidence(registry, "JD-RESP", "responsibility", "jd.responsibilities", index, item)
            responsibilities.append({"evidence_id": evidence_id, "text": item})

        safe_jd = {
            "job_title": self._safe_text(jd.get("job_title"), 240),
            "required_skills": safe_required_skills,
            "preferred_skills": safe_preferred_skills,
            "required_qualifications": safe_requirement_list("required_qualifications", "JD-REQ"),
            "preferred_qualifications": safe_requirement_list("preferred_qualifications", "JD-PREF-REQ"),
            "required_eligibility_requirements": safe_requirement_list("required_eligibility_requirements", "JD-ELIG"),
            "preferred_eligibility_requirements": safe_requirement_list("preferred_eligibility_requirements", "JD-PREF-ELIG"),
            "experience_requirements": safe_requirement_list("experience_requirements", "JD-EXP"),
            "education_requirements": safe_requirement_list("education_requirements", "JD-EDU"),
            "certifications": safe_requirement_list("certifications", "JD-CERT"),
            "responsibilities": responsibilities,
        }
        return safe_jd, {"responsibilities": responsibilities}

    def _safe_resume_analysis(self, analysis: Mapping[str, Any]) -> Dict[str, Any]:
        overall = analysis.get("overall_insights") or {}
        metrics = analysis.get("metrics") or {}
        candidate_info = {"candidate_label": REDACTED_CANDIDATE_LABEL}
        candidate_info.update(
            {
                key: (analysis.get("candidate_info") or {}).get(key)
                for key in ("skills_count", "experience_count", "education_count", "projects_count")
            }
        )
        safe = {
            "overall_insights": {
                "fit_score": overall.get("fit_score"),
                "week_change": overall.get("week_change"),
                "highlights": self._safe_strings(overall.get("highlights", [])),
            },
            "metrics": {
                key: metrics.get(key)
                for key in ("role_alignment", "skill_coverage", "readiness_actions_count")
                if metrics.get(key) is not None
            },
            "skill_strengths": self._safe_list_of_mappings(
                analysis.get("skill_strengths"), ("skill", "strength", "score", "evidence", "reason")
            ),
            "role_matches": self._safe_list_of_mappings(
                analysis.get("role_matches"), ("title", "match", "score", "missing_skills", "strengths", "reason")
            ),
            "next_actions": self._safe_list_of_mappings(
                analysis.get("next_actions"), ("title", "action", "reason", "skill", "priority")
            ),
            "candidate_info": candidate_info,
        }
        return safe

    def _safe_match_result(self, match: Mapping[str, Any], registry: List[EvidenceReference]) -> Dict[str, Any]:
        scalar_keys = (
            "score", "unconstrained_score", "readiness", "breakdown", "component_scores", "required_skill_coverage"
        )
        alignment_keys = (
            "required_skills", "preferred_skills", "experience_alignment", "project_alignment",
            "education_alignment", "certification_alignment", "eligibility_alignment",
            "qualification_alignment", "availability_alignment", "responsibility_alignment",
            "critical_gaps", "non_critical_gaps", "recommendations", "resume_alignment",
        )
        safe: Dict[str, Any] = {key: deepcopy(match.get(key)) for key in scalar_keys if key in match}
        for key in alignment_keys:
            if key in match:
                safe[key] = self._sanitize_value(match[key])
        return safe

    def _add_evidence(
        self,
        registry: List[EvidenceReference],
        prefix: str,
        category: str,
        source: str,
        index: int,
        label: Any,
    ) -> str:
        evidence_id = f"{prefix}-{index + 1:03d}"
        registry.append(
            EvidenceReference(
                evidence_id=evidence_id,
                category=category,
                source=source,
                label=self._safe_text(label, 240) or None,
            )
        )
        return evidence_id

    def _with_evidence_id(self, value: str, evidence_id: str) -> Dict[str, str]:
        return {"value": value, "evidence_id": evidence_id}

    def _select_text_fields(self, value: Any, fields: Iterable[str]) -> Dict[str, Any]:
        if not isinstance(value, Mapping):
            return {"value": self._safe_text(value, 240)}
        result: Dict[str, Any] = {}
        for field in fields:
            if field in value and value[field] is not None:
                result[field] = self._sanitize_value(value[field])
        return result

    def _safe_list_of_mappings(self, value: Any, fields: Iterable[str]) -> List[Dict[str, Any]]:
        result = []
        for item in self._mapping_list(value):
            result.append(self._select_text_fields(item, fields))
        return result

    def _mapping_list(self, value: Any) -> List[Mapping[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, Mapping)]

    def _safe_strings(self, value: Any) -> List[str]:
        if isinstance(value, str):
            return [self._safe_text(value, 240)] if value.strip() else []
        if not isinstance(value, (list, tuple, set)):
            return []
        return [cleaned for item in value if (cleaned := self._safe_text(item, 240))]

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): self._sanitize_value(nested)
                for key, nested in value.items()
                if str(key).lower() not in {"raw_text", "email", "phone", "filename", "file_path", "path", "api_key", "token", "password", "secret"}
            }
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, tuple):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, str):
            return self._safe_text(value, 700)
        return value

    def _safe_text(self, value: Any, limit: int) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        if REDACT_PII_BY_DEFAULT:
            text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
            text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
            text = _SECRET_RE.sub("[REDACTED_SECRET]", text)
            text = _PATH_RE.sub("[REDACTED_PATH]", text)
        return text[:limit]
