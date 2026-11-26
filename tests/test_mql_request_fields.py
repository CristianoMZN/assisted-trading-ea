import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EA = ROOT / "MQL5/Experts/AssistedTradingEA"


class MqlRiskPreferenceContractTests(unittest.TestCase):
    def test_panel_edits_and_validates_all_risk_preferences(self):
        panel = (EA / "Include/Panel.mqh").read_text(encoding="utf-8")
        source = (EA / "AssistedTradingEA.mq5").read_text(encoding="utf-8")
        for field in ("RR", "MAX_STOP", "MAX_LOSS", "ROUND_TRIP_COST", "DAILY_LOSS"):
            with self.subTest(field=field):
                self.assertIn(f'PANEL_PREFIX + "{field}"', panel)
                self.assertIn(f'"ATEA_{field}"', source)
        for setting in ("risk_reward_preference", "max_stop_points", "max_loss_per_trade", "round_trip_cost_per_contract", "daily_loss_limit"):
            with self.subTest(setting=setting):
                self.assertIn(setting, source)
        self.assertIn("ValidateRiskPreferences", source)
        self.assertIn("Configure perda máxima diária positiva", source)

    def test_mql_snapshot_serializes_contract_and_symbol_properties(self):
        market_data = (EA / "Include/MarketData.mqh").read_text(encoding="utf-8")
        for key in (
            "schema_version", "symbol_properties", "point", "tick_size", "tick_value_loss",
            "tick_value_profit", "stops_level_points", "risk_reward", "max_stop_points",
            "max_loss_per_trade", "round_trip_cost_per_contract", "daily_loss_limit", "contracts",
        ):
            with self.subTest(key=key):
                self.assertIn(f'\\"{key}\\"', market_data)
        self.assertIn('\\"1.1\\"', market_data)


class MqlNoSignalContractTests(unittest.TestCase):
    def test_reason_codes_and_absent_sources_are_handled_fail_closed(self):
        client = (EA / "Include/BackendClient.mqh").read_text(encoding="utf-8")
        source = (EA / "AssistedTradingEA.mq5").read_text(encoding="utf-8")
        panel = (EA / "Include/Panel.mqh").read_text(encoding="utf-8")
        self.assertIn("IsStableReasonCode(analysis.reason_code)", client)
        self.assertIn('status == "empty" || status == "unavailable" || status == "not_configured"', client)
        self.assertIn('type == "macroeconomic_news"', client)
        self.assertIn('status == "available" || status == "no_relevant_news" || status == "unavailable"', client)
        self.assertIn("analysis.valid = true;", client)
        self.assertIn("analysis.actionable = false;", client)
        self.assertIn("analysis.reason_code", panel)
        self.assertIn("analysis.reason", panel)
        self.assertIn("ZeroMemory(g_analysis);", source)
        self.assertIn('manual ? "manual_response_rejected" : "response_rejected"', source)


class MqlDailyRiskTests(unittest.TestCase):
    def test_daily_pnl_and_close_are_scoped_to_ea_magic(self):
        daily = (EA / "Include/DailyRisk.mqh").read_text(encoding="utf-8")
        source = (EA / "AssistedTradingEA.mq5").read_text(encoding="utf-8")
        self.assertIn("HistorySelect(day_start, server_now)", daily)
        self.assertIn("DEAL_MAGIC) != magic", daily)
        self.assertIn("POSITION_MAGIC) != magic", daily)
        for field in ("DEAL_PROFIT", "DEAL_SWAP", "DEAL_COMMISSION", "DEAL_FEE"):
            self.assertIn(field, daily)
        self.assertIn("POSITION_PROFIT", daily)
        self.assertIn("POSITION_SWAP", daily)
        self.assertIn("CloseManagedPositions(InpMagicNumber", source)
        self.assertIn("UpdateDailyRisk();", source)

    def test_final_order_gate_rechecks_stop_and_net_costs(self):
        execution = (EA / "Include/Execution.mqh").read_text(encoding="utf-8")
        self.assertIn("actual_stop_points > max_stop_points", execution)
        self.assertIn("round_trip_cost_per_contract * volume", execution)
        self.assertIn("MathAbs(stop_profit) + total_cost", execution)
        self.assertIn("estimated_target_profit - total_cost", execution)
        self.assertIn("net_expected_reward <= 0", execution)

    def test_daily_block_survives_restart_and_resets_without_reenabling(self):
        source = (EA / "AssistedTradingEA.mq5").read_text(encoding="utf-8")
        panel = (EA / "Include/Panel.mqh").read_text(encoding="utf-8")
        self.assertIn("GlobalVariableSet(DailyBlockGlobalName()", source)
        self.assertIn("GlobalVariablesFlush()", source)
        self.assertIn("LoadDailyBlock(trading_day)", source)
        self.assertIn("if(stored_day < trading_day)", source)
        self.assertIn("g_daily_limit_reached = LoadDailyBlock(trading_day)", source)
        self.assertIn("Limite diário atingido; aguarde o próximo dia do servidor e reative manualmente", source)
        self.assertIn("DAILY_PNL", panel)
        self.assertIn("DAILY_STATE", panel)
        self.assertIn("DAILY_CLOSE", panel)


if __name__ == "__main__":
    unittest.main()
