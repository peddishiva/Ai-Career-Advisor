"""Contract tests for the Phase 3A AI boundary."""

import json
import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from ai.contracts import AITaskType, DeterministicAIInput, FlowType  # noqa: E402


class TestAIContracts(unittest.TestCase):
    def _resume_input(self, **overrides):
        values = {
            "flow_type": FlowType.RESUME_ANALYSIS,
            "session_id": "resume-session-1",
            "resume_id": "resume-1",
            "deterministic_result_hash": "resume-result-hash",
            "deterministic_facts": {"resume": {"skills": ["Python"]}, "analysis": {}},
            "task": AITaskType.RESUME_EXPLANATION,
        }
        values.update(overrides)
        return DeterministicAIInput(**values)

    def test_supported_flow_and_task_are_strict(self):
        source = self._resume_input()
        self.assertEqual(source.flow_type.value, "resume_analysis")
        self.assertEqual(source.task.value, "resume_explanation")
        json.dumps(source.model_dump(mode="json"))

        with self.assertRaises(ValidationError):
            self._resume_input(flow_type="unsupported")

        with self.assertRaises(ValidationError):
            self._resume_input(task=AITaskType.JDXR_MATCH_EXPLANATION)

    def test_resume_scope_rejects_jd_identifier(self):
        with self.assertRaises(ValidationError):
            self._resume_input(jd_id="jd-1")

    def test_jdxr_scope_requires_both_document_identifiers(self):
        with self.assertRaises(ValidationError):
            DeterministicAIInput(
                flow_type=FlowType.JDXR,
                session_id="jdxr-session-1",
                resume_id="resume-1",
                deterministic_result_hash="match-hash",
                deterministic_facts={"resume": {}, "job_description": {}, "match": {}},
                task=AITaskType.JDXR_MATCH_EXPLANATION,
            )


if __name__ == "__main__":
    unittest.main()

