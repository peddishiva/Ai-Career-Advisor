"""
Tests for deterministic Phase 2B resume-to-JD matching.
"""

import json
import sys
from pathlib import Path
from datetime import date
import unittest

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
tests_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(tests_path))

from job_match_fixtures import (
    ALIAS_JD,
    ALIAS_RESUME,
    BACKEND_EXPERIENCE_JD,
    CA_FINANCIAL_RESUME,
    CERTIFICATION_JD,
    COMMERCE_EDUCATION_RESUME,
    DATA_ANALYST_MISMATCH_RESUME,
    EDUCATION_JD,
    ELIGIBILITY_JD,
    FINANCIAL_ANALYST_RESUME,
    LICENSE_JD,
    LICENSE_RESUME,
    MISSING_DATE_EXPERIENCE_RESUME,
    MEMBERSHIP_JD,
    MEMBERSHIP_RESUME,
    PREFERRED_QUALIFICATION_JD,
    PREFERRED_ONLY_JD,
    PREFERRED_TRAP_JD,
    PREFERRED_TRAP_RESUME,
    PROJECT_ONLY_BACKEND_RESUME,
    PROJECT_ONLY_ELIGIBILITY_RESUME,
    REQUIRED_ONLY_JD,
    RESPONSIBILITIES_ONLY_JD,
    SKILLS_ONLY_AWS_RESUME,
    SOFTWARE_ENGINEER_JD,
    SOFTWARE_ENGINEER_RESUME,
    SDE_FIDELITY_RESUME,
    TRAINEE_JD,
    TRAINEE_RESUME,
    parsed_jd,
    parsed_resume,
)
from services.job_match_service import JobMatchService
from job_description_fixtures import SDE_FIDELITY_JD


class TestJobMatchService(unittest.TestCase):
    """Validate deterministic, explainable resume-to-JD matching."""

    def setUp(self):
        self.service = JobMatchService(reference_year=2026)

    def test_software_engineer_strong_match_is_high(self):
        result = self.service.match(parsed_resume(SOFTWARE_ENGINEER_RESUME), parsed_jd(SOFTWARE_ENGINEER_JD))

        self.assertGreaterEqual(result["score"], 75)
        self.assertEqual(result["readiness"], "HIGH")
        self.assertEqual(result["required_skills"]["missing"], [])
        self.assertEqual(result["experience_alignment"]["status"], "met")
        self.assertEqual(result["education_alignment"]["status"], "aligned")
        self.assertTrue(any(item["type"] == "education" for item in result["resume_alignment"]))

    def test_strong_mismatch_is_low_with_critical_gaps(self):
        result = self.service.match(parsed_resume(DATA_ANALYST_MISMATCH_RESUME), parsed_jd(SOFTWARE_ENGINEER_JD))

        self.assertLess(result["score"], 50)
        self.assertEqual(result["readiness"], "LOW")
        missing_required = [item["skill"] for item in result["required_skills"]["missing"]]
        self.assertIn("Python", missing_required)
        self.assertIn("REST APIs", missing_required)
        self.assertTrue(any(gap["type"] == "required_skill" for gap in result["critical_gaps"]))

    def test_required_skill_deficit_constrains_preferred_trap(self):
        result = self.service.match(parsed_resume(PREFERRED_TRAP_RESUME), parsed_jd(PREFERRED_TRAP_JD))

        missing_required = [item["skill"] for item in result["required_skills"]["missing"]]
        self.assertIn("SQL", missing_required)
        self.assertIn("Docker", missing_required)
        self.assertGreaterEqual(len(result["preferred_skills"]["matched"]), 2)
        self.assertTrue(result["score_constraint"]["applied"])
        self.assertLess(result["score"], 70)

    def test_project_evidence_does_not_satisfy_professional_experience_years(self):
        result = self.service.match(parsed_resume(PROJECT_ONLY_BACKEND_RESUME), parsed_jd(BACKEND_EXPERIENCE_JD))

        self.assertGreater(result["project_alignment"]["score"], 0)
        self.assertIn(result["experience_alignment"]["status"], {"unmet", "insufficient_evidence"})
        self.assertIsNone(result["experience_alignment"]["candidate_years"])
        self.assertTrue(any(gap["type"] == "experience" for gap in result["critical_gaps"]))

    def test_education_match_aligns_degree_and_related_field(self):
        result = self.service.match(parsed_resume(SOFTWARE_ENGINEER_RESUME), parsed_jd(EDUCATION_JD))

        self.assertEqual(result["education_alignment"]["status"], "aligned")
        self.assertEqual(result["education_alignment"]["score"], 100)

    def test_education_mismatch_is_not_aligned(self):
        result = self.service.match(parsed_resume(COMMERCE_EDUCATION_RESUME), parsed_jd(EDUCATION_JD))

        self.assertEqual(result["education_alignment"]["status"], "not_aligned")
        self.assertEqual(result["education_alignment"]["score"], 0)
        self.assertTrue(any(gap["type"] == "education" for gap in result["critical_gaps"]))

    def test_financial_analyst_requirements_are_not_mapped_to_education(self):
        result = self.service.match(parsed_resume(FINANCIAL_ANALYST_RESUME), parsed_jd(ELIGIBILITY_JD))

        self.assertEqual("not_required", result["education_alignment"]["status"])
        self.assertEqual([], result["education_alignment"]["requirements"])

    def test_required_availability_and_domain_knowledge_are_critical_gaps(self):
        result = self.service.match(
            parsed_resume(FINANCIAL_ANALYST_RESUME),
            parsed_jd("""
            Financial Analyst Intern
            Company: Example Finance

            Basic Qualifications
            - Pursuing CA.
            - Available to intern for 12-18 months.
            - Good knowledge of accounting and finance.
            """),
        )

        self.assertEqual("not_required", result["education_alignment"]["status"])
        self.assertEqual("missing", result["availability_alignment"]["status"])
        self.assertEqual("missing", result["qualification_alignment"]["status"])
        gap_types = {gap["type"] for gap in result["critical_gaps"]}
        self.assertIn("availability", gap_types)
        self.assertIn("domain_knowledge", gap_types)

    def test_preferred_certification_matches_without_critical_gap(self):
        result = self.service.match(parsed_resume(SOFTWARE_ENGINEER_RESUME), parsed_jd(CERTIFICATION_JD))

        self.assertEqual(result["certification_alignment"]["status"], "matched")
        self.assertEqual(result["certification_alignment"]["score"], 100)
        self.assertFalse(any(gap["type"] == "certification" for gap in result["critical_gaps"]))

    def test_required_eligibility_gaps_are_critical_and_project_evidence_is_ignored(self):
        result = self.service.match(parsed_resume(FINANCIAL_ANALYST_RESUME), parsed_jd(ELIGIBILITY_JD))

        self.assertEqual(result["eligibility_alignment"]["status"], "missing")
        self.assertEqual(len(result["eligibility_alignment"]["requirements"]), 3)
        self.assertTrue(all(item["importance"] == "critical" for item in result["eligibility_alignment"]["requirements"]))
        self.assertEqual(len([gap for gap in result["critical_gaps"] if gap["type"] == "eligibility"]), 3)

        project_result = self.service.match(parsed_resume(PROJECT_ONLY_ELIGIBILITY_RESUME), parsed_jd(ELIGIBILITY_JD))
        self.assertEqual(project_result["eligibility_alignment"]["status"], "missing")

    def test_matching_qualification_evidence_is_explainable(self):
        result = self.service.match(parsed_resume(CA_FINANCIAL_RESUME), parsed_jd(ELIGIBILITY_JD))

        self.assertEqual(result["eligibility_alignment"]["status"], "matched")
        self.assertTrue(all(item["status"] == "matched" for item in result["eligibility_alignment"]["requirements"]))
        self.assertEqual([gap for gap in result["critical_gaps"] if gap["type"] == "eligibility"], [])

    def test_generic_license_membership_and_trainee_eligibility(self):
        license_result = self.service.match(parsed_resume(LICENSE_RESUME), parsed_jd(LICENSE_JD))
        membership_result = self.service.match(parsed_resume(MEMBERSHIP_RESUME), parsed_jd(MEMBERSHIP_JD))
        trainee_result = self.service.match(parsed_resume(TRAINEE_RESUME), parsed_jd(TRAINEE_JD))

        self.assertEqual(license_result["eligibility_alignment"]["status"], "matched")
        self.assertEqual(membership_result["eligibility_alignment"]["status"], "matched")
        self.assertEqual(trainee_result["eligibility_alignment"]["status"], "matched")

    def test_preferred_qualification_gap_is_non_critical(self):
        result = self.service.match(parsed_resume(FINANCIAL_ANALYST_RESUME), parsed_jd(PREFERRED_QUALIFICATION_JD))

        self.assertEqual(result["eligibility_alignment"]["status"], "missing")
        self.assertTrue(all(item["importance"] == "non_critical" for item in result["eligibility_alignment"]["requirements"]))
        self.assertTrue(any(gap["type"] == "preferred_eligibility" for gap in result["non_critical_gaps"]))
        self.assertFalse(any(gap["type"] == "eligibility" for gap in result["critical_gaps"]))

    def test_eligibility_output_is_deterministic_for_ten_runs(self):
        resume_data = parsed_resume(CA_FINANCIAL_RESUME)
        jd_data = parsed_jd(ELIGIBILITY_JD)
        results = [self.service.match(resume_data, jd_data) for _ in range(10)]

        self.assertTrue(all(result == results[0] for result in results))

    def test_alias_skills_canonicalize_and_match(self):
        result = self.service.match(parsed_resume(ALIAS_RESUME), parsed_jd(ALIAS_JD))

        matched = [item["skill"] for item in result["required_skills"]["matched"]]
        missing = [item["skill"] for item in result["required_skills"]["missing"]]

        self.assertIn("JavaScript", matched)
        self.assertIn("React", matched)
        self.assertIn("PostgreSQL", matched)
        self.assertIn("Kubernetes", matched)
        self.assertEqual([], missing)

    def test_skill_listed_only_is_partial(self):
        result = self.service.match(
            parsed_resume(SKILLS_ONLY_AWS_RESUME),
            {
                "required_skills": ["AWS"],
                "preferred_skills": [],
                "experience_requirements": [],
                "education_requirements": [],
                "certifications": [],
                "responsibilities": [],
            },
        )

        self.assertEqual(result["required_skills"]["partial"][0]["skill"], "AWS")
        self.assertIn("no professional or project application", result["required_skills"]["partial"][0]["reason"])

    def test_missing_experience_dates_are_insufficient_evidence(self):
        result = self.service.match(parsed_resume(MISSING_DATE_EXPERIENCE_RESUME), parsed_jd(BACKEND_EXPERIENCE_JD))

        self.assertEqual(result["experience_alignment"]["status"], "insufficient_evidence")
        self.assertIsNone(result["experience_alignment"]["candidate_years"])

    def test_reference_date_controls_present_experience_duration(self):
        resume_data = {
            "skills": ["Python"],
            "section_evidence": {
                "skills_section": ["Python"],
                "experience_skills": ["Python"],
                "project_skills": [],
                "all_skill_frequencies": {"Python": 2},
            },
            "experience": [
                {
                    "title": "Backend Developer",
                    "company": "Sample Services",
                    "date": "2024 - Present",
                    "description": "Developed backend services using Python.",
                    "skills_applied": ["Python"],
                }
            ],
            "education": [],
            "projects": [],
            "certifications": [],
        }
        jd_data = {
            "required_skills": ["Python"],
            "preferred_skills": [],
            "experience_requirements": [
                {
                    "years": 2,
                    "domain": "backend",
                    "text": "2+ years of backend experience.",
                    "requirement_type": "required",
                }
            ],
            "education_requirements": [],
            "certifications": [],
            "responsibilities": [],
        }

        fixed_year_result = JobMatchService(reference_year=2026).match(resume_data, jd_data)
        fixed_date_result = JobMatchService(reference_date=date(2025, 1, 15)).match(resume_data, jd_data)

        self.assertEqual(date.today().year, JobMatchService().reference_year)
        self.assertEqual(2.0, fixed_year_result["experience_alignment"]["candidate_years"])
        self.assertEqual("met", fixed_year_result["experience_alignment"]["status"])
        self.assertEqual(1.0, fixed_date_result["experience_alignment"]["candidate_years"])
        self.assertEqual("unmet", fixed_date_result["experience_alignment"]["status"])

    def test_responsibilities_only_jd_does_not_crash_or_fabricate_skills(self):
        result = self.service.match(parsed_resume(PROJECT_ONLY_BACKEND_RESUME), parsed_jd(RESPONSIBILITIES_ONLY_JD))

        self.assertEqual(result["required_skills"]["matched"], [])
        self.assertGreater(result["responsibility_alignment"]["score"], 0)
        self.assertEqual(result["score_constraint"]["applied"], False)

    def test_required_only_and_preferred_only_jds_are_safe(self):
        required_result = self.service.match(parsed_resume(SOFTWARE_ENGINEER_RESUME), parsed_jd(REQUIRED_ONLY_JD))
        preferred_result = self.service.match(parsed_resume(PREFERRED_TRAP_RESUME), parsed_jd(PREFERRED_ONLY_JD))

        self.assertIn("Python", [item["skill"] for item in required_result["required_skills"]["matched"]])
        self.assertEqual(required_result["preferred_skills"]["missing"], [])
        self.assertEqual(preferred_result["required_skills"]["missing"], [])
        self.assertIn("React", [item["skill"] for item in preferred_result["preferred_skills"]["matched"]])

    def test_empty_inputs_are_json_serializable_and_low(self):
        result = self.service.match({}, {})

        self.assertEqual(result["score"], 0)
        self.assertEqual(result["readiness"], "LOW")
        json.dumps(result)

    def test_determinism_for_ten_runs(self):
        resume_data = parsed_resume(SOFTWARE_ENGINEER_RESUME)
        jd_data = parsed_jd(SOFTWARE_ENGINEER_JD)
        results = [self.service.match(resume_data, jd_data) for _ in range(10)]

        self.assertTrue(all(result == results[0] for result in results))

    def test_sde_fidelity_education_projects_and_experience_range(self):
        resume = parsed_resume(SDE_FIDELITY_RESUME)
        jd = parsed_jd(SDE_FIDELITY_JD)
        result = self.service.match(resume, jd)

        self.assertEqual(len(resume["experience"]), 2)
        self.assertEqual(len(resume["projects"]), 3)
        self.assertEqual(resume["education"][0]["field"], "CSE (Artificial Intelligence and Machine Learning)")
        self.assertEqual(result["education_alignment"]["status"], "aligned")
        self.assertGreater(result["project_alignment"]["score"], 0)
        self.assertEqual(result["experience_alignment"]["requirements"][0]["required_years"], 2)
        self.assertEqual(result["experience_alignment"]["requirements"][0]["maximum_target_years"], 5)
        self.assertIn("minimum 2-year requirement", result["experience_alignment"]["requirements"][0]["reason"])
        self.assertNotIn("5+ year requirement", result["experience_alignment"]["requirements"][0]["reason"])
        capability_requirements = result["qualification_alignment"]["requirements"]
        self.assertEqual(
            next(item for item in capability_requirements if item["requirement"] == "Algorithms")["status"],
            "matched",
        )

    def test_experience_range_uses_minimum_and_does_not_reject_above_target(self):
        jd = parsed_jd("""
        Software Engineer
        Requirements
        - 2-5 years of professional software development experience.
        """)

        def result_for(date_text):
            return self.service.match(
                {
                    "skills": ["Python"],
                    "section_evidence": {"skills_section": ["Python"]},
                    "experience": [{"title": "Software Engineer", "company": "Example", "date": date_text, "description": "Built Python software.", "skills_applied": ["Python"]}],
                    "education": [],
                    "projects": [],
                    "certifications": [],
                },
                jd,
            )["experience_alignment"]

        self.assertEqual(result_for("2025")["status"], "unmet")
        self.assertEqual(result_for("2023-2026")["status"], "met")
        self.assertEqual(result_for("2020-2026")["status"], "met")


if __name__ == "__main__":
    unittest.main()
