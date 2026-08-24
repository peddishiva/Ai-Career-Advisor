"""Provenance and provider-independent boundary tests for Phase 3B."""

import sys
import unittest
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from knowledge.catalog import build_default_repository  # noqa: E402
from knowledge.models import SourceType, TrustLevel  # noqa: E402
from knowledge.provenance import provenance_for  # noqa: E402
from knowledge.retriever import KnowledgeRetriever  # noqa: E402


class TestKnowledgeProvenance(unittest.TestCase):
    def setUp(self):
        self.repository = build_default_repository()

    def test_provenance_preserves_item_and_source_identity(self):
        item = self.repository.get("SKILL-PYTHON-001")
        provenance = provenance_for(item)
        self.assertEqual(provenance.knowledge_id, item.knowledge_id)
        self.assertEqual(provenance.source_id, item.source.source_id)
        self.assertEqual(provenance.source_type, SourceType.OFFICIAL_DOCUMENTATION)
        self.assertEqual(provenance.knowledge_version, item.version)
        self.assertEqual(provenance.source_version, item.source.version)

    def test_curated_internal_sources_have_no_fabricated_url(self):
        role = self.repository.get("ROLE-SOFTWARE-ENGINEER-001")
        self.assertEqual(role.source.source_type, SourceType.CURATED_INTERNAL_GUIDANCE)
        self.assertIsNone(role.source.url)
        self.assertEqual(role.source.trust_level, TrustLevel.HIGH)

    def test_retriever_has_no_provider_dependency_or_network_boundary(self):
        retriever = KnowledgeRetriever(self.repository)
        self.assertFalse(hasattr(retriever, "provider"))
        self.assertEqual(retriever.retrieve({"query": "Python"})[0].source.source_id, "PYTHON-OFFICIAL")


if __name__ == "__main__":
    unittest.main()

