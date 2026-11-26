import asyncio
import json
import unittest

import httpx

from backend.openrouter import OpenRouterClient, OpenRouterError


def candidate(action="BUY"):
    if action == "NO_SIGNAL":
        return {
            "action": action,
            "reference_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
            "confidence": "low",
            "scenario": "Evidence is insufficient.",
        }
    return {
        "action": action,
        "reference_price": 100.0,
        "stop_loss": 99.0,
        "take_profit": 102.0,
        "risk_reward": "1:2",
        "confidence": "medium",
        "scenario": "Candidate for deterministic validation.",
    }


def provider_response(value):
    return httpx.Response(200, json={
        "model": "test/provider-model",
        "choices": [{"message": {"content": json.dumps(value)}}],
    })


class OpenRouterClientTests(unittest.TestCase):
    def run_async(self, awaitable):
        return asyncio.run(awaitable)

    def test_missing_key_fails_before_http_request(self):
        client = OpenRouterClient(lambda: None, model="test/model", transport=httpx.MockTransport(lambda _request: self.fail("request must not be sent")))
        with self.assertRaises(OpenRouterError) as caught:
            self.run_async(client.decide({"market": "snapshot"}))
        self.assertEqual(caught.exception.code, "provider_key_missing")

    def test_structured_candidate_is_validated_and_model_id_returned(self):
        client = OpenRouterClient(
            lambda: "secret-test-key",
            model="test/model",
            transport=httpx.MockTransport(lambda request: provider_response(candidate())),
        )
        result = self.run_async(client.decide({"market": "snapshot"}))
        self.assertEqual(result["action"], "BUY")
        self.assertEqual(result["model_id"], "test/provider-model")

    def test_timeout_is_non_actionable_and_redacted(self):
        def timeout(_request):
            raise httpx.ReadTimeout("provider timeout")

        client = OpenRouterClient(lambda: "secret-test-key", model="test/model", transport=httpx.MockTransport(timeout))
        with self.assertRaises(OpenRouterError) as caught:
            self.run_async(client.decide({"market": "snapshot"}))
        self.assertEqual(caught.exception.code, "provider_timeout")
        self.assertNotIn("secret-test-key", str(caught.exception))

    def test_output_outside_schema_is_rejected(self):
        client = OpenRouterClient(
            lambda: "secret-test-key",
            model="test/model",
            transport=httpx.MockTransport(lambda _request: provider_response({"action": "BUY"})),
        )
        with self.assertRaises(OpenRouterError) as caught:
            self.run_async(client.decide({"market": "snapshot"}))
        self.assertEqual(caught.exception.code, "invalid_model_output")

    def test_no_signal_has_no_prices(self):
        client = OpenRouterClient(
            lambda: "secret-test-key",
            model="test/model",
            transport=httpx.MockTransport(lambda _request: provider_response(candidate("NO_SIGNAL"))),
        )
        result = self.run_async(client.decide({"market": "snapshot"}))
        self.assertEqual(result["action"], "NO_SIGNAL")
        self.assertIsNone(result["reference_price"])


if __name__ == "__main__":
    unittest.main()
