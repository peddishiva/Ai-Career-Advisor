"""Provenance construction for knowledge retrieval results."""

from .models import KnowledgeItem, KnowledgeProvenance


def provenance_for(item: KnowledgeItem) -> KnowledgeProvenance:
    """Expose citation-safe source metadata without catalog internals."""
    return KnowledgeProvenance(
        knowledge_id=item.knowledge_id,
        source_id=item.source.source_id,
        source_type=item.source.source_type,
        source_title=item.source.title,
        publisher=item.source.publisher,
        url=item.source.url,
        source_version=item.source.version,
        knowledge_version=item.version,
        trust_level=item.source.trust_level,
    )

