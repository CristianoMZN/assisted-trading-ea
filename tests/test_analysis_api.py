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
from backend.repository import AnalysisRepository
from backend.openrouter import OpenRouterClient, OpenRouterError


def market_request():
    request = json.loads((Path(__file__).resolve().parents[1] / "contracts/examples/request-valid.json").read_text())
    end = datetime.fromisoformat("2026-11-25T14:05:00+00:00")
    request["candles"] = []
    for index in range(20):
        close = 100 + index
        stamp = end - timedelta(minutes=5 * (19 - index))
        request["candles"].append({
            "timestamp": stamp.isoformat().replace("+00:00", "Z"),
            "open": close - 0.5,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "tick_volume": 1,
            "real_volume": None,
            "buy_volume": None,
            "sell_volume": None,
        })
    return request


class FakeProvider:
    def __init__(self, outcome):
        self.outcome = outcome

    async def decide(self, _context):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class AnalysisApiFailClosedTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)
        self.request = market_request()
        self.factory_patch = patch("backend.main.get_session_factory", return_value=self.session_factory)
        self.factory_patch.start()

    def tearDown(self):
        self.factory_patch.stop()
        self.engine.dispose()

    def run_async(self, request):
        return asyncio.run(analyze(request))

    def test_missing_key_returns_error_not_decision(self):
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}, clear=False):
            with patch("backend.main.OpenRouterClient") as client_class:
                client_class.side_effect = lambda key_provider: OpenRouterClient(key_provider, model="test/model", transport=None)
                response = self.run_async(self.request)
        body = json.loads(response.body)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(body["error"]["code"], "provider_key_missing")
        self.assertNotIn("decision", body)
        self.assertEqual(AnalysisRepository(self.session_factory).get(self.request["request_id"])["state"], "failed")

    def test_timeout_and_invalid_schema_return_errors_not_decisions(self):
        for error in (
            OpenRouterError("provider_timeout", "OpenRouter request timed out.", retryable=True),
            OpenRouterError("invalid_model_output", "Model output does not match the required decision schema.", retryable=False),
        ):
            request = market_request()
            request["request_id"] = f"123e4567-e89b-42d3-a456-4266141740{len(error.code):02d}"
            with patch("backend.main.OpenRouterClient", return_value=FakeProvider(error)):
                response = self.run_async(request)
            body = json.loads(response.body)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(body["error"]["code"], error.code)
            self.assertNotIn("decision", body)

    def test_invalid_model_buy_candidate_becomes_no_signal(self):
        candidate = {
            "action": "BUY", "reference_price": 100.0, "stop_loss": 99.0,
            "take_profit": 102.0, "risk_reward": "1:2", "confidence": "medium",
            "scenario": "Candidate.", "model_id": "test/model",
        }
        with patch("backend.main.OpenRouterClient", return_value=FakeProvider(candidate)):
            response = self.run_async(self.request)
        body = json.loads(response.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "no_signal")
        self.assertEqual(body["reason_code"], "entry_price_mismatch")
        self.assertIsNone(body["decision"])

    def test_valid_model_candidate_returns_validated_ticket(self):
        candidate = {
            "action": "BUY", "reference_price": 5422.5, "stop_loss": 5421.5,
            "take_profit": 5424.5, "risk_reward": "1:2", "confidence": "medium",
            "scenario": "Candidate.", "model_id": "test/model",
        }
        with patch("backend.main.OpenRouterClient", return_value=FakeProvider(candidate)):
            response = self.run_async(self.request)
        body = json.loads(response.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "actionable")
        self.assertEqual(body["decision"]["direction"], "BUY")
        self.assertEqual(body["decision"]["risk_reward"], self.request["preferences"]["risk_reward"])
        self.assertAlmostEqual(body["decision"]["estimated_loss"], 2.5)
        recovered = AnalysisRepository(self.session_factory).get(self.request["request_id"])
        self.assertEqual(recovered["state"], "actionable")
        self.assertEqual(recovered["decision"]["direction"], "BUY")
        self.assertEqual(len(recovered["evidence"]), len(body["sources"]))
        model_version = next(item for item in recovered["versions"] if item["component"] == "model")
        self.assertEqual(model_version["model_id"], "test/model")

    def test_insufficient_snapshot_returns_persisted_no_signal_without_model_call(self):
        request = json.loads((Path(__file__).resolve().parents[1] / "contracts/examples/request-valid.json").read_text())
        with patch("backend.main.OpenRouterClient") as provider:
            provider.side_effect = AssertionError("insufficient market data must not call the model")
            response = self.run_async(request)
        body = json.loads(response.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "no_signal")
        self.assertEqual(body["reason_code"], "insufficient_market_data")
        self.assertIsNone(body["decision"])
        recovered = AnalysisRepository(self.session_factory).get(request["request_id"])
        self.assertEqual(recovered["state"], "no_signal")
        self.assertEqual(recovered["reason_code"], "insufficient_market_data")
        self.assertEqual(recovered["evidence"][0]["status"], "insufficient")

    def test_candidate_with_nonpositive_net_return_returns_no_signal(self):
        candidate = {
            "action": "BUY", "reference_price": 5422.5, "stop_loss": 5421.5,
            "take_profit": 5424.5, "risk_reward": "1:2", "confidence": "medium",
            "scenario": "Costs make the candidate invalid.", "model_id": "test/model",
        }
        request = market_request()
        request["preferences"]["round_trip_cost_per_contract"] = 2.0
        with patch("backend.main.OpenRouterClient", return_value=FakeProvider(candidate)):
            response = self.run_async(request)
        body = json.loads(response.body)
        self.assertEqual(body["status"], "no_signal")
        self.assertEqual(body["reason_code"], "net_return_non_positive")
        self.assertIsNone(body["decision"])


if __name__ == "__main__":
    unittest.main()
