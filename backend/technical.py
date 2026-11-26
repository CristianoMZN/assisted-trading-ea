"""Deterministic technical indicators derived only from received M5 candles."""

from __future__ import annotations

import math
from statistics import fmean


INDICATOR_VERSION = "technical-indicators-v1"
REQUIRED_CANDLE_COUNT = 20


def calculate_indicators(snapshot: dict) -> dict:
    candles = snapshot.get("candles")
    if not isinstance(candles, list):
        return {"status": "insufficient", "missing": ["candles"], "version": INDICATOR_VERSION}
    if len(candles) < REQUIRED_CANDLE_COUNT:
        return {
            "status": "insufficient",
            "missing": [f"at_least_{REQUIRED_CANDLE_COUNT}_candles"],
            "available_candles": len(candles),
            "required_candles": REQUIRED_CANDLE_COUNT,
            "version": INDICATOR_VERSION,
        }

    required_fields = ("open", "high", "low", "close")
    for index, candle in enumerate(candles):
        if not isinstance(candle, dict):
            return {"status": "insufficient", "missing": [f"candles[{index}]"], "version": INDICATOR_VERSION}
        for field in required_fields:
            value = candle.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                return {
                    "status": "insufficient",
                    "missing": [f"candles[{index}].{field}"],
                    "version": INDICATOR_VERSION,
                }
        opening, high, low, close = (float(candle[field]) for field in required_fields)
        if low > min(opening, close) or high < max(opening, close) or low > high:
            return {
                "status": "insufficient",
                "missing": [f"candles[{index}].consistent_ohlc"],
                "version": INDICATOR_VERSION,
            }

    closes = [float(candle["close"]) for candle in candles]
    sma_5 = fmean(closes[-5:])
    sma_20 = fmean(closes[-20:])
    changes = [closes[index] - closes[index - 1] for index in range(len(closes) - 14, len(closes))]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    average_gain = fmean(gains)
    average_loss = fmean(losses)
    if average_gain == 0 and average_loss == 0:
        rsi_14 = 50.0
    elif average_loss == 0:
        rsi_14 = 100.0
    else:
        relative_strength = average_gain / average_loss
        rsi_14 = 100.0 - (100.0 / (1.0 + relative_strength))

    ranges = []
    for index in range(len(candles) - 14, len(candles)):
        candle = candles[index]
        previous_close = float(candles[index - 1]["close"])
        ranges.append(max(
            float(candle["high"]) - float(candle["low"]),
            abs(float(candle["high"]) - previous_close),
            abs(float(candle["low"]) - previous_close),
        ))
    atr_14 = fmean(ranges)
    close = closes[-1]
    if close > sma_20 and sma_5 > sma_20:
        trend = "uptrend"
    elif close < sma_20 and sma_5 < sma_20:
        trend = "downtrend"
    else:
        trend = "mixed"
    momentum = "overbought" if rsi_14 >= 70 else "oversold" if rsi_14 <= 30 else "neutral"
    return {
        "status": "ready",
        "version": INDICATOR_VERSION,
        "periods": {"sma_fast": 5, "sma_slow": 20, "rsi": 14, "atr": 14},
        "observations": len(candles),
        "observed_at": candles[-1].get("timestamp"),
        "values": {
            "sma_5": sma_5,
            "sma_20": sma_20,
            "rsi_14": rsi_14,
            "atr_14": atr_14,
            "last_close": close,
        },
        "interpretation": {"trend": trend, "momentum": momentum},
    }
