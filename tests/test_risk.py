import copy
import json
import unittest
from pathlib import Path

from backend.risk import RiskValidationError, validate_operational_candidate


class DeterministicRiskTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.request = json.loads((root / "contracts/examples/request-valid.json").read_text())
        self.candidate = {
            "action": "BUY",
            "reference_price": 5422.5,
            "stop_loss": 5421.5,
            "take_profit": 5424.5,
            "risk_reward": "1:2",
            "confidence": "medium",
            "scenario": "Test candidate.",
        }

    def assert_reason(self, expected, *, candidate=None, request=None):
        with self.assertRaises(RiskValidationError) as caught:
            validate_operational_candidate(candidate or self.candidate, request or self.request)
        self.assertEqual(caught.exception.reason_code, expected)

    def test_valid_candidate_includes_cost_in_loss_and_net_reward(self):
        result = validate_operational_candidate(self.candidate, self.request)
        self.assertEqual(result["direction"], "BUY")
        self.assertAlmostEqual(result["estimated_loss"], 2.5)
        self.assertAlmostEqual(result["net_expected_reward"], 0.5)

    def test_invalid_direction_is_rejected(self):
        candidate = dict(self.candidate, action="HOLD")
        self.assert_reason("invalid_direction", candidate=candidate)

    def test_entry_must_match_current_quote(self):
        candidate = dict(self.candidate, reference_price=5424.0, stop_loss=5423.0, take_profit=5426.0)
        self.assert_reason("entry_price_mismatch", candidate=candidate)

    def test_prices_must_follow_direction(self):
        candidate = dict(self.candidate, stop_loss=5423.0)
        self.assert_reason("invalid_price_order", candidate=candidate)

    def test_off_tick_prices_are_rejected(self):
        candidate = dict(self.candidate, stop_loss=5421.4)
        self.assert_reason("off_tick", candidate=candidate)

    def test_broker_stop_level_is_enforced(self):
        request = copy.deepcopy(self.request)
        request["symbol_properties"]["stops_level_points"] = 101
        self.assert_reason("stop_level_violation", request=request)

    def test_maximum_stop_is_enforced(self):
        request = copy.deepcopy(self.request)
        request["preferences"]["max_stop_points"] = 99
        self.assert_reason("max_stop_exceeded", request=request)

    def test_risk_reward_geometry_and_preference_are_enforced(self):
        candidate = dict(self.candidate, take_profit=5423.5)
        self.assert_reason("risk_reward_mismatch", candidate=candidate)
        request = copy.deepcopy(self.request)
        request["preferences"]["risk_reward"] = "1:3"
        self.assert_reason("risk_reward_mismatch", request=request)

    def test_maximum_loss_includes_costs(self):
        request = copy.deepcopy(self.request)
        request["preferences"]["max_loss_per_trade"] = 2.4
        self.assert_reason("max_loss_exceeded", request=request)

    def test_net_return_must_remain_positive_after_cost(self):
        request = copy.deepcopy(self.request)
        request["preferences"]["round_trip_cost_per_contract"] = 2.0
        self.assert_reason("net_return_non_positive", request=request)


if __name__ == "__main__":
    unittest.main()
