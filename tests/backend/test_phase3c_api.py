"""Phase 3C API boundary tests."""

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from ai.contracts import AITaskType
from ai.orchestrator import AIOrchestrator
from ai.provider import MockAIProvider
from routes import analysis as analysis_route
from routes import jdxr as jdxr_route
from services.ai_enrichment_service import AIEnrichmentService
from test_phase3c_service import _FakeJdxrService


class TestPhase3CApi(unittest.TestCase):
    def test_phase3c_routes_are_registered(self):
        from main import app

        paths = app.openapi().get("paths", {})
        self.assertIn("/api/analysis/ai", paths)
        self.assertIn("/api/jdxr/session/{session_id}/ai", paths)

    def test_resume_ai_endpoint_returns_separate_deterministic_and_ai_payloads(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            stored = {
                "metadata": {"file_id": file_id},
                "overall_insights": {"fit_score": 80},
                "parsed_resume": {"skills": ["Python"], "experience": []},
            }
            (Path(temp_dir) / f"{file_id}.json").write_text(json.dumps(stored), encoding="utf-8")
            service = AIEnrichmentService(
                analysis_dir=temp_dir,
                orchestrator=AIOrchestrator(provider=MockAIProvider(), enabled=True),
            )
            previous = analysis_route.ai_enrichment_service
            analysis_route.ai_enrichment_service = service
            try:
                response = asyncio.run(
                    analysis_route.generate_analysis_ai(
                        file_id=file_id,
                        request=analysis_route.AIAnalysisRequest(task=AITaskType.RESUME_EXPLANATION),
                    )
                )
            finally:
                analysis_route.ai_enrichment_service = previous
            payload = json.loads(response.body.decode("utf-8"))
            self.assertEqual(200, response.status_code, payload)
            self.assertEqual(80, payload["deterministic_result"]["overall_insights"]["fit_score"])
            self.assertEqual("complete", payload["ai_status"])
            self.assertNotIn("parsed_resume", payload["deterministic_result"])

    def test_jdxr_ai_endpoint_uses_only_the_selected_session(self):
        fake_sessions = _FakeJdxrService()
        service = AIEnrichmentService(
            orchestrator=AIOrchestrator(provider=MockAIProvider(), enabled=True),
        )
        previous_session_service = jdxr_route.jdxr_session_service
        previous_ai_service = jdxr_route.ai_enrichment_service
        jdxr_route.jdxr_session_service = fake_sessions
        jdxr_route.ai_enrichment_service = service
        try:
            response = asyncio.run(
                jdxr_route.generate_jdxr_ai(
                    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    jdxr_route.JdxrAIRequest(task=AITaskType.JDXR_MATCH_EXPLANATION),
                )
            )
        finally:
            jdxr_route.jdxr_session_service = previous_session_service
            jdxr_route.ai_enrichment_service = previous_ai_service
        payload = json.loads(response.body.decode("utf-8"))
        self.assertEqual(200, response.status_code, payload)
        self.assertEqual(81, payload["deterministic_result"]["score"])
        self.assertEqual("complete", payload["ai_status"])


if __name__ == "__main__":
    unittest.main()
