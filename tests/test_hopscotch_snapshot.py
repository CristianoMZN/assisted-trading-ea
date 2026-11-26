import unittest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.macro_repository import MacroRepository
from backend.main import analyze
from scripts.backend_contract import validate_request, validate_response
from scripts.hopscotch_snapshot import make_snapshot
from tests.test_analysis_api import FakeProvider


class HopscotchSnapshotTests(unittest.TestCase):
    def test_both_instruments_generate_current_contract_11_requests(self):
        for instrument, symbol, bid, ask in (("WDO", "WDOZ26", 5422.0, 5422.5), ("WIN", "WINZ26", 130000, 130005)):
            with self.subTest(instrument=instrument):
                body = make_snapshot(instrument, symbol, bid, ask)
                validate_request(body)
                sent = datetime.fromisoformat(body["sent_at"].replace("Z", "+00:00"))
                self.assertLess((datetime.now(timezone.utc) - sent).total_seconds(), 2)
                self.assertEqual(len(body["candles"]), 20)

    def test_generated_post_keeps_contract_11_for_both_instruments(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        factory = sessionmaker(engine, expire_on_commit=False)
        try:
            for instrument, symbol, bid, ask in (("WDO", "WDOZ26", 5422.0, 5422.5), ("WIN", "WINZ26", 130000, 130005)):
                with self.subTest(instrument=instrument):
                    now = datetime.now(timezone.utc)
                    MacroRepository(factory).save_success(instrument, {
                        "status": "no_relevant_news", "summary": "Nada relevante.", "items": [], "model_id": "test/macro",
                    }, rss_evidence=[], as_of=now, completed_at=now, prompt_version="macroeconomic-news-v6")
                    body = make_snapshot(instrument, symbol, bid, ask)
                    provider = FakeProvider({"action": "NO_SIGNAL", "reference_price": None, "stop_loss": None,
                                             "take_profit": None, "risk_reward": None, "confidence": "low",
                                             "scenario": "Sem sinal.", "model_id": "test/decision"})
                    with patch("backend.main.get_session_factory", return_value=factory), patch("backend.main.OpenRouterClient", return_value=provider):
                        response = asyncio.run(analyze(body))
                    result = json.loads(response.body)
                    self.assertEqual(response.status_code, 200)
                    validate_response(result, now=datetime.now(timezone.utc), expected_request_id=body["request_id"],
                                      expected_instrument=body["instrument"], tick_size=body["symbol_properties"]["tick_size"])
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
