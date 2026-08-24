"""Application service for optional, flow-isolated AI enrichment."""

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

from config.ai_config import AI_MAX_RETRIEVAL_RESULTS
from config.roles import ROLE_DEFINITIONS
from knowledge.catalog import build_default_repository
from knowledge.models import RetrievalQuery
from knowledge.retriever import KnowledgeRetriever
from utils.normalization import extract_matched_skills

from ai.contracts import (
    AITaskType,
    AIOrchestrationResult,
    DeterministicAIInput,
    FlowType,
)
from ai.improvement_facts import ImprovementFactsBuilder
from ai.orchestrator import AIOrchestrator


class AIEnrichmentError(Exception):
    """Safe application error for an AI enrichment request."""

    def __init__(self, status_code: int, error: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.error = error
        self.message = message


class AIEnrichmentService:
    """Build bounded AI inputs without changing deterministic analysis."""

    FILE_ID_PATTERN = re.compile(r"^[a-fA-F0-9-]{36}$")

    def __init__(
        self,
        analysis_dir: Path | str = Path("uploads/analysis"),
        orchestrator: Optional[AIOrchestrator] = None,
        retriever: Optional[KnowledgeRetriever] = None,
        jdxr_session_service: Any = None,
    ):
        self.analysis_dir = Path(analysis_dir)
        self.orchestrator = orchestrator or AIOrchestrator()
        self.retriever = retriever or KnowledgeRetriever(build_default_repository())
        self.jdxr_session_service = jdxr_session_service
        self.improvement_facts_builder = ImprovementFactsBuilder()

    def enrich_resume(self, file_id: str, task: AITaskType) -> AIOrchestrationResult:
        stored = self._load_resume_analysis(file_id)
        parsed_resume = stored.get("parsed_resume")
        if not isinstance(parsed_resume, Mapping):
            raise AIEnrichmentError(422, "resume_analysis_incomplete", "This resume analysis has no structured resume evidence.")
        deterministic_result = self._public_analysis(stored)
        improvement_facts = (
            self.improvement_facts_builder.build_resume(parsed_resume, deterministic_result)
            if task is AITaskType.RESUME_IMPROVEMENT else None
        )
        deterministic_hash_input = {
            "result": deterministic_result,
            "parsed_resume": dict(parsed_resume),
            "improvement_facts": improvement_facts,
        } if improvement_facts is not None else deterministic_result
        source = DeterministicAIInput(
            flow_type=FlowType.RESUME_ANALYSIS,
            session_id=file_id,
            resume_id=file_id,
            deterministic_result_hash=self._hash(deterministic_hash_input),
            deterministic_facts={
                "parsed_resume": deepcopy(dict(parsed_resume)),
                "analysis": deepcopy(deterministic_result),
                **({"improvement_facts": improvement_facts} if improvement_facts is not None else {}),
            },
            task=task,
        )
        knowledge = self._retrieve(source)
        return self.orchestrator.enrich(source, deterministic_result, retrieved_knowledge=knowledge)

    def enrich_jdxr(
        self,
        session_id: str,
        task: AITaskType,
        session_service: Any = None,
    ) -> AIOrchestrationResult:
        service = session_service or self.jdxr_session_service
        if service is None:
            raise AIEnrichmentError(500, "jdxr_service_unavailable", "JDxR session service is unavailable.")
        state = service.get_ai_source(session_id)
        deterministic_result = deepcopy(state["deterministic_result"])
        improvement_facts = (
            self.improvement_facts_builder.build_jdxr(
                state["parsed_resume"], state["parsed_jd"], deterministic_result
            )
            if task is AITaskType.JDXR_RESUME_IMPROVEMENT else None
        )
        deterministic_hash_input = {
            "result": deterministic_result,
            "parsed_resume": state["parsed_resume"],
            "parsed_jd": state["parsed_jd"],
            "improvement_facts": improvement_facts,
        } if improvement_facts is not None else deterministic_result
        source = DeterministicAIInput(
            flow_type=FlowType.JDXR,
            session_id=session_id,
            resume_id=state["resume_id"],
            jd_id=state["jd_id"],
            deterministic_result_hash=self._hash(deterministic_hash_input),
            deterministic_facts={
                "parsed_resume": deepcopy(state["parsed_resume"]),
                "parsed_jd": deepcopy(state["parsed_jd"]),
                "match_result": deepcopy(deterministic_result),
                **({"improvement_facts": improvement_facts} if improvement_facts is not None else {}),
            },
            task=task,
        )
        knowledge = self._retrieve(source)
        return self.orchestrator.enrich(source, deterministic_result, retrieved_knowledge=knowledge)

    def enrich_resume_improvements(self, file_id: str) -> AIOrchestrationResult:
        return self.enrich_resume(file_id, AITaskType.RESUME_IMPROVEMENT)

    def enrich_jdxr_improvements(self, session_id: str, session_service: Any = None) -> AIOrchestrationResult:
        return self.enrich_jdxr(
            session_id,
            AITaskType.JDXR_RESUME_IMPROVEMENT,
            session_service=session_service,
        )

    def _load_resume_analysis(self, file_id: str) -> Dict[str, Any]:
        if not self.FILE_ID_PATTERN.fullmatch(file_id or ""):
            raise AIEnrichmentError(404, "analysis_not_found", "Resume analysis was not found.")
        base = self.analysis_dir.resolve()
        candidate = (base / f"{file_id}.json").resolve()
        if candidate.parent != base or not candidate.exists():
            raise AIEnrichmentError(404, "analysis_not_found", "Resume analysis was not found.")
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception as error:
            raise AIEnrichmentError(500, "analysis_unreadable", "Resume analysis could not be loaded.") from error
        if not isinstance(payload, dict):
            raise AIEnrichmentError(500, "analysis_unreadable", "Resume analysis could not be loaded.")
        return payload

    def _public_analysis(self, stored: Mapping[str, Any]) -> Dict[str, Any]:
        result = deepcopy(dict(stored))
        result.pop("parsed_resume", None)
        return result

    def _retrieve(self, source: DeterministicAIInput) -> list[Dict[str, Any]]:
        facts = source.deterministic_facts
        resume = facts.get("parsed_resume") or {}
        analysis = facts.get("analysis") or {}
        jd = facts.get("parsed_jd") or {}
        match = facts.get("match_result") or {}
        improvement_facts = facts.get("improvement_facts") or {}

        skills = set(extract_matched_skills(" ".join(self._string_values(resume.get("skills", [])))))
        roles = set()
        query_parts = [source.task.value.replace("_", " ")]
        if source.flow_type is FlowType.RESUME_ANALYSIS:
            for role in analysis.get("role_matches", []) if isinstance(analysis, Mapping) else []:
                title = role.get("title") if isinstance(role, Mapping) else None
                if title in ROLE_DEFINITIONS:
                    roles.add(title)
                    query_parts.append(title)
            query_parts.extend(self._gap_strings(analysis))
            query_parts.extend(["resume", "learning", "interview"])
        else:
            job_title = jd.get("job_title")
            if job_title:
                query_parts.append(str(job_title))
            if isinstance(jd, Mapping):
                skills.update(extract_matched_skills(" ".join(self._string_values(jd.get("required_skills", [])))))
                skills.update(extract_matched_skills(" ".join(self._string_values(jd.get("preferred_skills", [])))))
            query_parts.extend(self._gap_strings(match))
            query_parts.extend(["learning", "interview", "resume"])
            if job_title in ROLE_DEFINITIONS:
                roles.add(job_title)

        if source.task in {AITaskType.RESUME_IMPROVEMENT, AITaskType.JDXR_RESUME_IMPROVEMENT}:
            for opportunity in improvement_facts.get("opportunities", [])[:10]:
                if isinstance(opportunity, Mapping):
                    query_parts.extend([
                        str(opportunity.get("title", "")),
                        str(opportunity.get("knowledge_query", "")),
                    ])

        query = " ".join(query_parts)[:400]
        results = self.retriever.retrieve(
            RetrievalQuery(
                query=query,
                skills=sorted(skills)[:20],
                roles=sorted(roles)[:10],
                max_results=AI_MAX_RETRIEVAL_RESULTS,
            )
        )
        return [self._knowledge_reference(result) for result in results]

    def _knowledge_reference(self, result: Any) -> Dict[str, Any]:
        source = result.source
        return {
            "knowledge_id": result.knowledge_id,
            "title": result.title,
            "category": result.category.value,
            "content": result.content,
            "source_id": source.source_id,
            "source_title": source.source_title,
            "publisher": source.publisher,
            "url": source.url,
            "source_version": source.source_version,
            "knowledge_version": source.knowledge_version,
            "trust_level": source.trust_level.value,
        }

    def _gap_strings(self, value: Any) -> list[str]:
        results = []
        if isinstance(value, Mapping):
            for key, nested in value.items():
                if key in {
                    "missing_skills",
                    "critical_gaps",
                    "non_critical_gaps",
                    "weak_skills",
                    "next_actions",
                }:
                    results.extend(self._string_values(nested))
                else:
                    results.extend(self._gap_strings(nested))
        elif isinstance(value, list):
            for item in value:
                results.extend(self._gap_strings(item))
        return results[:20]

    def _string_values(self, value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, Mapping):
            return [
                str(value[key])
                for key in ("name", "skill", "title", "text", "description", "action")
                if value.get(key) is not None
            ]
        if isinstance(value, (list, tuple, set)):
            results = []
            for item in value:
                results.extend(self._string_values(item))
            return results
        return []

    def _hash(self, value: Mapping[str, Any]) -> str:
        serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
