"""Typed contracts for the optional AI enrichment boundary."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from config.ai_config import AI_SCHEMA_VERSION, PROMPT_VERSION


class FlowType(str, Enum):
    RESUME_ANALYSIS = "resume_analysis"
    JDXR = "jdxr"


class AITaskType(str, Enum):
    RESUME_EXPLANATION = "resume_explanation"
    RESUME_CAREER_GUIDANCE = "resume_career_guidance"
    JDXR_MATCH_EXPLANATION = "jdxr_match_explanation"
    JDXR_GAP_EXPLANATION = "jdxr_gap_explanation"
    JDXR_RESUME_IMPROVEMENT = "jdxr_resume_improvement"
    JDXR_INTERVIEW_GUIDANCE = "jdxr_interview_guidance"


class AIResponseStatus(str, Enum):
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    COMPLETE = "complete"
    ABSTAINED = "abstained"
    INVALID = "invalid"


RESUME_TASKS = {
    AITaskType.RESUME_EXPLANATION,
    AITaskType.RESUME_CAREER_GUIDANCE,
}
JDXR_TASKS = {
    AITaskType.JDXR_MATCH_EXPLANATION,
    AITaskType.JDXR_GAP_EXPLANATION,
    AITaskType.JDXR_RESUME_IMPROVEMENT,
    AITaskType.JDXR_INTERVIEW_GUIDANCE,
}


class ContractModel(BaseModel):
    """Common strict model behavior for Phase 3A contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class EvidenceReference(ContractModel):
    evidence_id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{2,80}$")
    category: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=160)
    label: Optional[str] = Field(default=None, max_length=240)


class Citation(ContractModel):
    source_id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{2,120}$")
    title: str = Field(min_length=1, max_length=240)
    url: Optional[str] = Field(default=None, max_length=1_000)
    version: Optional[str] = Field(default=None, max_length=120)
    chunk_id: Optional[str] = Field(default=None, max_length=160)


class KnowledgeReference(ContractModel):
    """Minimal retrieved knowledge plus provenance safe to send to a provider."""

    knowledge_id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{4,100}$")
    title: str = Field(min_length=1, max_length=240)
    category: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=4_000)
    source_id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{2,80}$")
    source_title: str = Field(min_length=1, max_length=240)
    publisher: str = Field(min_length=1, max_length=200)
    url: Optional[str] = Field(default=None, max_length=1_000)
    source_version: str = Field(min_length=1, max_length=120)
    knowledge_version: str = Field(min_length=1, max_length=120)
    trust_level: str = Field(min_length=1, max_length=20)


class AIInsight(ContractModel):
    text: str = Field(min_length=1, max_length=2_000)
    evidence_reference_ids: List[str] = Field(default_factory=list)
    knowledge_reference_ids: List[str] = Field(default_factory=list)


class AIAction(ContractModel):
    text: str = Field(min_length=1, max_length=2_000)
    evidence_reference_ids: List[str] = Field(default_factory=list)
    knowledge_reference_ids: List[str] = Field(default_factory=list)


class DeterministicAIInput(ContractModel):
    """Validated input assembled by an existing deterministic workflow."""

    flow_type: FlowType
    session_id: str = Field(min_length=1, max_length=160)
    resume_id: Optional[str] = Field(default=None, max_length=160)
    jd_id: Optional[str] = Field(default=None, max_length=160)
    deterministic_result_hash: str = Field(min_length=1, max_length=128)
    deterministic_facts: Dict[str, Any]
    task: AITaskType
    schema_version: str = AI_SCHEMA_VERSION

    @model_validator(mode="after")
    def validate_scope(self) -> "DeterministicAIInput":
        if self.flow_type is FlowType.RESUME_ANALYSIS:
            if not self.resume_id:
                raise ValueError("resume_analysis requires resume_id")
            if self.jd_id:
                raise ValueError("resume_analysis cannot include jd_id")
            if self.task not in RESUME_TASKS:
                raise ValueError("resume_analysis does not support this AI task")
        else:
            if not self.resume_id or not self.jd_id:
                raise ValueError("jdxr requires resume_id and jd_id")
            if self.task not in JDXR_TASKS:
                raise ValueError("jdxr does not support this AI task")
        return self


class AIContext(ContractModel):
    """Whitelisted model context; deterministic facts are kept separate."""

    flow_type: FlowType
    candidate_label: str = Field(default="Candidate", min_length=1, max_length=80)
    source_result_hash: str = Field(min_length=1, max_length=128)
    deterministic: Dict[str, Any]
    untrusted_data: Dict[str, Any] = Field(default_factory=dict)
    evidence_registry: List[EvidenceReference] = Field(default_factory=list)
    retrieved_knowledge: List[KnowledgeReference] = Field(default_factory=list)
    context_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class PromptPackage(ContractModel):
    system_policy: str = Field(min_length=1, max_length=8_000)
    task_instructions: str = Field(min_length=1, max_length=4_000)
    structured_context: Dict[str, Any]
    evidence_registry: List[EvidenceReference] = Field(default_factory=list)
    knowledge_references: List[KnowledgeReference] = Field(default_factory=list)
    output_schema: Dict[str, Any]
    prompt_version: str = PROMPT_VERSION


class AIRequest(ContractModel):
    request_id: str = Field(min_length=1, max_length=160)
    flow_type: FlowType
    session_id: str = Field(min_length=1, max_length=160)
    resume_id: Optional[str] = Field(default=None, max_length=160)
    jd_id: Optional[str] = Field(default=None, max_length=160)
    task: AITaskType
    context: AIContext
    prompt: PromptPackage
    prompt_version: str = PROMPT_VERSION
    schema_version: str = AI_SCHEMA_VERSION

    @model_validator(mode="after")
    def validate_scope(self) -> "AIRequest":
        if self.flow_type is not self.context.flow_type:
            raise ValueError("request and context flow_type must match")
        if self.flow_type is FlowType.RESUME_ANALYSIS:
            if not self.resume_id or self.jd_id or self.task not in RESUME_TASKS:
                raise ValueError("invalid resume_analysis request scope")
        else:
            if not self.resume_id or not self.jd_id or self.task not in JDXR_TASKS:
                raise ValueError("invalid jdxr request scope")
        return self


class AIResponse(ContractModel):
    """Structured enrichment kept separate from deterministic output."""

    schema_version: str = AI_SCHEMA_VERSION
    status: AIResponseStatus
    summary: str = Field(default="", max_length=4_000)
    strengths: List[AIInsight] = Field(default_factory=list)
    priority_gaps: List[AIInsight] = Field(default_factory=list)
    learning_actions: List[AIAction] = Field(default_factory=list)
    resume_actions: List[AIAction] = Field(default_factory=list)
    interview_actions: List[AIAction] = Field(default_factory=list)
    evidence_references: List[str] = Field(default_factory=list)
    knowledge_references: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    confidence_notes: List[str] = Field(default_factory=list)
    refusal_or_abstention_reason: Optional[str] = Field(default=None, max_length=1_000)


class AIOrchestrationResult(ContractModel):
    """Combined result that cannot overwrite deterministic result fields."""

    request_id: str
    flow_type: FlowType
    session_id: str
    context_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    ai_status: AIResponseStatus
    deterministic_result: Dict[str, Any]
    ai: Optional[AIResponse] = None
    error_code: Optional[str] = None
