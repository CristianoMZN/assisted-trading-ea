import copy
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from backend_contract import ContractError, validate_request, validate_response  # noqa: E402


def fixture(name):
    return json.loads((ROOT / "contracts" / "examples" / name).read_text(encoding="utf-8"))


class BackendContractTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 25, 14, 5, 30, tzinfo=timezone.utc)
        self.request = fixture("request-valid.json")
        self.response = fixture("response-valid.json")
        self.instrument = self.request["instrument"]

    def validate_response(self, response=None, now=None):
        validate_response(
            response or self.response,
            now=now or self.now,
            expected_request_id=self.request["request_id"],
            expected_instrument=self.instrument,
            tick_size=0.5,
        )

    def test_valid_request_and_response(self):
        validate_request(self.request)
        self.validate_response()

    def test_request_requires_valid_risk_preferences(self):
        request = copy.deepcopy(self.request)
        request["preferences"]["max_loss_per_trade"] = 0
        with self.assertRaisesRegex(ContractError, "max_loss_per_trade must be positive"):
            validate_request(request)

    def test_request_rejects_unsupported_risk_reward_preference(self):
        request = copy.deepcopy(self.request)
        request["preferences"]["risk_reward"] = "1:4"
        with self.assertRaisesRegex(ContractError, "risk_reward must be 1:2 or 1:3"):
            validate_request(request)

    def test_request_requires_symbol_tick_properties(self):
        request = copy.deepcopy(self.request)
        del request["symbol_properties"]["tick_value_loss"]
        with self.assertRaisesRegex(ContractError, "symbol_properties missing required fields: tick_value_loss"):
            validate_request(request)

    def test_missing_required_candle_field_is_rejected(self):
        request = copy.deepcopy(self.request)
        del request["candles"][0]["close"]
        with self.assertRaisesRegex(ContractError, "missing required fields: close"):
            validate_request(request)

    def test_history_must_reach_start_of_window(self):
        request = copy.deepcopy(self.request)
        request["history_first_available_at"] = "2026-11-19T14:05:00Z"
        with self.assertRaisesRegex(ContractError, "available history must reach"):
            validate_request(request)

    def test_inconsistent_ohlc_is_rejected(self):
        request = copy.deepcopy(self.request)
        request["candles"][0]["low"] = request["candles"][0]["open"] + 1
        with self.assertRaisesRegex(ContractError, "OHLC values are inconsistent"):
            validate_request(request)

    def test_stale_current_quote_is_rejected(self):
        request = copy.deepcopy(self.request)
        request["current_quote"]["timestamp"] = "2026-11-25T13:55:00Z"
        with self.assertRaisesRegex(ContractError, "current_quote timestamp"):
            validate_request(request)

    def test_expired_response_is_rejected(self):
        with self.assertRaisesRegex(ContractError, "response is not current"):
            self.validate_response(now=datetime(2026, 11, 25, 14, 6, 0, tzinfo=timezone.utc))

    def test_unknown_version_is_rejected(self):
        response = copy.deepcopy(self.response)
        response["schema_version"] = "2.0"
        with self.assertRaisesRegex(ContractError, "unsupported schema_version"):
            self.validate_response(response)

    def test_no_signal_has_no_actionable_decision(self):
        response = fixture("response-no-signal.json")
        self.validate_response(response)

    def test_no_signal_requires_stable_reason_code(self):
        response = copy.deepcopy(self.response)
        response["status"] = "no_signal"
        response["decision"] = None
        response["reason_code"] = "Risk Limit"
        response["reason"] = "Limite excedido."
        with self.assertRaisesRegex(ContractError, "reason_code must be stable snake_case"):
            self.validate_response(response)

    def test_incompatible_risk_reward_is_rejected(self):
        response = copy.deepcopy(self.response)
        response["decision"]["take_profit"] = 5425.5
        with self.assertRaisesRegex(ContractError, "do not match declared risk_reward"):
            self.validate_response(response)


if __name__ == "__main__":
    unittest.main()
