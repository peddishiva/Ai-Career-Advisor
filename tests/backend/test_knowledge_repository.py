"""Repository and catalog invariant tests for Phase 3B."""

import sys
import unittest
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from knowledge.catalog import build_default_repository  # noqa: E402
from knowledge.models import KnowledgeCategory, KnowledgeStatus, TrustLevel  # noqa: E402
from knowledge.repository import InMemoryKnowledgeRepository, KnowledgeRepositoryError  # noqa: E402
from test_knowledge_models import curated_source, knowledge_item  # noqa: E402


class TestKnowledgeRepository(unittest.TestCase):
    def setUp(self):
        self.repository = build_default_repository()

    def test_get_list_health_and_version(self):
        item = self.repository.get("SKILL-PYTHON-001")
        self.assertIsNotNone(item)
        self.assertEqual(self.repository.version(), "3.1.0")
        self.assertEqual(self.repository.health().item_count, 44)
        self.assertEqual(len(self.repository.list(category=KnowledgeCategory.SKILL)), 23)

    def test_metadata_filtering_role_and_skill_lookup_reuse_canonical_system(self):
        self.assertTrue(self.repository.get_by_skill("react.js"))
        role_items = self.repository.get_by_role("software-engineer")
        self.assertTrue(any(item.title == "Software Engineer" for item in role_items))
        filtered = self.repository.search_metadata(
            category=KnowledgeCategory.SKILL,
            skills=["Python"],
        )
        self.assertIn("Python", [item.title for item in filtered])
        self.assertTrue(all("Python" in self.repository._item_skills(item) for item in filtered))

    def test_inactive_items_are_not_retrievable_by_default(self):
        inactive = knowledge_item(
            knowledge_id="TEST-INACTIVE-001",
            title="Inactive React Guidance",
            category=KnowledgeCategory.RESUME_GUIDANCE,
            status=KnowledgeStatus.INACTIVE,
            content="Inactive guidance content.",
            related_skills=[],
            roles=[],
        )
        repository = InMemoryKnowledgeRepository([inactive])
        self.assertEqual(repository.list(), [])
        self.assertIsNotNone(repository.get("TEST-INACTIVE-001"))

    def test_duplicate_ids_and_duplicate_content_are_rejected(self):
        with self.assertRaises(KnowledgeRepositoryError):
            InMemoryKnowledgeRepository([knowledge_item(), knowledge_item()])

        duplicate_content = knowledge_item(
            knowledge_id="TEST-SKILL-002",
            title="Another React",
        )
        with self.assertRaises(KnowledgeRepositoryError):
            InMemoryKnowledgeRepository([knowledge_item(), duplicate_content])

    def test_medium_trust_is_excluded_by_high_filter(self):
        medium = knowledge_item(
            knowledge_id="TEST-MEDIUM-001",
            title="Medium React Guidance",
            content="Medium trust guidance content.",
            source=curated_source(source_id="TEST-MEDIUM", trust_level=TrustLevel.MEDIUM),
        )
        repository = InMemoryKnowledgeRepository([medium])
        self.assertEqual(repository.list(minimum_trust=TrustLevel.HIGH), [])
        self.assertEqual(len(repository.list(minimum_trust=TrustLevel.MEDIUM)), 1)


if __name__ == "__main__":
    unittest.main()
