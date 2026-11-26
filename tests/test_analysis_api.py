import asyncio
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.main import analyze
from backend.macro_repository import MacroRepository
from backend.models import MacroExecution
from backend.repository import AnalysisRepository
from backend.openrouter import OpenRouterError
from scripts.backend_contract import validate_response


def stamp(value):
    return value.isoformat().replace("+00:00", "Z")


def market_request(*, instrument="WDO", candles=20, age_seconds=0):
    request = json.loads((Path(__file__).resolve().parents[1] / "contracts/examples/request-valid.json").read_text())
    end = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=age_seconds)
    request["sent_at"] = stamp(end)
    request["window"]["to"] = stamp(end)
    request["window"]["from"] = stamp(end - timedelta(days=7))
    request["history_first_available_at"] = stamp(end - timedelta(days=7, minutes=5))
    request["current_quote"]["timestamp"] = stamp(end)
    request["tick_flow"]["to"] = stamp(end)
    request["tick_flow"]["from"] = stamp(end - timedelta(minutes=1))
    request["instrument"]["logical_symbol"] = instrument
    request["instrument"]["broker_symbol"] = f"{instrument}Z26"
    request["candles"] = []
    for index in range(candles):
        close = 100 + index
        request["candles"].append({
            "timestamp": stamp(end - timedelta(minutes=5 * (candles - index))),
            "open": close - 0.5, "high": close + 1, "low": close - 1,
            "close": close, "tick_volume": 1, "real_volume": None,
            "buy_volume": None, "sell_volume": None,
        })
    return request


class FakeProvider:
    def __init__(self, outcome=None):
        self.outcome = outcome or {
            "action": "BUY", "reference_price": 5422.5, "stop_loss": 5421.5,
            "take_profit": 5424.5, "risk_reward": "1:2", "confidence": "medium",
            "scenario": "Candidate.", "model_id": "test/decision",
        }
        self.calls = []

    async def analyze_news(self, _context):
        raise AssertionError("HTTP endpoint must not perform macro research")

    async def interpret_technical(self, context):
        self.calls.append(("technical", context))
        return {"trend": "bullish", "momentum": "positive", "summary": "Current indicators.", "model_id": "test/technical"}

    async def decide(self, context):
        self.calls.append(("decision", context))
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class AnalysisApiCacheTests(unittest.TestCase):
    def setUp(self):
        self.snapshot_age_patch = patch.dict("os.environ", {"MARKET_SNAPSHOT_MAX_AGE_SECONDS": "30"})
        self.snapshot_age_patch.start()
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine, expire_on_commit=False)
        self.repository = MacroRepository(self.factory)
        self.factory_patch = patch("backend.main.get_session_factory", return_value=self.factory)
        self.factory_patch.start()

    def tearDown(self):
        self.factory_patch.stop()
        self.snapshot_age_patch.stop()
        self.engine.dispose()

    def seed(self, instrument="WDO", status="available", completed=None):
        completed = completed or datetime.now(timezone.utc)
        return self.repository.save_success(
            instrument, {"status": status, "summary": "Contexto verificado.",
                         "items": [{"title": "Fato", "url": "https://www.bcb.gov.br/fato", "published_at": None,
                                    "confirmation": "official_confirmation", "relevance": "high", "instrument_effect": "unclear",
                                    "fact_summary": "Fato.", "transmission_channel": "Expectativas de juros."}] if status == "available" else [],
                         "model_id": "test/macro"},
            rss_evidence=[{"type": "news", "status": "unavailable", "source": "feed.example",
                           "observed_at": stamp(completed), "valid_until": stamp(completed + timedelta(minutes=15)),
                           "summary": "Fonte de notícias indisponível.", "data": []}],
            as_of=completed, completed_at=completed, prompt_version="macroeconomic-news-v6",
        )

    def run_async(self, request, provider=None):
        provider = provider or FakeProvider()
        with patch("backend.main.OpenRouterClient", return_value=provider), patch("backend.news.RSSNewsAdapter.collect", side_effect=AssertionError("RSS must not run during POST")):
            response = asyncio.run(analyze(request))
        return response, json.loads(response.body), provider

    def test_cache_reused_with_technical_then_decision_for_each_snapshot(self):
        cache_id = self.seed()
        for index in range(2):
            request = market_request()
            request["request_id"] = f"123e4567-e89b-42d3-a456-4266141740{index:02d}"
            response, body, provider = self.run_async(request)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(body["status"], "actionable")
            self.assertEqual([name for name, _ in provider.calls], ["technical", "decision"])
            self.assertEqual(provider.calls[1][1]["evidence"][-1]["data"]["cache_id"], cache_id)
            audited = AnalysisRepository(self.factory).get(request["request_id"])
            self.assertEqual(audited["macro_execution_id"], cache_id)
            self.assertEqual(len(audited["evidence"]), len(body["sources"]))
            self.assertTrue({"news_analysis_model", "cached_news_prompt", "technical_interpretation_model", "decision_model"} <= {item["component"] for item in audited["versions"]})
            self.assertNotIn("secret-test-key", json.dumps(body) + json.dumps(audited))
            validate_response(body, now=datetime.now(timezone.utc), expected_request_id=request["request_id"], expected_instrument=request["instrument"], tick_size=request["symbol_properties"]["tick_size"])

    def test_missing_wrong_instrument_expired_and_invalid_cache_return_503(self):
        for state in ("missing", "wrong_instrument", "expired", "invalid"):
            with self.subTest(state=state):
                request = market_request(instrument="WIN")
                request["request_id"] = f"123e4567-e89b-42d3-a456-4266141741{len(state):02d}"
                if state == "wrong_instrument":
                    self.seed("WDO")
                elif state == "expired":
                    self.seed("WIN", completed=datetime.now(timezone.utc) - timedelta(minutes=16))
                elif state == "invalid":
                    record_id = self.seed("WIN")
                    with self.factory() as session:
                        session.get(MacroExecution, record_id).items = [{"title": "Incomplete"}]
                        session.commit()
                response, body, provider = self.run_async(request)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(body["error"]["code"], "macro_context_unavailable")
                self.assertEqual(provider.calls, [])
                self.assertEqual(AnalysisRepository(self.factory).get(request["request_id"])["reason_code"], "macro_context_unavailable")

    def test_no_relevant_news_is_usable_and_feed_failure_is_distinct(self):
        self.seed(status="no_relevant_news")
        response, body, _ = self.run_async(market_request())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["sources"][1]["status"], "unavailable")
        self.assertEqual(body["sources"][2]["status"], "no_relevant_news")

    def test_insufficient_market_data_skips_cache_and_models(self):
        response, body, provider = self.run_async(market_request(candles=1))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["reason_code"], "insufficient_market_data")
        self.assertEqual(provider.calls, [])

    def test_provider_error_is_audited_without_actionable_decision(self):
        self.seed()
        request = market_request()
        provider = FakeProvider(OpenRouterError("provider_timeout", "OpenRouter request timed out.", retryable=True))
        response, body, _ = self.run_async(request, provider)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(body["error"]["code"], "provider_timeout")
        self.assertNotIn("decision", body)
        self.assertEqual(AnalysisRepository(self.factory).get(request["request_id"])["state"], "failed")

    def test_stale_at_arrival_returns_no_signal_without_models(self):
        self.seed()
        response, body, provider = self.run_async(market_request(age_seconds=35))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["reason_code"], "stale_market_snapshot")
        self.assertEqual(provider.calls, [])

    def test_old_quote_with_current_sent_at_is_stale(self):
        self.seed()
        request = market_request()
        quote_at = datetime.fromisoformat(request["sent_at"].replace("Z", "+00:00")) - timedelta(seconds=35)
        request["current_quote"]["timestamp"] = stamp(quote_at)
        response, body, provider = self.run_async(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["reason_code"], "stale_market_snapshot")
        self.assertEqual(provider.calls, [])

    def test_action_expiry_is_capped_by_market_deadline(self):
        self.seed()
        request = market_request()
        response, body, _ = self.run_async(request)
        self.assertEqual(body["status"], "actionable")
        expiry = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
        sent = datetime.fromisoformat(request["sent_at"].replace("Z", "+00:00"))
        self.assertLessEqual(expiry, sent + timedelta(seconds=30))

    def test_logs_stage_durations_without_credentials(self):
        self.seed()
        with patch("backend.main.logger.info") as info:
            self.run_async(market_request())
        records = [str(call) for call in info.call_args_list]
        for stage in ("indicators", "macro_cache_read", "technical_interpretation", "decision", "persistence"):
            self.assertTrue(any(stage in record and "duration_ms=" in record for record in records), stage)
        self.assertNotIn("secret-test-key", " ".join(records))

    def test_snapshot_becoming_stale_during_models_is_not_actionable(self):
        self.seed()
        request = market_request()
        base = datetime.fromisoformat(request["sent_at"].replace("Z", "+00:00"))
        class Clock(datetime):
            calls = 0
            @classmethod
            def now(cls, tz=None):
                cls.calls += 1
                return base + timedelta(seconds=1 if cls.calls == 1 else 31)
        with patch("backend.main.datetime", Clock):
            response, body, provider = self.run_async(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "no_signal")
        self.assertEqual(body["reason_code"], "stale_market_snapshot")
        self.assertIsNone(body["decision"])
        self.assertEqual([name for name, _ in provider.calls], ["technical", "decision"])


if __name__ == "__main__":
    unittest.main()
