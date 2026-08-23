"""
Tests for deterministic Phase 2A job description parsing.
"""

import sys
from pathlib import Path
import unittest

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
tests_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(tests_path))

from job_description_fixtures import (
    DATA_ANALYST_JD,
    DEVOPS_CLOUD_JD,
    ENTRY_LEVEL_SOFTWARE_ENGINEER_JD,
    FINANCIAL_ANALYST_INTERN_JD,
    MESSY_INLINE_HEADER_JD,
    MISSING_OPTIONAL_SECTIONS_JD,
    ML_ENGINEER_JD,
    NO_EXPLICIT_REQUIREMENT_HEADERS_JD,
    PREFERRED_ONLY_JD,
    REQUIRED_ONLY_JD,
    SOFTWARE_ENGINEER_JD,
    SDE_FIDELITY_JD,
)
from services.job_description_parser import JobDescriptionParser


class TestJobDescriptionParser(unittest.TestCase):
    """Validate structured JD extraction without resume matching/scoring."""

    def setUp(self):
        self.parser = JobDescriptionParser()

    def test_software_engineer_core_fields_and_sections(self):
        data = self.parser.parse_text(SOFTWARE_ENGINEER_JD)

        self.assertEqual(data["job_title"], "Software Engineer")
        self.assertEqual(data["company"], "Clearpath Labs")
        self.assertEqual(data["location"], "Remote, United States")
        self.assertEqual(data["employment_type"], "Full-time")
        self.assertIn("responsibilities", data["sections"])
        self.assertIn("required_qualifications", data["sections"])
        self.assertIn("preferred_qualifications", data["sections"])

    def test_about_metadata_extracts_company_without_inference(self):
        explicit_data = self.parser.parse_text("""
Data Engineer
About: Example Corp
Location: Remote
Employment Type: Full-time

Requirements
- Must have Python and SQL experience.
""")
        role_data = self.parser.parse_text("""
Data Engineer
About the Role: You will build analytics pipelines.
Location: Remote
Employment Type: Full-time

Requirements
- Must have Python and SQL experience.
""")

        self.assertEqual(explicit_data["company"], "Example Corp")
        self.assertIsNone(role_data["company"])

    def test_required_and_preferred_skills_are_separated(self):
        data = self.parser.parse_text(SOFTWARE_ENGINEER_JD)

        self.assertIn("Python", data["required_skills"])
        self.assertIn("SQL", data["required_skills"])
        self.assertIn("REST APIs", data["required_skills"])
        self.assertIn("Git", data["required_skills"])
        self.assertIn("Docker", data["preferred_skills"])
        self.assertIn("AWS", data["preferred_skills"])
        self.assertIn("React", data["preferred_skills"])

    def test_experience_education_and_certification_requirements(self):
        data = self.parser.parse_text(SOFTWARE_ENGINEER_JD)

        self.assertEqual(data["experience_requirements"][0]["years"], 2)
        self.assertEqual(data["experience_requirements"][0]["domain"], "software development")
        self.assertEqual(data["education_requirements"][0]["degree_level"], ["bachelor"])
        self.assertIn("Computer Science", data["education_requirements"][0]["fields"])
        self.assertTrue(data["education_requirements"][0]["related_field_allowed"])
        self.assertEqual(data["certifications"][0]["name"], "AWS certification")
        self.assertFalse(data["certifications"][0]["required"])

    def test_explicit_eligibility_requirements_are_structured_separately(self):
        data = self.parser.parse_text(FINANCIAL_ANALYST_INTERN_JD)

        eligibility = data["required_eligibility_requirements"]
        texts = [item["text"] for item in eligibility]
        self.assertTrue(any("pursuing CA" in text for text in texts))
        self.assertTrue(any("IPCC" in text for text in texts))
        self.assertTrue(any("industrial training" in text for text in texts))
        self.assertTrue(all(item["category"] == "eligibility" for item in eligibility))
        self.assertEqual(data["education_requirements"], [])

        availability = data["required_availability_requirements"]
        self.assertTrue(any("12-18 months" in item["text"] for item in availability))

        capabilities = data["required_capability_requirements"]
        self.assertTrue(any("accounting and finance" in item["text"].lower() for item in capabilities))

    def test_skill_like_ms_excel_is_not_education(self):
        data = self.parser.parse_text("""
        Financial Analyst Intern
        Company: Example Finance

        Preferred Qualifications
        - Proficiency in MS Excel.
        - Strong communication preferred.
        """)

        self.assertEqual(data["education_requirements"], [])
        self.assertIn("Excel", data["preferred_skills"])
        self.assertTrue(all(item["category"] != "education" for item in data["preferred_qualifications"]))

    def test_responsibilities_split_sentences_and_filter_promotion(self):
        data = self.parser.parse_text("""
        Financial Analyst Intern
        Company: Example Finance

        Description
        Example Finance is a global company serving customers across many markets.

        Key Job Responsibilities
        Are you looking for an opportunity to kick-start your finance career in an exciting industry?
        The selected candidate will work with business and finance leaders to deliver financial analysis.
        The candidate will work with key stakeholders; support accounting and planning teams.
        """)

        self.assertEqual(
            data["responsibilities"],
            [
                "The selected candidate will work with business and finance leaders to deliver financial analysis.",
                "The candidate will work with key stakeholders",
                "support accounting and planning teams.",
            ],
        )
        self.assertFalse(any("global company" in item for item in data["responsibilities"]))
        self.assertFalse(any("kick-start" in item for item in data["responsibilities"]))

    def test_soft_mentions_are_not_eligibility_requirements(self):
        data = self.parser.parse_text("""
        Financial Analyst
        Company: Example Finance

        Requirements
        - Experience working with finance teams.
        - Exposure to CA processes is helpful.
        - Knowledge of accounting systems is preferred.
        - Worked with licensed professionals.
        """)

        self.assertEqual(data["required_eligibility_requirements"], [])
        self.assertEqual(data["preferred_eligibility_requirements"], [])

    def test_education_and_certification_remain_separate_categories(self):
        data = self.parser.parse_text("""
        Compliance Analyst
        Company: Example Compliance

        Requirements
        - Bachelor's degree in Accounting or Finance.
        - CPA certification required.
        - Must be registered with the relevant professional body.
        """)

        self.assertEqual(data["education_requirements"][0]["degree_level"], ["bachelor"])
        self.assertEqual(data["certifications"][0]["name"], "CPA certification")
        self.assertEqual(len(data["required_eligibility_requirements"]), 1)
        self.assertNotIn("CPA certification required.", [item["text"] for item in data["required_eligibility_requirements"]])

    def test_responsibilities_are_clean_individual_items(self):
        data = self.parser.parse_text(DATA_ANALYST_JD)

        self.assertEqual(len(data["responsibilities"]), 2)
        self.assertEqual(data["responsibilities"][0], "Analyze operational datasets with SQL and Excel.")
        self.assertEqual(data["responsibilities"][1], "Create dashboards for business stakeholders.")
        self.assertIn("Python", data["preferred_skills"])
        self.assertNotIn("Statistics", data["required_skills"])
        self.assertEqual(data["education_requirements"][0]["degree_level"], ["bachelor"])

    def test_alias_skill_normalization(self):
        data = self.parser.parse_text(DEVOPS_CLOUD_JD)

        self.assertIn("AWS", data["required_skills"])
        self.assertIn("Docker", data["required_skills"])
        self.assertIn("Linux", data["required_skills"])
        self.assertIn("Git", data["required_skills"])
        self.assertIn("Kubernetes", data["preferred_skills"])
        self.assertIn("Terraform", data["preferred_skills"])
        self.assertIn("CI/CD", data["preferred_skills"])

    def test_machine_learning_degree_and_skills(self):
        data = self.parser.parse_text(ML_ENGINEER_JD)

        self.assertEqual(data["job_title"], "Machine Learning Engineer")
        self.assertIn("Machine Learning", data["required_skills"])
        self.assertIn("Statistics", data["required_skills"])
        self.assertIn("PyTorch", data["preferred_skills"])
        self.assertIn("TensorFlow", data["preferred_skills"])
        self.assertEqual(data["experience_requirements"][0]["years"], 3)

    def test_entry_level_inline_required_and_preferred_skills(self):
        data = self.parser.parse_text(ENTRY_LEVEL_SOFTWARE_ENGINEER_JD)

        self.assertEqual(data["job_title"], "Entry-Level Software Engineer")
        self.assertIn("Python", data["required_skills"])
        self.assertIn("Java", data["required_skills"])
        self.assertIn("Git", data["required_skills"])
        self.assertIn("React", data["preferred_skills"])
        self.assertIn("Docker", data["preferred_skills"])
        self.assertEqual(data["experience_requirements"][0]["years"], 0)

    def test_messy_and_inline_headers_parse(self):
        data = self.parser.parse_text(MESSY_INLINE_HEADER_JD)

        self.assertEqual(data["job_title"], "Data Scientist")
        self.assertEqual(data["company"], "SignalWorks")
        self.assertEqual(data["employment_type"], "Full-time")
        self.assertIn("responsibilities", data["sections"])
        self.assertIn("required_qualifications", data["sections"])
        self.assertIn("preferred_skills", data["sections"])
        self.assertIn("Pandas", data["required_skills"])
        self.assertIn("Power BI", data["preferred_skills"])

    def test_missing_optional_sections_do_not_fabricate_values(self):
        data = self.parser.parse_text(MISSING_OPTIONAL_SECTIONS_JD)

        self.assertEqual(data["job_title"], "QA Engineer")
        self.assertEqual(data["employment_type"], "Full-time")
        self.assertEqual(data["preferred_skills"], [])
        self.assertEqual(data["education_requirements"], [])
        self.assertEqual(data["certifications"], [])

    def test_required_only_and_preferred_only_inputs(self):
        required_data = self.parser.parse_text(REQUIRED_ONLY_JD)
        preferred_data = self.parser.parse_text(PREFERRED_ONLY_JD)

        self.assertIn("Python", required_data["required_skills"])
        self.assertEqual(required_data["preferred_skills"], [])
        self.assertEqual(preferred_data["required_skills"], [])
        self.assertIn("React", preferred_data["preferred_skills"])
        self.assertIn("TypeScript", preferred_data["preferred_skills"])

    def test_no_explicit_required_preferred_headings(self):
        data = self.parser.parse_text(NO_EXPLICIT_REQUIREMENT_HEADERS_JD)

        self.assertIn("Python", data["required_skills"])
        self.assertIn("SQL", data["required_skills"])
        self.assertIn("Docker", data["preferred_skills"])
        self.assertEqual(data["responsibilities"], ["You will build REST APIs with the product engineering team."])
        self.assertEqual(data["education_requirements"][0]["degree_level"], ["bachelor"])

    def test_long_job_description_is_deduplicated(self):
        long_text = SOFTWARE_ENGINEER_JD + "\n" + "\n".join([
            "- Proficient in Python, SQL, Git, and REST APIs."
            for _ in range(25)
        ])
        data = self.parser.parse_text(long_text)

        qualification_texts = [item["text"] for item in data["required_qualifications"]]
        self.assertEqual(qualification_texts.count("Proficient in Python, SQL, Git, and REST APIs."), 1)
        self.assertEqual(data["required_skills"].count("Python"), 1)

    def test_parser_output_is_deterministic_for_ten_runs(self):
        results = [self.parser.parse_text(SOFTWARE_ENGINEER_JD) for _ in range(10)]

        self.assertTrue(all(result == results[0] for result in results))

    def test_sde_fidelity_fixture_routes_requirements_without_inflation(self):
        data = self.parser.parse_text(SDE_FIDELITY_JD)

        self.assertEqual(len(data["experience_requirements"]), 1)
        self.assertEqual(data["experience_requirements"][0]["min_years"], 2)
        self.assertEqual(data["experience_requirements"][0]["max_years"], 5)
        self.assertIsNone(data["experience_requirements"][0]["domain"])
        self.assertIn("Python", data["required_skills"])
        self.assertIn("JavaScript", data["required_skills"])
        self.assertIn("TypeScript", data["required_skills"])
        self.assertNotIn("Data Structures", data["required_skills"])
        self.assertTrue(any(item["category"] == "capability" and "Data structures" in item["text"] for item in data["required_capability_requirements"]))
        self.assertEqual(len(data["education_requirements"]), 1)
        self.assertEqual(len(data["responsibilities"]), 8)
        self.assertEqual(len(data["required_qualifications"]), len({item["text"] for item in data["required_qualifications"]}))


if __name__ == "__main__":
    unittest.main()
