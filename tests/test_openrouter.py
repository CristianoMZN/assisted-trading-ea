import asyncio
import json
import unittest

import httpx

from backend.openrouter import OpenRouterClient, OpenRouterError, validate_candidate, validate_news_analysis


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

    def test_decision_scenario_reports_safe_validation_reason(self):
        for scenario, diagnostic in (
            (None, "must be a string"),
            ("   ", "must be non-empty"),
            ("private " + "x" * 241, "exceeds 240 characters"),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaises(OpenRouterError) as caught:
                validate_candidate({**candidate(), "scenario": scenario})
            self.assertEqual(caught.exception.code, "invalid_model_output")
            self.assertIn(diagnostic, caught.exception.message)
            self.assertNotIn("private", caught.exception.message)

    def test_decision_prompt_requires_brief_scenario(self):
        from backend.prompts import PROMPT_VERSIONS, load_prompt
        self.assertEqual(PROMPT_VERSIONS["decision"], "market-decision-v2")
        self.assertIn("at most 240 characters", load_prompt("decision"))

    def test_news_request_requires_schema_capable_provider(self):
        def respond(request):
            body = json.loads(request.content)
            self.assertEqual(body["provider"], {"require_parameters": True})
            self.assertEqual(body["response_format"]["type"], "json_schema")
            self.assertEqual(len(body["tools"]), 2)
            self.assertEqual(body["tool_choice"], "required")
            return provider_response({
                "status": "no_relevant_news",
                "summary": "No relevant news found.",
                "items": [],
            })

        client = OpenRouterClient(
            lambda: "secret-test-key",
            news_model="test/news-model",
            transport=httpx.MockTransport(respond),
        )
        result = self.run_async(client.analyze_news({"instrument": {"logical_symbol": "WDO"}, "as_of": "2026-11-26T12:00:00Z"}))
        self.assertEqual(result["status"], "no_relevant_news")

    def test_news_returns_only_safe_server_tool_counts(self):
        response = httpx.Response(200, json={
            "model": "test/news", "choices": [{"message": {"content": json.dumps({
                "status": "unavailable", "summary": "Search could not finish.", "items": [],
            })}}],
            "usage": {"server_tool_use": {"web_search_requests": 2, "web_fetch_requests": 0, "raw": "private tool output"}},
        })
        client = OpenRouterClient(lambda: "secret", news_model="test/news", transport=httpx.MockTransport(lambda _request: response))
        result = self.run_async(client.analyze_news({"instrument": {"logical_symbol": "WDO"}}))
        self.assertEqual(result["tool_use"], {"web_search_requests": 2, "web_fetch_requests": 0})
        self.assertNotIn("private", json.dumps(result))

    def test_news_reads_current_openrouter_tool_usage_shape(self):
        response = httpx.Response(200, json={
            "model": "test/news", "choices": [{"message": {"content": json.dumps({
                "status": "unavailable", "summary": "Search could not finish.", "items": [],
            })}}],
            "usage": {"server_tool_use_details": {
                "web_search_requests": 1, "tool_calls_requested": 1,
                "tool_calls_executed": 1, "raw": "private tool output",
            }},
        })
        client = OpenRouterClient(lambda: "secret", news_model="test/news", transport=httpx.MockTransport(lambda _request: response))
        result = self.run_async(client.analyze_news({"instrument": {"logical_symbol": "WDO"}}))
        self.assertEqual(result["tool_use"], {"web_search_requests": 1})
        self.assertNotIn("private", json.dumps(result))

    def test_news_model_without_required_parameters_has_explicit_error(self):
        def unsupported(_request):
            return httpx.Response(404, json={
                "error": {"message": "No endpoints found that can handle the requested parameters"},
            })

        client = OpenRouterClient(
            lambda: "secret-test-key",
            news_model="test/news-model",
            transport=httpx.MockTransport(unsupported),
        )
        with self.assertRaises(OpenRouterError) as caught:
            self.run_async(client.analyze_news({"instrument": {"logical_symbol": "WDO"}}))
        self.assertEqual(caught.exception.code, "model_parameters_unsupported")
        self.assertFalse(caught.exception.retryable)

    def test_provider_http_failure_reports_safe_status_only(self):
        client = OpenRouterClient(
            lambda: "secret-test-key", model="test/model",
            transport=httpx.MockTransport(lambda _request: httpx.Response(429, text="private provider body")),
        )
        with self.assertRaises(OpenRouterError) as caught:
            self.run_async(client.decide({"market": "snapshot"}))
        self.assertEqual(caught.exception.code, "provider_unavailable")
        self.assertEqual(caught.exception.message, "OpenRouter returned HTTP 429.")
        self.assertNotIn("private provider body", caught.exception.message)

    def test_rate_limit_reports_safe_origin_without_provider_body(self):
        response = httpx.Response(429, json={"error": {
            "message": "private provider body",
            "metadata": {"limit_source": "upstream_provider_shared_pool", "raw": "private upstream response"},
        }})
        client = OpenRouterClient(
            lambda: "secret-test-key", model="test/model",
            transport=httpx.MockTransport(lambda _request: response),
        )
        with self.assertRaises(OpenRouterError) as caught:
            self.run_async(client.decide({"market": "snapshot"}))
        self.assertIn("limit_source=upstream_provider_shared_pool", caught.exception.message)
        self.assertNotIn("private", caught.exception.message)

    def test_news_schema_error_reports_shape_without_content(self):
        with self.assertRaises(OpenRouterError) as caught:
            validate_news_analysis({"status": "available", "private_value": "do not log"}, "WDO")
        self.assertEqual(caught.exception.code, "invalid_model_output")
        self.assertIn("missing fields: items, summary", caught.exception.message)
        self.assertNotIn("private_value", caught.exception.message)
        self.assertNotIn("do not log", caught.exception.message)

    def test_invalid_news_summary_is_rejected_without_fabrication(self):
        for summary in ("", None, "x" * 601):
            with self.subTest(summary_type=type(summary).__name__):
                with self.assertRaises(OpenRouterError) as caught:
                    validate_news_analysis({"status": "no_relevant_news", "summary": summary, "items": []}, "WDO")
                self.assertEqual(caught.exception.code, "invalid_model_output")
                self.assertIn("summary", caught.exception.message)

    def test_news_item_requires_exact_fields_and_allowed_https_url(self):
        item = {
            "title": "Comunicado do Banco Central",
            "url": "https://www.bcb.gov.br/comunicados/teste",
            "published_at": None,
            "confirmation": "official_confirmation",
            "relevance": "high",
            "instrument_effect": "unclear",
            "fact_summary": "Comunicado oficial consultado.",
            "transmission_channel": "Pode afetar expectativas de juros.",
        }
        value = {"status": "available", "summary": "Resumo curto.", "items": [item]}
        result = validate_news_analysis(value, "WDO")
        self.assertEqual(result["items"][0]["source_name"], "www.bcb.gov.br")
        self.assertEqual(result["items"][0]["instrument"], "WDO")
        self.assertIsNone(validate_news_analysis({**value, "items": [{**item, "published_at": "2026-11-26"}]}, "WDO")["items"][0]["published_at"])
        for changed, diagnostic in (
            ({k: v for k, v in item.items() if k != "fact_summary"}, "fact_summary"),
            ({**item, "extra_comment": "private"}, "unexpected field count: 1"),
            ({**item, "url": "http://evil.example/fato"}, "allowed source"),
            ({**item, "title": ""}, "title"),
            ({**item, "instrument_effect": "pressure_up"}, "instrument effect"),
            ({**item, "transmission_channel": None}, "transmission_channel text (must be a string)"),
            ({**item, "transmission_channel": "  "}, "transmission_channel text (must be non-empty)"),
            ({**item, "transmission_channel": "x" * 301}, "transmission_channel text (exceeds 300 characters)"),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaises(OpenRouterError) as caught:
                validate_news_analysis({**value, "items": [changed]}, "WDO")
            self.assertIn(diagnostic, caught.exception.message)
            self.assertNotIn("private", caught.exception.message)

    def test_win_prompt_and_effect_are_instrument_specific(self):
        from backend.prompts import load_prompt
        self.assertIn("PREÇO DO WIN", load_prompt("news_analysis", instrument="WIN"))
        self.assertIn("PREÇO DO WDO", load_prompt("news_analysis", instrument="WDO"))
        self.assertIn("`transmission_channel`, 1–300", load_prompt("news_analysis", instrument="WIN"))
        self.assertIn("`transmission_channel`, 1–300", load_prompt("news_analysis", instrument="WDO"))
        self.assertNotIn("pressão sobre USD/BRL", load_prompt("news_analysis", instrument="WDO"))
        self.assertIn("páginas de especificação do contrato", load_prompt("news_analysis", instrument="WDO"))
        self.assertEqual(validate_news_analysis({"status": "no_relevant_news", "summary": "Nada relevante.", "items": []}, "WIN")["items"], [])


if __name__ == "__main__":
    unittest.main()
