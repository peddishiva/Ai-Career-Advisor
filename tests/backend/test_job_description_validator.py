"""
Tests for the deterministic job description validation gate.
"""

import sys
from pathlib import Path
import unittest

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
tests_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(tests_path))

from job_description_fixtures import (
    MESSY_INLINE_HEADER_JD,
    NEGATIVE_CONTROLS,
    NO_EXPLICIT_REQUIREMENT_HEADERS_JD,
    REALISTIC_JDS,
)
from config.job_description_config import UNSECTIONED_JD_STRUCTURE_SCORE
from services.job_description_validator import (
    NOT_A_JOB_DESCRIPTION,
    UNCERTAIN,
    VALID_JOB_DESCRIPTION,
    JobDescriptionValidator,
)


class TestJobDescriptionValidator(unittest.TestCase):
    """Validate job description and non-job-document classification."""

    def setUp(self):
        self.validator = JobDescriptionValidator()

    def assert_valid_jd(self, text: str):
        result = self.validator.validate_text(text)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["classification"], VALID_JOB_DESCRIPTION)
        self.assertEqual(result["document_type"], "job_description")

    def assert_not_jd(self, text: str):
        result = self.validator.validate_text(text)
        self.assertFalse(result["valid"], result)
        self.assertIn(result["classification"], {NOT_A_JOB_DESCRIPTION, UNCERTAIN})
        if result["classification"] == NOT_A_JOB_DESCRIPTION:
            self.assertEqual(result["document_type"], "not_job_description")

    def test_realistic_job_descriptions_are_valid(self):
        for name, text in REALISTIC_JDS.items():
            with self.subTest(name=name):
                self.assert_valid_jd(text)

    def test_negative_controls_are_not_valid_job_descriptions(self):
        for name, text in NEGATIVE_CONTROLS.items():
            with self.subTest(name=name):
                self.assert_not_jd(text)

    def test_messy_inline_headers_are_valid(self):
        result = self.validator.validate_text(MESSY_INLINE_HEADER_JD)

        self.assertTrue(result["valid"], result)
        self.assertIn("responsibilities", result["signals"]["sections"])
        self.assertIn("preferred_skills", result["signals"]["sections"])

    def test_unsectioned_compact_job_description_is_valid(self):
        self.assert_valid_jd(NO_EXPLICIT_REQUIREMENT_HEADERS_JD)

    def test_unsectioned_structure_score_uses_configured_value(self):
        lines = [line.strip() for line in NO_EXPLICIT_REQUIREMENT_HEADERS_JD.splitlines() if line.strip()]
        sections = self.validator._detected_sections(lines)

        self.assertEqual(
            self.validator._structure_score(NO_EXPLICIT_REQUIREMENT_HEADERS_JD, lines, sections),
            UNSECTIONED_JD_STRUCTURE_SCORE,
        )

    def test_technology_keywords_only_do_not_pass(self):
        result = self.validator.validate_text(NEGATIVE_CONTROLS["technology_keyword_list"])

        self.assertFalse(result["valid"], result)
        self.assertEqual(result["classification"], NOT_A_JOB_DESCRIPTION)
        self.assertIn("keyword_list_only", result["signals"]["negative"])

    def test_validation_is_deterministic(self):
        results = [
            self.validator.validate_text(REALISTIC_JDS["software_engineer"])
            for _ in range(10)
        ]

        self.assertTrue(all(result == results[0] for result in results))


if __name__ == "__main__":
    unittest.main()
