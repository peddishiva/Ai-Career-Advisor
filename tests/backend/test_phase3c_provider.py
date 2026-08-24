"""Phase 3C provider adapter and failure-mode tests."""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from ai.contracts import AIRequest, AITaskType, DeterministicAIInput, FlowType
from ai.context_builder import AIContextBuilder
from ai.prompt_builder import PromptBuilder
from ai.provider import (
    AIProviderConfigurationError,
    AIProviderInvalidResponse,
    AIProviderRateLimited,
    AIProviderTimeout,
    GeminiProvider,
    MockAIProvider,
    NullAIProvider,
    build_configured_provider,
)
from config.ai_config import AIProviderConfig


class TestPhase3CProvider(unittest.TestCase):
    def setUp(self):
        source = DeterministicAIInput(
            flow_type=FlowType.RESUME_ANALYSIS,
            session_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            resume_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            deterministic_result_hash="result-hash",
            deterministic_facts={
                "parsed_resume": {"skills": ["Python"], "experience": []},
                "analysis": {},
            },
            task=AITaskType.RESUME_EXPLANATION,
        )
        context = AIContextBuilder().build(
            source,
            retrieved_knowledge=[
                {
                    "knowledge_id": "SKILL-PYTHON-001",
                    "title": "Python",
                    "category": "skill",
                    "content": "Python guidance.",
                    "source_id": "PYTHON-OFFICIAL",
                    "source_title": "Python Documentation",
                    "publisher": "Python Software Foundation",
                    "url": "https://docs.python.org/3/",
                    "source_version": "1.0.0",
                    "knowledge_version": "1.0.0",
                    "trust_level": "high",
                }
            ],
        )
        self.request = AIRequest(
            request_id="request-1",
            flow_type=source.flow_type,
            session_id=source.session_id,
            resume_id=source.resume_id,
            task=source.task,
            context=context,
            prompt=PromptBuilder().build(context, source.task),
        )
        self.config = AIProviderConfig(
            enabled=True,
            provider_name="gemini",
            model_name="gemini-test",
            timeout_seconds=0.1,
            max_output_tokens=200,
            retry_limit=0,
            temperature=0.0,
            api_key_env_var="PHASE3C_TEST_KEY",
            provider_url="https://example.invalid/{model}",
        )

    def test_mock_provider_returns_structured_json_serializable_output(self):
        response = MockAIProvider().generate(self.request)
        payload = response.model_dump(mode="json")
        self.assertEqual("complete", payload["status"])
        self.assertIn("SKILL-PYTHON-001", payload["knowledge_references"])
        json.dumps(payload)

    def test_gemini_adapter_parses_strict_json_and_keeps_key_server_side(self):
        provider = GeminiProvider(self.config)
        body = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "status": "complete",
                                        "summary": "General guidance.",
                                        "confidence_notes": ["Structured test response."],
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }
        response = Mock(status_code=200)
        response.json.return_value = body
        with patch.dict(os.environ, {"PHASE3C_TEST_KEY": "secret-test-key"}, clear=False), patch(
            "ai.provider.requests.post", return_value=response
        ) as post:
            parsed = provider.generate(self.request)
        self.assertEqual("complete", parsed.status.value)
        call = post.call_args
        self.assertNotIn("secret-test-key", call.args[0])
        self.assertEqual("secret-test-key", call.kwargs["headers"]["x-goog-api-key"])

    def test_missing_key_is_rejected_without_network_call(self):
        provider = GeminiProvider(self.config)
        with patch.dict(os.environ, {}, clear=True), patch("ai.provider.requests.post") as post:
            with self.assertRaises(AIProviderConfigurationError):
                provider.generate(self.request)
        post.assert_not_called()

    def test_timeout_and_rate_limit_are_normalized(self):
        provider = GeminiProvider(self.config)
        with patch.dict(os.environ, {"PHASE3C_TEST_KEY": "key"}, clear=False), patch(
            "ai.provider.requests.post", side_effect=__import__("requests").Timeout()
        ):
            with self.assertRaises(AIProviderTimeout):
                provider.generate(self.request)

        response = Mock(status_code=429)
        with patch.dict(os.environ, {"PHASE3C_TEST_KEY": "key"}, clear=False), patch(
            "ai.provider.requests.post", return_value=response
        ):
            with self.assertRaises(AIProviderRateLimited):
                provider.generate(self.request)

    def test_malformed_json_and_schema_invalid_response_are_rejected(self):
        provider = GeminiProvider(self.config)
        for text in ("not-json", json.dumps({"status": "complete", "unexpected": True})):
            response = Mock(status_code=200)
            response.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": text}]}}],
            }
            with patch.dict(os.environ, {"PHASE3C_TEST_KEY": "key"}, clear=False), patch(
                "ai.provider.requests.post", return_value=response
            ):
                with self.assertRaises(AIProviderInvalidResponse):
                    provider.generate(self.request)

    def test_provider_factory_supports_disabled_and_mock_modes(self):
        self.assertIsInstance(
            build_configured_provider(
                AIProviderConfig(enabled=False, provider_name="gemini")
            ),
            NullAIProvider,
        )
        mock_provider = build_configured_provider(
            AIProviderConfig(enabled=True, provider_name="mock", model_name="mock-test")
        )
        self.assertIsInstance(mock_provider, MockAIProvider)


if __name__ == "__main__":
    unittest.main()
