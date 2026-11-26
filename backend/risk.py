"""Deterministic validation of model candidates against EA and broker limits."""

from __future__ import annotations

import math


class RiskValidationError(ValueError):
    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message


def _finite_positive(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _fail(code: str, message: str) -> None:
    raise RiskValidationError(code, message)


def validate_operational_candidate(candidate: dict, request: dict) -> dict:
    action = candidate.get("action")
    if action not in ("BUY", "SELL"):
        _fail("invalid_direction", "A direção proposta não é compatível com uma operação.")

    properties = request.get("symbol_properties", {})
    preferences = request.get("preferences", {})
    for name in ("point", "tick_size", "tick_value_loss", "tick_value_profit"):
        if not _finite_positive(properties.get(name)):
            _fail("symbol_properties_unavailable", "Propriedades de tick do símbolo indisponíveis.")
    point = float(properties["point"])
    tick_size = float(properties["tick_size"])
    tick_value_loss = float(properties["tick_value_loss"])
    tick_value_profit = float(properties["tick_value_profit"])
    stops_level_points = properties.get("stops_level_points")
    if isinstance(stops_level_points, bool) or not isinstance(stops_level_points, int) or stops_level_points < 0:
        _fail("symbol_properties_unavailable", "Distância mínima de stop do símbolo indisponível.")

    entry, stop, target = (candidate.get(name) for name in ("reference_price", "stop_loss", "take_profit"))
    if any(not _finite_positive(value) for value in (entry, stop, target)):
        _fail("invalid_prices", "Entrada, stop ou alvo não contém preço positivo válido.")
    entry, stop, target = float(entry), float(stop), float(target)
    quote = request.get("current_quote", {})
    expected_entry = quote.get("ask") if action == "BUY" else quote.get("bid")
    if not _finite_positive(expected_entry) or abs(entry - float(expected_entry)) > tick_size:
        _fail("entry_price_mismatch", "Preço de referência diverge da cotação enviada pelo EA.")

    if action == "BUY":
        if not stop < entry < target:
            _fail("invalid_price_order", "Preços da compra não estão na ordem esperada.")
        risk_distance, reward_distance = entry - stop, target - entry
    else:
        if not target < entry < stop:
            _fail("invalid_price_order", "Preços da venda não estão na ordem esperada.")
        risk_distance, reward_distance = stop - entry, entry - target

    for price in (entry, stop, target):
        steps = price / tick_size
        if abs(steps - round(steps)) > 1e-6:
            _fail("off_tick", "Entrada, stop ou alvo não respeita o tick size do símbolo.")

    minimum_distance = stops_level_points * point
    if risk_distance + 1e-12 < minimum_distance or reward_distance + 1e-12 < minimum_distance:
        _fail("stop_level_violation", "Stop ou alvo viola a distância mínima do broker.")

    max_stop_points = preferences.get("max_stop_points")
    if not _finite_positive(max_stop_points):
        _fail("risk_limit_unconfigured", "Configure um máximo de stop positivo.")
    stop_points = risk_distance / point
    if stop_points > float(max_stop_points) + 1e-8:
        _fail("max_stop_exceeded", "Stop excede o máximo configurado em pontos.")

    selected_rr = preferences.get("risk_reward")
    if selected_rr not in ("1:2", "1:3") or candidate.get("risk_reward") != selected_rr:
        _fail("risk_reward_mismatch", "Relação risco-retorno proposta diverge da preferência configurada.")
    target_multiple = 2.0 if selected_rr == "1:2" else 3.0
    if abs(reward_distance - risk_distance * target_multiple) > tick_size:
        _fail("risk_reward_mismatch", "Distâncias de preço não correspondem à relação risco-retorno dentro de um tick.")

    contracts = preferences.get("contracts")
    max_loss = preferences.get("max_loss_per_trade")
    round_trip_cost = preferences.get("round_trip_cost_per_contract")
    if not _finite_positive(contracts) or not _finite_positive(max_loss):
        _fail("risk_limit_unconfigured", "Configure quantidade e perda máxima positiva por operação.")
    if isinstance(round_trip_cost, bool) or not isinstance(round_trip_cost, (int, float)) or not math.isfinite(round_trip_cost) or round_trip_cost < 0:
        _fail("risk_limit_unconfigured", "Custo de ida e volta precisa ser um valor não negativo.")

    volume = float(contracts)
    cost = float(round_trip_cost) * volume
    gross_loss = risk_distance / tick_size * tick_value_loss * volume
    estimated_loss = gross_loss + cost
    if estimated_loss > float(max_loss) + 1e-9:
        _fail("max_loss_exceeded", "Perda estimada incluindo custos excede o limite por operação.")

    gross_reward = reward_distance / tick_size * tick_value_profit * volume
    net_reward = gross_reward - cost
    if net_reward <= 0:
        _fail("net_return_non_positive", "Custos de ida e volta eliminam o retorno esperado.")

    return {
        "direction": action,
        "entry_type": "MARKET",
        "reference_price": entry,
        "stop_loss": stop,
        "take_profit": target,
        "risk_reward": selected_rr,
        "scenario": candidate["scenario"],
        "confidence": candidate["confidence"],
        "estimated_loss": estimated_loss,
        "net_expected_reward": net_reward,
    }
