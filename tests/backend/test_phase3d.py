"""Phase 3D deterministic improvement, grounding, API, and isolation tests."""

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from ai.context_builder import AIContextBuilder
from ai.contracts import (
    AITaskType,
    AIResponse,
    AIResponseStatus,
)
from ai.improvement_facts import ImprovementFactsBuilder
from ai.orchestrator import AIOrchestrator
from ai.provider import MockAIProvider, NullAIProvider
from ai.response_validator import GroundingValidationError, AIResponseValidator
from routes import analysis as analysis_route
from routes import jdxr as jdxr_route
from services.ai_enrichment_service import AIEnrichmentError, AIEnrichmentService


def resume_data(skills=None, project_description="Built a Python API with MySQL."):
    skills = skills or ["Python"]
    return {
        "skills": skills,
        "section_evidence": {"skills_section": skills, "experience_skills": [], "project_skills": skills},
        "experience": [],
        "projects": [{"title": "Career Advisor", "description": project_description, "technologies": ["Python", "MySQL"]}],
        "education": [{"degree": "B.Tech", "field": "Computer Science"}],
        "certifications": [],
    }


def software_analysis(missing_required=None):
    return {
        "overall_insights": {"fit_score": 72},
        "metrics": {"skill_coverage": 48},
        "role_matches": [{
            "title": "Software Engineer",
            "match": 72,
            "missing_required_skills": missing_required or ["REST APIs"],
            "missing_preferred_skills": ["Docker"],
        }],
    }


class TestPhase3DImprovementFacts(unittest.TestCase):
    def test_skill_strength_and_metric_status_are_deterministic(self):
        facts = ImprovementFactsBuilder().build_resume(resume_data(), software_analysis())
        python = next(item for item in facts["skills"] if item["skill"] == "Python")
        self.assertEqual("PROJECT_EVIDENCE", python["evidence_strength"])
        self.assertEqual("NO_METRIC_FOUND", facts["projects"][0]["metric_status"])
        self.assertIn("RESUME-PROJECT-001", python["evidence_reference_ids"])

    def test_missing_jd_skill_is_learning_action_not_resume_fact(self):
        parsed_jd = {
            "job_title": "Cloud Engineer",
            "required_skills": ["Kubernetes"],
            "preferred_skills": [],
            "education_requirements": [],
            "required_eligibility_requirements": [],
            "preferred_eligibility_requirements": [],
        }
        match = {
            "required_skills": {"matched": [], "partial": [], "missing": [{"skill": "Kubernetes"}]},
            "preferred_skills": {"matched": [], "partial": [], "missing": []},
            "education_alignment": {"status": "not_required", "requirements": []},
            "eligibility_alignment": {"status": "not_required", "requirements": []},
            "project_alignment": {},
            "experience_alignment": {},
        }
        facts = ImprovementFactsBuilder().build_jdxr(resume_data(), parsed_jd, match)
        item = next(item for item in facts["opportunities"] if "Kubernetes" in item["title"])
        self.assertEqual("LEARNING_ACTION", item["fact_status"])
        self.assertNotIn("Add Kubernetes to your resume", item["recommendation"])

    def test_related_api_wording_is_evidence_visibility_not_missing_skill(self):
        parsed_jd = {
            "job_title": "Software Engineer",
            "required_skills": ["REST APIs"],
            "preferred_skills": [],
            "education_requirements": [],
            "required_eligibility_requirements": [],
            "preferred_eligibility_requirements": [],
        }
        match = {
            "required_skills": {"matched": [], "partial": [], "missing": [{"skill": "REST APIs"}]},
            "preferred_skills": {"matched": [], "partial": [], "missing": []},
            "education_alignment": {"status": "not_required", "requirements": []},
            "eligibility_alignment": {"status": "not_required", "requirements": []},
            "project_alignment": {},
            "experience_alignment": {},
        }
        facts = ImprovementFactsBuilder().build_jdxr(
            resume_data(project_description="Built a Python API with MySQL."), parsed_jd, match
        )
        item = next(item for item in facts["opportunities"] if "REST APIs" in item["title"])
        self.assertEqual("SKILL_EVIDENCE", item["category"])
        self.assertEqual("INSUFFICIENT_EVIDENCE", item["fact_status"])

    def test_matched_education_does_not_create_education_addition(self):
        parsed_jd = {
            "job_title": "Software Engineer",
            "required_skills": ["Python"],
            "preferred_skills": [],
            "education_requirements": [{"raw_text": "Bachelor's CSE", "degree_level": ["bachelor"], "fields": ["computer science"]}],
            "required_eligibility_requirements": [],
            "preferred_eligibility_requirements": [],
        }
        match = {
            "required_skills": {"matched": [{"skill": "Python"}], "partial": [], "missing": []},
            "preferred_skills": {"matched": [], "partial": [], "missing": []},
            "education_alignment": {"status": "aligned", "requirements": [{"status": "aligned"}]},
            "eligibility_alignment": {"status": "not_required", "requirements": []},
            "project_alignment": {},
            "experience_alignment": {},
        }
        facts = ImprovementFactsBuilder().build_jdxr(resume_data(), parsed_jd, match)
        self.assertFalse(any(item["category"] == "EDUCATION_PRESENTATION" for item in facts["opportunities"]))

    def test_eligibility_gap_is_a_blocker_not_a_resume_edit(self):
        parsed_jd = {
            "job_title": "Accountant",
            "required_skills": [],
            "preferred_skills": [],
            "education_requirements": [],
            "required_eligibility_requirements": [{"text": "CA/IPCC", "requirement_type": "required"}],
            "preferred_eligibility_requirements": [],
        }
        match = {
            "required_skills": {"matched": [], "partial": [], "missing": []},
            "preferred_skills": {"matched": [], "partial": [], "missing": []},
            "education_alignment": {"status": "not_required", "requirements": []},
            "eligibility_alignment": {"status": "missing", "requirements": [{"requirement": "CA/IPCC", "status": "missing"}]},
            "project_alignment": {},
            "experience_alignment": {},
        }
        facts = ImprovementFactsBuilder().build_jdxr(resume_data(), parsed_jd, match)
        blocker = next(item for item in facts["opportunities"] if item["improvement_id"] == "IMPROVEMENT-JDXR-ELIGIBILITY-BLOCKER")
        self.assertEqual("CRITICAL", blocker["priority"])
        self.assertIn("Do not add", blocker["recommendation"])


class _FakeJdxrService:
    def __init__(self):
        self.sources = {
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa": {
                "resume_id": "resume-a",
                "jd_id": "jd-a",
                "parsed_resume": resume_data(),
                "parsed_jd": {
                    "job_title": "Cloud Engineer",
                    "required_skills": ["Kubernetes"],
                    "preferred_skills": [],
                    "education_requirements": [],
                    "required_eligibility_requirements": [],
                    "preferred_eligibility_requirements": [],
                },
                "deterministic_result": {
                    "score": 42,
                    "readiness": "LOW",
                    "critical_gaps": ["Kubernetes"],
                    "required_skills": {"matched": [], "partial": [], "missing": [{"skill": "Kubernetes"}]},
                    "preferred_skills": {"matched": [], "partial": [], "missing": []},
                    "education_alignment": {"status": "not_required", "requirements": []},
                    "eligibility_alignment": {"status": "not_required", "requirements": []},
                    "project_alignment": {},
                    "experience_alignment": {},
                },
            }
        }

    def get_ai_source(self, session_id):
        if session_id not in self.sources:
            raise AIEnrichmentError(404, "session_not_found", "Session not found.")
        return self.sources[session_id]


class TestPhase3DService(unittest.TestCase):
    def test_resume_improvements_preserve_deterministic_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            deterministic = {**software_analysis(), "metadata": {"file_id": file_id}}
            stored = {**deterministic, "parsed_resume": resume_data()}
            (Path(temp_dir) / f"{file_id}.json").write_text(json.dumps(stored), encoding="utf-8")
            service = AIEnrichmentService(
                analysis_dir=temp_dir,
                orchestrator=AIOrchestrator(provider=MockAIProvider(), enabled=True),
            )
            result = service.enrich_resume_improvements(file_id)
            self.assertEqual(AIResponseStatus.COMPLETE, result.ai_status)
            self.assertEqual(deterministic, result.deterministic_result)
            self.assertTrue(result.ai.improvements)
            json.dumps(result.model_dump(mode="json"))

    def test_jdxr_improvements_are_session_scoped(self):
        fake = _FakeJdxrService()
        service = AIEnrichmentService(
            orchestrator=AIOrchestrator(provider=MockAIProvider(), enabled=True),
            jdxr_session_service=fake,
        )
        result = service.enrich_jdxr_improvements("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        self.assertEqual(42, result.deterministic_result["score"])
        self.assertEqual(AIResponseStatus.COMPLETE, result.ai_status)
        self.assertTrue(any("Kubernetes" in item.title for item in result.ai.improvements))

    def test_disabled_provider_keeps_improvements_optional(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            stored = {"metadata": {"file_id": file_id}, "parsed_resume": resume_data()}
            (Path(temp_dir) / f"{file_id}.json").write_text(json.dumps(stored), encoding="utf-8")
            result = AIEnrichmentService(
                analysis_dir=temp_dir,
                orchestrator=AIOrchestrator(provider=NullAIProvider(), enabled=False),
            ).enrich_resume_improvements(file_id)
            self.assertEqual(AIResponseStatus.DISABLED, result.ai_status)
            self.assertIsNone(result.ai)


class TestPhase3DGrounding(unittest.TestCase):
    def test_priority_mutation_and_unknown_improvement_are_rejected(self):
        parsed_resume = resume_data()
        analysis = software_analysis()
        facts = ImprovementFactsBuilder().build_resume(parsed_resume, analysis)
        source = self._source(parsed_resume, analysis, facts)
        context = AIContextBuilder().build(source)
        expected = facts["opportunities"][0]
        item = {
            key: value for key, value in expected.items() if key != "knowledge_query"
        }
        item["priority"] = "LOW"
        item["knowledge_reference_ids"] = []
        response = AIResponse(status=AIResponseStatus.COMPLETE, improvements=[item])
        with self.assertRaises(GroundingValidationError):
            AIResponseValidator().validate(response, context)

        unknown = {
            **{key: value for key, value in expected.items() if key != "knowledge_query"},
            "improvement_id": "IMPROVEMENT-UNKNOWN-001",
            "knowledge_reference_ids": [],
        }
        with self.assertRaises(GroundingValidationError):
            AIResponseValidator().validate(
                AIResponse(status=AIResponseStatus.COMPLETE, improvements=[unknown]), context
            )

    def test_deterministic_context_and_response_are_json_serializable(self):
        parsed_resume = resume_data()
        analysis = software_analysis()
        facts = ImprovementFactsBuilder().build_resume(parsed_resume, analysis)
        source = self._source(parsed_resume, analysis, facts)
        context = AIContextBuilder().build(source)
        json.dumps(context.model_dump(mode="json"))

    def _source(self, parsed_resume, analysis, facts):
        from ai.contracts import DeterministicAIInput, FlowType
        return DeterministicAIInput(
            flow_type=FlowType.RESUME_ANALYSIS,
            session_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            resume_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            deterministic_result_hash="a" * 64,
            deterministic_facts={
                "parsed_resume": parsed_resume,
                "analysis": analysis,
                "improvement_facts": facts,
            },
            task=AITaskType.RESUME_IMPROVEMENT,
        )


class TestPhase3DApi(unittest.TestCase):
    def test_improvement_routes_are_registered(self):
        from main import app
        paths = app.openapi().get("paths", {})
        self.assertIn("/api/analysis/ai/improvements", paths)
        self.assertIn("/api/jdxr/session/{session_id}/ai/improvements", paths)

    def test_resume_improvement_requires_explicit_file_id(self):
        with self.assertRaises(Exception):
            asyncio.run(analysis_route.generate_analysis_improvements())

    def test_resume_improvement_endpoint_returns_separate_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            stored = {
                **software_analysis(),
                "metadata": {"file_id": file_id},
                "parsed_resume": resume_data(),
            }
            (Path(temp_dir) / f"{file_id}.json").write_text(json.dumps(stored), encoding="utf-8")
            previous = analysis_route.ai_enrichment_service
            analysis_route.ai_enrichment_service = AIEnrichmentService(
                analysis_dir=temp_dir,
                orchestrator=AIOrchestrator(provider=MockAIProvider(), enabled=True),
            )
            try:
                response = asyncio.run(analysis_route.generate_analysis_improvements(file_id))
            finally:
                analysis_route.ai_enrichment_service = previous
            payload = json.loads(response.body.decode("utf-8"))
            self.assertEqual(200, response.status_code, payload)
            self.assertEqual(72, payload["deterministic_result"]["overall_insights"]["fit_score"])
            self.assertEqual("complete", payload["ai_status"])

    def test_jdxr_improvement_uses_selected_session_service(self):
        previous_service = jdxr_route.jdxr_session_service
        previous_ai = jdxr_route.ai_enrichment_service
        jdxr_route.jdxr_session_service = _FakeJdxrService()
        jdxr_route.ai_enrichment_service = AIEnrichmentService(
            orchestrator=AIOrchestrator(provider=MockAIProvider(), enabled=True),
        )
        try:
            response = asyncio.run(
                jdxr_route.generate_jdxr_improvements("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            )
        finally:
            jdxr_route.jdxr_session_service = previous_service
            jdxr_route.ai_enrichment_service = previous_ai
        payload = json.loads(response.body.decode("utf-8"))
        self.assertEqual(200, response.status_code, payload)
        self.assertEqual(42, payload["deterministic_result"]["score"])


if __name__ == "__main__":
    unittest.main()
