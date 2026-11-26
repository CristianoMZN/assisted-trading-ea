import unittest

from backend.prompts import PROMPT_VERSIONS, load_prompt, version_records
from backend.technical import calculate_indicators


def candles(count=25, *, missing_close_at=None):
    rows = []
    for index in range(count):
        close = 100.0 + index
        row = {
            "timestamp": f"2026-11-25T{index % 24:02d}:00:00Z",
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
        }
        if index == missing_close_at:
            del row["close"]
        rows.append(row)
    return rows


class TechnicalAnalysisTests(unittest.TestCase):
    def test_indicators_are_deterministic_and_versioned(self):
        snapshot = {"candles": candles()}
        first = calculate_indicators(snapshot)
        second = calculate_indicators(snapshot)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "ready")
        self.assertEqual(first["version"], "technical-indicators-v1")
        self.assertEqual(first["periods"], {"sma_fast": 5, "sma_slow": 20, "rsi": 14, "atr": 14})
        self.assertEqual(first["interpretation"]["trend"], "uptrend")

    def test_insufficient_candles_are_reported_without_inference(self):
        result = calculate_indicators({"candles": candles(10)})
        self.assertEqual(result["status"], "insufficient")
        self.assertIn("at_least_20_candles", result["missing"])

    def test_missing_ohlc_field_is_reported(self):
        result = calculate_indicators({"candles": candles(missing_close_at=3)})
        self.assertEqual(result["missing"], ["candles[3].close"])

    def test_prompts_have_stable_versions(self):
        for instrument in ("WIN", "WDO"):
            self.assertIn(PROMPT_VERSIONS["news_analysis"], load_prompt("news_analysis", instrument=instrument))
        self.assertIn(PROMPT_VERSIONS["decision"], load_prompt("decision"))
        self.assertIn(PROMPT_VERSIONS["technical_interpretation"], load_prompt("technical_interpretation"))
        self.assertEqual(len(version_records()), 4)
        self.assertIn({"component": "technical_indicators", "version": "technical-indicators-v1"}, version_records())


if __name__ == "__main__":
    unittest.main()
