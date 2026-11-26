import asyncio
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from backend.__main__ import main
from backend.database import Base, make_engine
from backend.macro_repository import MacroRepository
from backend.openrouter import OpenRouterError
from sqlalchemy.orm import sessionmaker
import httpx


class FakeProvider:
    def __init__(self, _key_provider):
        self.calls = 0

    async def analyze_news(self, context):
        self.calls += 1
        return {"status": "no_relevant_news", "summary": "No relevant facts.", "items": [], "model_id": "test/news"}


class MacroRefreshTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.engine = make_engine(f"sqlite:///{self.tempdir.name}/macro.db")
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine, expire_on_commit=False)

    def tearDown(self):
        self.engine.dispose()
        self.tempdir.cleanup()

    def test_cli_refresh_persists_and_returns_safe_output_without_uvicorn(self):
        output = io.StringIO()
        with patch("backend.macro_refresh.get_session_factory", return_value=self.factory), patch("backend.macro_refresh.OpenRouterClient", FakeProvider), patch("backend.macro_refresh.RSSNewsAdapter") as rss, patch("backend.__main__.uvicorn.run", side_effect=AssertionError("server must not start")), redirect_stdout(output):
            rss.return_value.collect.return_value = []
            code = main(["refresh-macro", "--instrument", "WDO"])
        self.assertEqual(code, 0)
        self.assertIn("state=no_relevant_news", output.getvalue())
        self.assertIn("valid_until=", output.getvalue())
        self.assertNotIn("secret", output.getvalue())
        self.assertEqual(MacroRepository(self.factory).latest_usable("WDO")["prompt_version"], "macroeconomic-news-v7")

    def test_invalid_output_retries_once_then_records_failure(self):
        class InvalidProvider(FakeProvider):
            async def analyze_news(self, context):
                self.calls += 1
                raise OpenRouterError("invalid_model_output", "missing fields: summary", retryable=False)

        provider = InvalidProvider(None)
        output = io.StringIO()
        with patch("backend.macro_refresh.get_session_factory", return_value=self.factory), patch("backend.macro_refresh.OpenRouterClient", return_value=provider), patch("backend.macro_refresh.RSSNewsAdapter") as rss, redirect_stdout(output):
            rss.return_value.collect.return_value = []
            code = main(["refresh-macro", "--instrument", "WIN"])
        self.assertEqual(code, 1)
        self.assertEqual(provider.calls, 2)
        self.assertIn("invalid_model_output", output.getvalue())
        self.assertIsNone(MacroRepository(self.factory).latest_usable("WIN"))

    def test_invalid_output_recovers_on_single_retry(self):
        class RecoveringProvider(FakeProvider):
            contexts = []

            async def analyze_news(self, context):
                self.calls += 1
                self.contexts.append(context)
                if self.calls == 1:
                    raise OpenRouterError("invalid_model_output", "A macroeconomic news item has an unsupported confirmation level.", retryable=False)
                return {"status": "no_relevant_news", "summary": "No relevant facts.", "items": [], "model_id": "test/news"}

        provider = RecoveringProvider(None)
        with patch("backend.macro_refresh.get_session_factory", return_value=self.factory), patch("backend.macro_refresh.OpenRouterClient", return_value=provider), patch("backend.macro_refresh.RSSNewsAdapter") as rss:
            rss.return_value.collect.return_value = []
            success, message = asyncio.run(__import__("backend.macro_refresh", fromlist=["refresh_macro"]).refresh_macro("WIN"))
        self.assertTrue(success)
        self.assertEqual(provider.calls, 2)
        self.assertNotIn("format_feedback", provider.contexts[0])
        self.assertEqual(provider.contexts[1]["format_feedback"], "A macroeconomic news item has an unsupported confirmation level.")
        self.assertEqual(MacroRepository(self.factory).latest_usable("WIN")["status"], "no_relevant_news")

    def test_web_unavailable_is_failure_not_no_relevant_news(self):
        class UnavailableProvider(FakeProvider):
            async def analyze_news(self, context):
                return {"status": "unavailable", "summary": "Research failed.", "items": [],
                        "model_id": "test/news", "tool_use": {"web_search_requests": 1}}

        with patch("backend.macro_refresh.get_session_factory", return_value=self.factory), patch("backend.macro_refresh.OpenRouterClient", UnavailableProvider), patch("backend.macro_refresh.RSSNewsAdapter") as rss:
            rss.return_value.collect.return_value = []
            success, message = asyncio.run(__import__("backend.macro_refresh", fromlist=["refresh_macro"]).refresh_macro("WDO"))
        self.assertFalse(success)
        self.assertIn("research_unavailable", message)
        self.assertIn("web_search_requests=1", message)
        self.assertIsNone(MacroRepository(self.factory).latest_usable("WDO"))

    def test_recorded_provider_response_persists_versions_and_rss_without_secret(self):
        from backend.macro_refresh import refresh_macro
        from backend.openrouter import OpenRouterClient
        from backend.news import NewsSourceResult
        def recorded(request):
            body = json.loads(request.content)
            self.assertIn("PREÇO DO WIN", body["messages"][0]["content"])
            self.assertEqual(len(body["tools"]), 2)
            return httpx.Response(200, json={"model": "recorded/model", "choices": [{"message": {"content": json.dumps({
                "status": "available", "summary": "Fato relevante para o índice.", "items": [{
                    "title": "Comunicado", "url": "https://www.bcb.gov.br/comunicado",
                    "published_at": None, "confirmation": "official_confirmation", "relevance": "high",
                    "instrument_effect": "unclear", "fact_summary": "Comunicado publicado.",
                    "transmission_channel": "Pode afetar expectativas de juros.",
                }],
            })}}]})
        transport = httpx.MockTransport(recorded)
        feed = NewsSourceResult("unavailable", "feed.example", "2026-11-26T15:00:00Z", "2026-11-26T15:15:00Z", (), "Feed indisponível.")
        with patch("backend.macro_refresh.get_session_factory", return_value=self.factory), patch("backend.macro_refresh.OpenRouterClient", side_effect=lambda _key: OpenRouterClient(lambda: "secret-test-key", news_model="test/news", transport=transport)), patch("backend.macro_refresh.RSSNewsAdapter") as rss:
            rss.return_value.collect.return_value = [feed]
            success, message = asyncio.run(refresh_macro("WIN"))
        self.assertTrue(success)
        cached = MacroRepository(self.factory).latest_usable("WIN")
        self.assertEqual(cached["model_id"], "recorded/model")
        self.assertEqual(cached["prompt_version"], "macroeconomic-news-v7")
        self.assertEqual(cached["rss_evidence"][0]["status"], "unavailable")
        self.assertEqual(cached["items"][0]["instrument"], "WIN")
        self.assertNotIn("secret-test-key", json.dumps(cached) + message)

    def test_default_command_starts_server(self):
        with patch("backend.__main__.uvicorn.run") as run:
            self.assertEqual(main([]), 0)
            run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
