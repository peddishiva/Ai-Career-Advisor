"""Phase 3C service integration and deterministic preservation tests."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from ai.contracts import AITaskType, AIResponseStatus
from ai.orchestrator import AIOrchestrator
from ai.provider import MockAIProvider, NullAIProvider
from services.ai_enrichment_service import AIEnrichmentService, AIEnrichmentError
from test_ai_context_builder import TestAIContextBuilder


class _FakeJdxrService:
    def __init__(self):
        self.sources = {
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa": {
                "resume_id": "resume-a",
                "jd_id": "jd-a",
                "parsed_resume": {"skills": ["Python"], "experience": []},
                "parsed_jd": {"job_title": "Software Engineer", "required_skills": ["Python"]},
                "deterministic_result": {
                    "score": 81,
                    "readiness": "HIGH",
                    "critical_gaps": [],
                },
            },
            "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb": {
                "resume_id": "resume-b",
                "jd_id": "jd-b",
                "parsed_resume": {"skills": ["Excel"], "experience": []},
                "parsed_jd": {"job_title": "Data Analyst", "required_skills": ["Excel"]},
                "deterministic_result": {
                    "score": 34,
                    "readiness": "LOW",
                    "critical_gaps": ["SQL"],
                },
            },
        }

    def get_ai_source(self, session_id):
        if session_id not in self.sources:
            raise AIEnrichmentError(404, "session_not_found", "Session not found.")
        return self.sources[session_id]


class TestPhase3CService(unittest.TestCase):
    def _service(self, analysis_dir):
        return AIEnrichmentService(
            analysis_dir=analysis_dir,
            orchestrator=AIOrchestrator(provider=MockAIProvider(), enabled=True),
        )

    def test_resume_analysis_uses_retrieval_and_preserves_deterministic_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            analysis_dir = Path(temp_dir)
            file_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            deterministic = {
                "metadata": {"file_id": file_id, "filename": "resume.pdf"},
                "overall_insights": {"fit_score": 82},
                "metrics": {"skill_coverage": 74},
                "role_matches": [{"title": "Software Engineer", "match": 88}],
            }
            stored = {
                **deterministic,
                "parsed_resume": {
                    "skills": ["Python"],
                    "experience": [{"title": "Engineer", "company": "Example", "date": "2022 - Present"}],
                    "projects": [],
                    "education": [],
                    "certifications": [],
                },
            }
            (analysis_dir / f"{file_id}.json").write_text(json.dumps(stored), encoding="utf-8")

            service = self._service(analysis_dir)
            first = service.enrich_resume(file_id, AITaskType.RESUME_CAREER_GUIDANCE)
            second = service.enrich_resume(file_id, AITaskType.RESUME_CAREER_GUIDANCE)

            self.assertEqual(AIResponseStatus.COMPLETE, first.ai_status)
            self.assertEqual(deterministic, first.deterministic_result)
            self.assertEqual(first.context_hash, second.context_hash)
            self.assertEqual(first.deterministic_result, second.deterministic_result)
            self.assertIsNotNone(first.ai)
            self.assertTrue(first.ai.knowledge_references)
            json.dumps(first.model_dump(mode="json"))

    def test_disabled_ai_returns_deterministic_result_without_provider_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            deterministic = {"overall_insights": {"fit_score": 61}}
            stored = {
                **deterministic,
                "parsed_resume": {"skills": ["Python"], "experience": []},
            }
            path = Path(temp_dir) / f"{file_id}.json"
            path.write_text(json.dumps(stored), encoding="utf-8")
            service = AIEnrichmentService(
                analysis_dir=temp_dir,
                orchestrator=AIOrchestrator(provider=NullAIProvider(), enabled=False),
            )
            result = service.enrich_resume(file_id, AITaskType.RESUME_EXPLANATION)
            self.assertEqual(AIResponseStatus.DISABLED, result.ai_status)
            self.assertIsNone(result.ai)
            self.assertEqual(deterministic, result.deterministic_result)

    def test_jdxr_isolation_keeps_contexts_and_results_separate(self):
        fake_sessions = _FakeJdxrService()
        service = AIEnrichmentService(
            orchestrator=AIOrchestrator(provider=MockAIProvider(), enabled=True),
            jdxr_session_service=fake_sessions,
        )
        first = service.enrich_jdxr(
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            AITaskType.JDXR_MATCH_EXPLANATION,
        )
        second = service.enrich_jdxr(
            "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            AITaskType.JDXR_MATCH_EXPLANATION,
        )
        self.assertNotEqual(first.context_hash, second.context_hash)
        self.assertNotEqual(first.deterministic_result, second.deterministic_result)
        self.assertEqual(81, first.deterministic_result["score"])
        self.assertEqual(34, second.deterministic_result["score"])

    def test_missing_resume_analysis_is_a_controlled_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(AIEnrichmentError) as error:
                self._service(temp_dir).enrich_resume(
                    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    AITaskType.RESUME_EXPLANATION,
                )
            self.assertEqual(404, error.exception.status_code)

    def test_context_too_large_preserves_deterministic_result(self):
        source = TestAIContextBuilder()._resume_input()
        knowledge = [
            {
                "knowledge_id": f"SKILL-PYTHON-{index:03d}",
                "title": "Python",
                "category": "skill",
                "content": "x" * 4_000,
                "source_id": "PYTHON-OFFICIAL",
                "source_title": "Python Documentation",
                "publisher": "Python Software Foundation",
                "url": "https://docs.python.org/3/",
                "source_version": "1.0.0",
                "knowledge_version": "1.0.0",
                "trust_level": "high",
            }
            for index in range(1, 6)
        ]
        deterministic = {"overall_insights": {"fit_score": 42}}
        result = AIOrchestrator(provider=MockAIProvider(), enabled=True).enrich(
            source,
            deterministic,
            retrieved_knowledge=knowledge,
        )
        self.assertEqual(AIResponseStatus.UNAVAILABLE, result.ai_status)
        self.assertEqual("context_too_large", result.error_code)
        self.assertEqual(deterministic, result.deterministic_result)


if __name__ == "__main__":
    unittest.main()
