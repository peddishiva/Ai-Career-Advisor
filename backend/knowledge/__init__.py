"""Curated, deterministic, provider-independent knowledge retrieval."""

from .catalog import KNOWLEDGE_BASE_VERSION, build_default_repository
from .models import (
    KnowledgeCategory,
    KnowledgeItem,
    KnowledgeSource,
    KnowledgeStatus,
    RetrievalQuery,
    RetrievalResult,
    SourceType,
    TrustLevel,
)
from .repository import InMemoryKnowledgeRepository, KnowledgeRepository
from .retriever import KnowledgeRetriever

__all__ = [
    "InMemoryKnowledgeRepository",
    "KnowledgeCategory",
    "KnowledgeItem",
    "KnowledgeRepository",
    "KnowledgeRetriever",
    "KnowledgeSource",
    "KnowledgeStatus",
    "KNOWLEDGE_BASE_VERSION",
    "RetrievalQuery",
    "RetrievalResult",
    "SourceType",
    "TrustLevel",
    "build_default_repository",
]

