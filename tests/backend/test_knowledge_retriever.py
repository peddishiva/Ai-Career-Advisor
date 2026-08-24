"""Deterministic retrieval and realistic scenario tests for Phase 3B."""

import json
import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from knowledge.catalog import build_default_repository  # noqa: E402
from knowledge.models import KnowledgeCategory, RetrievalQuery, TrustLevel  # noqa: E402
from knowledge.retriever import KnowledgeRetriever  # noqa: E402


class TestKnowledgeRetriever(unittest.TestCase):
    def setUp(self):
        self.retriever = KnowledgeRetriever(build_default_repository())

    def titles(self, query, **kwargs):
        return [item.title for item in self.retriever.retrieve({"query": query, **kwargs})]

    def test_exact_skill_match_ranks_first(self):
        results = self.retriever.retrieve({"query": "Python"})
        self.assertEqual(results[0].title, "Python")
        self.assertGreater(results[0].score, results[1].score)

    def test_realistic_backend_query_contains_expected_evidence(self):
        titles = self.titles("Python backend development")
        self.assertIn("Python", titles)
        self.assertIn("FastAPI", titles)
        self.assertIn("REST APIs", titles)
        self.assertIn("Software Engineer", titles)

    def test_realistic_interview_query_prioritizes_interview_topics(self):
        titles = self.titles("prepare for software engineer interview")
        self.assertIn("Data Structures and Algorithms Interview Preparation", titles)
        self.assertIn("Object-Oriented Programming Interview Preparation", titles)
        self.assertIn("SQL Interview Preparation", titles)
        self.assertIn("REST API Interview Preparation", titles)
        self.assertIn("System Design Interview Preparation", titles)

    def test_realistic_resume_query_returns_skill_and_resume_guidance(self):
        titles = self.titles("resume improvement for missing Docker evidence")
        self.assertEqual(titles[0], "Docker")
        self.assertTrue(any(title in titles for title in ["Project Evidence", "Skills Evidence", "Evidence-Based Resume Bullets"]))

    def test_realistic_data_and_cloud_queries(self):
        data_titles = self.titles("data analyst SQL Excel")
        self.assertIn("Data Analyst", data_titles[:4])
        self.assertIn("SQL", data_titles)
        self.assertIn("Excel", data_titles)

        cloud_titles = self.titles("cloud engineer AWS Kubernetes")
        self.assertIn("AWS", cloud_titles[:3])
        self.assertIn("Kubernetes", cloud_titles[:3])
        self.assertIn("DevOps / Cloud Engineer", cloud_titles[:4])

    def test_metadata_filters_and_max_results_are_enforced(self):
        results = self.retriever.retrieve(
            RetrievalQuery(
                query="",
                categories=[KnowledgeCategory.INTERVIEW_TOPIC],
                max_results=3,
            )
        )
        self.assertEqual(len(results), 3)
        self.assertTrue(all(result.category is KnowledgeCategory.INTERVIEW_TOPIC for result in results))

    def test_empty_and_unknown_queries_are_safe(self):
        self.assertEqual(self.retriever.retrieve({"query": ""}), [])
        self.assertEqual(self.retriever.retrieve({"query": "quantum pastry archaeology"}), [])

    def test_repeatability_and_json_serializability(self):
        query = {"query": "cloud engineer AWS Kubernetes", "max_results": 5}
        first = [result.model_dump(mode="json") for result in self.retriever.retrieve(query)]
        for _ in range(10):
            self.assertEqual(first, [result.model_dump(mode="json") for result in self.retriever.retrieve(query)])
        json.dumps(first)

    def test_tie_breaking_is_stable_by_category_then_knowledge_id(self):
        results = self.retriever.retrieve({"query": "interview", "max_results": 10})
        sort_keys = [
            (result.category.value, result.knowledge_id)
            for result in results
            if result.score == results[0].score
        ]
        self.assertEqual(sort_keys, sorted(sort_keys))

    def test_provenance_and_version_are_returned(self):
        result = self.retriever.retrieve({"query": "Python"})[0]
        self.assertEqual(result.source.knowledge_id, result.knowledge_id)
        self.assertEqual(result.knowledge_version, "1.0.0")
        self.assertEqual(result.source.source_id, "PYTHON-OFFICIAL")
        self.assertTrue(result.source.url.startswith("https://"))

    def test_high_trust_default_and_explicit_low_trust_filter(self):
        high_results = self.retriever.retrieve({"query": "Python", "minimum_trust": TrustLevel.HIGH})
        low_results = self.retriever.retrieve({"query": "Python", "minimum_trust": TrustLevel.LOW})
        self.assertEqual([item.model_dump(mode="json") for item in high_results], [item.model_dump(mode="json") for item in low_results])


if __name__ == "__main__":
    unittest.main()
