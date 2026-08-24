"""Response and grounding contract tests for Phase 3A."""

import sys
import unittest
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from ai.context_builder import AIContextBuilder  # noqa: E402
from ai.contracts import AIResponse, AIResponseStatus  # noqa: E402
from ai.response_validator import (  # noqa: E402
    AIResponseValidationError,
    EvidenceGroundingValidator,
    GroundingValidationError,
    AIResponseValidator,
)
from test_ai_context_builder import TestAIContextBuilder  # noqa: E402


class TestAIResponseValidator(unittest.TestCase):
    def setUp(self):
        source = TestAIContextBuilder()._resume_input()
        self.context = AIContextBuilder().build(source)
        self.evidence_id = self.context.evidence_registry[0].evidence_id
        self.validator = AIResponseValidator()

    def test_valid_grounded_response_is_accepted(self):
        response = AIResponse(
            status=AIResponseStatus.COMPLETE,
            summary="The deterministic profile has strong evidence.",
            strengths=[{"text": "Python is supported.", "evidence_reference_ids": [self.evidence_id]}],
            evidence_references=[self.evidence_id],
        )
        validated = self.validator.validate(response, self.context)
        self.assertEqual(validated.status, AIResponseStatus.COMPLETE)

    def test_unknown_evidence_reference_is_rejected(self):
        response = AIResponse(
            status=AIResponseStatus.COMPLETE,
            summary="Unsupported claim.",
            strengths=[{"text": "Unsupported.", "evidence_reference_ids": ["RESUME-SKILL-999"]}],
        )
        with self.assertRaises(GroundingValidationError):
            self.validator.validate(response, self.context)

    def test_unavailable_response_requires_reason(self):
        response = AIResponse(status=AIResponseStatus.UNAVAILABLE, summary="Unavailable")
        with self.assertRaises(AIResponseValidationError):
            self.validator.validate(response, self.context)

    def test_deterministic_score_mutation_is_rejected(self):
        with self.assertRaises(AIResponseValidationError):
            self.validator.validate(
                {"status": "complete", "summary": "bad", "score": 100},
                self.context,
            )

    def test_unknown_top_level_fields_are_rejected(self):
        with self.assertRaises(AIResponseValidationError):
            self.validator.validate(
                {"status": "complete", "summary": "bad", "unexpected": True},
                self.context,
            )

    def test_grounding_contract_only_checks_registered_ids(self):
        grounding = EvidenceGroundingValidator()
        self.assertTrue(grounding.validate_claim("supported", [self.evidence_id], self.context))
        self.assertFalse(grounding.validate_claim("unsupported", ["UNKNOWN"], self.context))
        self.assertFalse(grounding.validate_claim("no evidence", [], self.context))


if __name__ == "__main__":
    unittest.main()

