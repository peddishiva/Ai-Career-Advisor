"""Strict models for curated knowledge and deterministic retrieval."""

import re
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from config.knowledge_config import (
    DEFAULT_MAX_RESULTS,
    MAX_KNOWLEDGE_CONTENT_CHARS,
    MAX_QUERY_CHARS,
    MAX_RESULTS,
    MAX_QUERY_TERMS,
)
from .text_utils import canonical_role_references, canonical_skill_references, tokenize


class KnowledgeCategory(str, Enum):
    SKILL = "skill"
    ROLE = "role"
    CAREER_PATH = "career_path"
    LEARNING_GUIDANCE = "learning_guidance"
    INTERVIEW_TOPIC = "interview_topic"
    RESUME_GUIDANCE = "resume_guidance"
    JOB_REQUIREMENT_CONCEPT = "job_requirement_concept"


class SourceType(str, Enum):
    OFFICIAL_DOCUMENTATION = "official_documentation"
    CURATED_FRAMEWORK = "curated_framework"
    CURATED_INTERNAL_GUIDANCE = "curated_internal_guidance"
    EDUCATIONAL_REFERENCE = "educational_reference"


class TrustLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class KnowledgeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class KnowledgeDifficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class KnowledgeSource(KnowledgeModel):
    source_id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{2,80}$")
    source_type: SourceType
    title: str = Field(min_length=1, max_length=240)
    publisher: str = Field(min_length=1, max_length=200)
    url: Optional[str] = Field(default=None, max_length=1_000)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    curated_date: Optional[date] = None
    trust_level: TrustLevel = TrustLevel.HIGH

    @model_validator(mode="after")
    def validate_url_policy(self) -> "KnowledgeSource":
        if self.url:
            parsed = urlparse(self.url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("source URL must be an absolute HTTP(S) URL")
        if self.source_type is not SourceType.CURATED_INTERNAL_GUIDANCE and not self.url:
            raise ValueError("external knowledge sources require an explicit URL")
        return self


_UNSAFE_CONTENT_PATTERN = re.compile(
    r"(?:ignore\s+(?:all\s+)?previous\s+instructions|system\s+prompt|developer\s+message|"
    r"(?:execute|run)\s+(?:arbitrary|shell|python|javascript)\s+(?:code|command)|"
    r"(?:curl|wget|powershell|cmd(?:\.exe)?|subprocess)\b|"
    r"(?:api[_ -]?key|secret|password|access[_ -]?token)\s*[:=])",
    re.IGNORECASE,
)


class KnowledgeItem(KnowledgeModel):
    knowledge_id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{4,100}$")
    title: str = Field(min_length=1, max_length=240)
    category: KnowledgeCategory
    subcategory: Optional[str] = Field(default=None, max_length=120)
    content: str = Field(min_length=1, max_length=MAX_KNOWLEDGE_CONTENT_CHARS)
    keywords: List[str] = Field(default_factory=list, max_length=40)
    related_skills: List[str] = Field(default_factory=list, max_length=30)
    roles: List[str] = Field(default_factory=list, max_length=20)
    difficulty: Optional[KnowledgeDifficulty] = None
    source: KnowledgeSource
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE

    @field_validator("keywords", mode="before")
    @classmethod
    def normalize_keywords(cls, values: Any) -> List[str]:
        if values is None:
            return []
        if isinstance(values, str):
            values = [values]
        cleaned = {str(value).strip().casefold() for value in values if str(value).strip()}
        return sorted(cleaned)

    @field_validator("related_skills", mode="before")
    @classmethod
    def normalize_skills(cls, values: Any) -> List[str]:
        if values is None:
            return []
        if isinstance(values, str):
            values = [values]
        return canonical_skill_references(values)

    @field_validator("roles", mode="before")
    @classmethod
    def normalize_roles(cls, values: Any) -> List[str]:
        if values is None:
            return []
        if isinstance(values, str):
            values = [values]
        return canonical_role_references(values)

    @field_validator("content")
    @classmethod
    def reject_unsafe_content(cls, value: str) -> str:
        if _UNSAFE_CONTENT_PATTERN.search(value):
            raise ValueError("knowledge content contains executable or prompt-instruction text")
        return value.strip()


class RetrievalQuery(KnowledgeModel):
    query: str = Field(default="", max_length=MAX_QUERY_CHARS)
    categories: List[KnowledgeCategory] = Field(default_factory=list, max_length=7)
    skills: List[str] = Field(default_factory=list, max_length=20)
    roles: List[str] = Field(default_factory=list, max_length=10)
    minimum_trust: TrustLevel = TrustLevel.HIGH
    max_results: int = Field(default=DEFAULT_MAX_RESULTS, ge=1, le=MAX_RESULTS)

    @field_validator("skills", mode="before")
    @classmethod
    def normalize_query_skills(cls, values: Any) -> List[str]:
        if values is None:
            return []
        if isinstance(values, str):
            values = [values]
        return canonical_skill_references(values)

    @field_validator("roles", mode="before")
    @classmethod
    def normalize_query_roles(cls, values: Any) -> List[str]:
        if values is None:
            return []
        if isinstance(values, str):
            values = [values]
        return canonical_role_references(values)

    @model_validator(mode="after")
    def validate_query_size(self) -> "RetrievalQuery":
        if len([term for term in self.query.split() if term.strip()]) > MAX_QUERY_TERMS:
            raise ValueError("retrieval query contains too many terms")
        return self


class KnowledgeProvenance(KnowledgeModel):
    knowledge_id: str
    source_id: str
    source_type: SourceType
    source_title: str
    publisher: str
    url: Optional[str] = None
    source_version: str
    knowledge_version: str
    trust_level: TrustLevel


class RetrievalResult(KnowledgeModel):
    knowledge_id: str
    title: str
    category: KnowledgeCategory
    content: str
    score: float = Field(ge=0.0, le=1.0)
    matched_terms: List[str] = Field(default_factory=list)
    knowledge_version: str
    source: KnowledgeProvenance


class KnowledgeHealth(KnowledgeModel):
    status: str
    knowledge_base_version: str
    item_count: int = Field(ge=0)
