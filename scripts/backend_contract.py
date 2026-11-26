"""Small, dependency-free validation helpers for backend contract v1 fixtures."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from uuid import UUID


VERSION = "1.1"


class ContractError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _timestamp(value: object, field: str) -> datetime:
    _require(isinstance(value, str), f"{field} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{field} must be a valid ISO-8601 timestamp") from exc
    _require(parsed.tzinfo is not None, f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _object(value: object, field: str) -> dict:
    _require(isinstance(value, dict), f"{field} must be an object")
    return value


def _required(obj: dict, fields: tuple[str, ...], context: str) -> None:
    missing = [field for field in fields if field not in obj]
    _require(not missing, f"{context} missing required fields: {', '.join(missing)}")


def _instrument(value: object, context: str) -> dict:
    instrument = _object(value, f"{context}.instrument")
    _required(instrument, ("logical_symbol", "broker_symbol"), f"{context}.instrument")
    _require(instrument["logical_symbol"] in ("WIN", "WDO"), f"{context}.instrument.logical_symbol is unsupported")
    _require(isinstance(instrument["broker_symbol"], str) and instrument["broker_symbol"], f"{context}.instrument.broker_symbol is required")
    return instrument


def _preferences(value: object) -> dict:
    preferences = _object(value, "preferences")
    _required(preferences, ("risk_reward", "max_stop_points", "max_loss_per_trade", "round_trip_cost_per_contract", "daily_loss_limit", "contracts"), "preferences")
    _require(preferences["risk_reward"] in ("1:2", "1:3"), "preferences.risk_reward must be 1:2 or 1:3")
    for name in ("max_stop_points", "max_loss_per_trade", "round_trip_cost_per_contract", "daily_loss_limit", "contracts"):
        number = preferences[name]
        _require(isinstance(number, (int, float)) and not isinstance(number, bool) and math.isfinite(number), f"preferences.{name} must be a finite number")
        _require(number >= 0, f"preferences.{name} must be non-negative")
    _require(preferences["max_stop_points"] > 0, "preferences.max_stop_points must be positive")
    _require(preferences["max_loss_per_trade"] > 0, "preferences.max_loss_per_trade must be positive")
    _require(preferences["daily_loss_limit"] > 0, "preferences.daily_loss_limit must be positive")
    _require(preferences["contracts"] > 0, "preferences.contracts must be positive")
    return preferences


def _symbol_properties(value: object) -> dict:
    properties = _object(value, "symbol_properties")
    _required(properties, ("point", "tick_size", "tick_value_loss", "tick_value_profit", "stops_level_points", "digits"), "symbol_properties")
    for name in ("point", "tick_size", "tick_value_loss", "tick_value_profit"):
        number = properties[name]
        _require(isinstance(number, (int, float)) and not isinstance(number, bool) and math.isfinite(number) and number > 0, f"symbol_properties.{name} must be a finite positive number")
    _require(isinstance(properties["stops_level_points"], int) and not isinstance(properties["stops_level_points"], bool) and properties["stops_level_points"] >= 0, "symbol_properties.stops_level_points must be a non-negative integer")
    _require(isinstance(properties["digits"], int) and not isinstance(properties["digits"], bool) and 0 <= properties["digits"] <= 12, "symbol_properties.digits must be an integer from 0 through 12")
    return properties


def validate_request(payload: object) -> None:
    request = _object(payload, "request")
    _required(request, ("schema_version", "message_type", "request_id", "sent_at", "instrument", "symbol_properties", "timeframe", "window", "server_utc_offset_seconds", "history_first_available_at", "current_quote", "tick_flow", "candles", "unavailable_fields", "preferences"), "request")
    _require(request["schema_version"] == VERSION, "unsupported schema_version")
    _require(request["message_type"] == "market_snapshot", "message_type must be market_snapshot")
    try:
        UUID(request["request_id"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise ContractError("request_id must be a UUID") from exc
    sent_at = _timestamp(request["sent_at"], "sent_at")
    _instrument(request["instrument"], "request")
    _symbol_properties(request["symbol_properties"])
    _preferences(request["preferences"])
    _require(request["timeframe"] == "M5", "timeframe must be M5")

    window = _object(request["window"], "window")
    _required(window, ("from", "to"), "window")
    start = _timestamp(window["from"], "window.from")
    end = _timestamp(window["to"], "window.to")
    _require(end - start == timedelta(days=7), "window must cover exactly seven calendar days")
    _require(end == sent_at, "window.to must equal sent_at")
    _require(isinstance(request["server_utc_offset_seconds"], int), "server_utc_offset_seconds must be an integer")
    history_first = _timestamp(request["history_first_available_at"], "history_first_available_at")
    _require(history_first <= start, "available history must reach the beginning of the requested window")

    quote = _object(request["current_quote"], "current_quote")
    _required(quote, ("timestamp", "bid", "ask", "last", "volume", "volume_real", "flags"), "current_quote")
    quote_time = _timestamp(quote["timestamp"], "current_quote.timestamp")
    _require(timedelta(0) <= sent_at - quote_time <= timedelta(minutes=5), "current_quote timestamp must be current and within the polling window")
    _require(all(isinstance(quote[name], (int, float)) and math.isfinite(quote[name]) for name in ("bid", "ask", "last")), "current quote prices must be finite numbers")
    _require(quote["bid"] >= 0 and quote["ask"] >= quote["bid"] and quote["last"] >= 0, "current quote prices are inconsistent")
    _require(isinstance(quote["volume"], int) and quote["volume"] >= 0, "current quote volume must be non-negative integer")
    _require(quote["volume_real"] is None or (isinstance(quote["volume_real"], (int, float)) and quote["volume_real"] >= 0), "current quote volume_real must be non-negative or null")
    _require(isinstance(quote["flags"], int), "current quote flags must be an integer")

    flow = _object(request["tick_flow"], "tick_flow")
    _required(flow, ("from", "to", "classification_available", "buy_volume", "sell_volume"), "tick_flow")
    flow_start = _timestamp(flow["from"], "tick_flow.from")
    flow_end = _timestamp(flow["to"], "tick_flow.to")
    _require(flow_end == sent_at and timedelta(seconds=60) <= flow_end - flow_start <= timedelta(minutes=5), "tick_flow must cover the preceding 1–5 minutes")
    _require(isinstance(flow["classification_available"], bool), "tick_flow.classification_available must be boolean")
    if flow["classification_available"]:
        _require(all(isinstance(flow[name], (int, float)) and flow[name] >= 0 for name in ("buy_volume", "sell_volume")), "classified tick volumes must be non-negative numbers")
    else:
        _require(flow["buy_volume"] is None and flow["sell_volume"] is None, "unclassified tick volumes must be null")

    candles = request["candles"]
    _require(isinstance(candles, list) and candles, "candles must be a non-empty array")
    previous = None
    for index, raw in enumerate(candles):
        candle = _object(raw, f"candles[{index}]")
        fields = ("timestamp", "open", "high", "low", "close", "tick_volume", "real_volume", "buy_volume", "sell_volume")
        _required(candle, fields, f"candles[{index}]")
        stamp = _timestamp(candle["timestamp"], f"candles[{index}].timestamp")
        _require(start <= stamp <= end, f"candles[{index}] timestamp is outside window")
        _require(previous is None or stamp > previous, "candles must be strictly ordered by timestamp")
        previous = stamp
        prices = [candle[name] for name in ("open", "high", "low", "close")]
        _require(all(isinstance(price, (int, float)) and math.isfinite(price) for price in prices), f"candles[{index}] prices must be finite numbers")
        opening, high, low, close = prices
        _require(low <= min(opening, close) <= max(opening, close) <= high, f"candles[{index}] OHLC values are inconsistent")
        for name in ("tick_volume", "real_volume", "buy_volume", "sell_volume"):
            value = candle[name]
            _require(value is None or (isinstance(value, int) and not isinstance(value, bool) and value >= 0), f"candles[{index}].{name} must be a non-negative integer or null")
    unavailable = request["unavailable_fields"]
    _require(isinstance(unavailable, list) and all(isinstance(item, str) for item in unavailable), "unavailable_fields must be an array of strings")


def validate_response(
    payload: object,
    *,
    now: datetime,
    expected_request_id: str,
    expected_instrument: dict,
    tick_size: float,
) -> None:
    response = _object(payload, "response")
    _required(response, ("schema_version", "message_type", "request_id", "created_at", "expires_at", "instrument", "status", "decision", "reason_code", "reason", "sources"), "response")
    _require(response["schema_version"] == VERSION, "unsupported schema_version")
    _require(response["message_type"] == "analysis_response", "message_type must be analysis_response")
    _require(response["request_id"] == expected_request_id, "response request_id does not match request")
    created = _timestamp(response["created_at"], "created_at")
    expires = _timestamp(response["expires_at"], "expires_at")
    current = now.astimezone(timezone.utc)
    _require(created <= current < expires, "response is not current")
    _require(expires > created, "expires_at must follow created_at")
    actual_instrument = _instrument(response["instrument"], "response")
    _require(actual_instrument == expected_instrument, "response instrument does not match request")

    sources = response["sources"]
    _require(isinstance(sources, list), "sources must be an array")
    for index, raw in enumerate(sources):
        source = _object(raw, f"sources[{index}]")
        _required(source, ("type", "status", "source", "observed_at", "valid_until", "summary"), f"sources[{index}]")
        _timestamp(source["observed_at"], f"sources[{index}].observed_at")
        _timestamp(source["valid_until"], f"sources[{index}].valid_until")

    if response["status"] == "no_signal":
        _require(response["decision"] is None, "no_signal response must have decision=null")
        _require(isinstance(response["reason_code"], str) and response["reason_code"].strip() and response["reason_code"].replace("_", "").isalnum() and response["reason_code"] == response["reason_code"].lower(), "no_signal reason_code must be stable snake_case text")
        _require(isinstance(response["reason"], str) and response["reason"].strip(), "no_signal reason must be non-empty text")
        return

    _require(response["status"] == "actionable", "status must be actionable or no_signal")
    _require(response["reason_code"] is None and response["reason"] is None, "actionable response must not include a no_signal reason")
    decision = _object(response["decision"], "decision")
    _required(decision, ("direction", "entry_type", "reference_price", "stop_loss", "take_profit", "risk_reward", "scenario", "confidence"), "decision")
    _require(decision["direction"] in ("BUY", "SELL"), "direction must be BUY or SELL")
    _require(decision["entry_type"] == "MARKET", "entry_type must be MARKET")
    _require(decision["risk_reward"] in ("1:2", "1:3"), "risk_reward must be 1:2 or 1:3")
    _require(decision["confidence"] in ("low", "medium", "high"), "confidence is unsupported")
    entry, stop, target = (decision[name] for name in ("reference_price", "stop_loss", "take_profit"))
    _require(all(isinstance(value, (int, float)) and math.isfinite(value) for value in (entry, stop, target)), "decision prices must be finite numbers")
    if decision["direction"] == "BUY":
        _require(stop < entry < target, "BUY prices must satisfy stop_loss < entry < take_profit")
        risk, reward = entry - stop, target - entry
    else:
        _require(target < entry < stop, "SELL prices must satisfy take_profit < entry < stop_loss")
        risk, reward = stop - entry, entry - target
    expected_ratio = 2 if decision["risk_reward"] == "1:2" else 3
    _require(isinstance(tick_size, (int, float)) and tick_size > 0, "tick_size must be positive")
    _require(abs(reward - risk * expected_ratio) <= tick_size, "prices do not match declared risk_reward within one tick")
