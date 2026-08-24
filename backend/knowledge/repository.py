"""Read-only repository abstraction for the curated knowledge catalog."""

from typing import Iterable, List, Optional, Protocol, Sequence, runtime_checkable

from config.knowledge_config import KNOWLEDGE_BASE_VERSION, TRUST_RANK

from .models import (
    KnowledgeCategory,
    KnowledgeHealth,
    KnowledgeItem,
    KnowledgeStatus,
    TrustLevel,
)
from .text_utils import canonical_role_references, canonical_skill_reference, normalized_content_key


class KnowledgeRepositoryError(ValueError):
    """Raised when a catalog violates repository invariants."""


@runtime_checkable
class KnowledgeRepository(Protocol):
    def get(self, knowledge_id: str) -> Optional[KnowledgeItem]: ...

    def list(
        self,
        category: Optional[KnowledgeCategory] = None,
        minimum_trust: TrustLevel = TrustLevel.LOW,
        include_inactive: bool = False,
    ) -> List[KnowledgeItem]: ...

    def search_metadata(
        self,
        category: Optional[KnowledgeCategory] = None,
        skills: Sequence[str] = (),
        roles: Sequence[str] = (),
        minimum_trust: TrustLevel = TrustLevel.LOW,
    ) -> List[KnowledgeItem]: ...

    def get_by_role(self, role: str, minimum_trust: TrustLevel = TrustLevel.LOW) -> List[KnowledgeItem]: ...

    def get_by_skill(self, skill: str, minimum_trust: TrustLevel = TrustLevel.LOW) -> List[KnowledgeItem]: ...

    def version(self) -> str: ...

    def health(self) -> KnowledgeHealth: ...


class InMemoryKnowledgeRepository:
    """Deterministic, versioned repository backed by immutable Pydantic items."""

    def __init__(
        self,
        items: Iterable[KnowledgeItem],
        knowledge_base_version: str = KNOWLEDGE_BASE_VERSION,
    ):
        self._version = knowledge_base_version
        self._items = {}
        content_owners = {}
        for item in items:
            if not isinstance(item, KnowledgeItem):
                raise KnowledgeRepositoryError("repository accepts KnowledgeItem instances only")
            if item.knowledge_id in self._items:
                raise KnowledgeRepositoryError(f"duplicate knowledge_id: {item.knowledge_id}")
            content_key = normalized_content_key(item.content)
            if content_key in content_owners:
                raise KnowledgeRepositoryError(
                    f"duplicate knowledge content: {content_owners[content_key]} and {item.knowledge_id}"
                )
            self._items[item.knowledge_id] = item
            content_owners[content_key] = item.knowledge_id

    def get(self, knowledge_id: str) -> Optional[KnowledgeItem]:
        return self._items.get(knowledge_id)

    def list(
        self,
        category: Optional[KnowledgeCategory] = None,
        minimum_trust: TrustLevel = TrustLevel.LOW,
        include_inactive: bool = False,
    ) -> List[KnowledgeItem]:
        category = KnowledgeCategory(category) if category is not None else None
        return [
            item
            for item in sorted(self._items.values(), key=lambda value: value.knowledge_id)
            if (category is None or item.category is category)
            and (include_inactive or item.status is KnowledgeStatus.ACTIVE)
            and self._trust_allowed(item, minimum_trust)
        ]

    def search_metadata(
        self,
        category: Optional[KnowledgeCategory] = None,
        skills: Sequence[str] = (),
        roles: Sequence[str] = (),
        minimum_trust: TrustLevel = TrustLevel.LOW,
    ) -> List[KnowledgeItem]:
        requested_skills = {canonical_skill_reference(skill) for skill in skills}
        requested_roles = set(canonical_role_references(roles))
        items = self.list(category=category, minimum_trust=minimum_trust)
        return [
            item
            for item in items
            if (not requested_skills or requested_skills.intersection(self._item_skills(item)))
            and (not requested_roles or requested_roles.intersection(set(item.roles)))
        ]

    def get_by_role(self, role: str, minimum_trust: TrustLevel = TrustLevel.LOW) -> List[KnowledgeItem]:
        return self.search_metadata(roles=[role], minimum_trust=minimum_trust)

    def get_by_skill(self, skill: str, minimum_trust: TrustLevel = TrustLevel.LOW) -> List[KnowledgeItem]:
        return self.search_metadata(skills=[skill], minimum_trust=minimum_trust)

    def version(self) -> str:
        return self._version

    def health(self) -> KnowledgeHealth:
        return KnowledgeHealth(
            status="healthy",
            knowledge_base_version=self._version,
            item_count=len(self._items),
        )

    def _trust_allowed(self, item: KnowledgeItem, minimum_trust: TrustLevel) -> bool:
        return TRUST_RANK[item.source.trust_level.value] >= TRUST_RANK[minimum_trust.value]

    def _item_skills(self, item: KnowledgeItem) -> set[str]:
        skills = set(item.related_skills)
        if item.category is KnowledgeCategory.SKILL:
            try:
                skills.add(canonical_skill_reference(item.title))
            except ValueError:
                pass
        return skills

