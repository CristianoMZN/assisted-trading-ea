"""Generate a current, synthetic contract-1.1 snapshot for HTTP smoke tests."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.backend_contract import validate_request


def stamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def make_snapshot(instrument: str, broker_symbol: str, bid: float, ask: float) -> dict:
    template = Path(__file__).resolve().parents[1] / "contracts/examples/request-valid.json"
    payload = json.loads(template.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).replace(microsecond=0)
    payload["request_id"] = __import__("uuid").uuid4().__str__()
    payload["sent_at"] = stamp(now)
    payload["instrument"] = {"logical_symbol": instrument, "broker_symbol": broker_symbol}
    payload["window"] = {"from": stamp(now - timedelta(days=7)), "to": stamp(now)}
    payload["history_first_available_at"] = stamp(now - timedelta(days=7, minutes=5))
    payload["current_quote"].update({"timestamp": stamp(now), "bid": bid, "ask": ask, "last": ask})
    payload["tick_flow"].update({"from": stamp(now - timedelta(minutes=1)), "to": stamp(now)})
    tick = payload["symbol_properties"]["tick_size"]
    base = round(ask / tick) * tick
    payload["candles"] = []
    for index in range(20):
        close = base + (index - 19) * tick
        payload["candles"].append({
            "timestamp": stamp(now - timedelta(minutes=5 * (20 - index))),
            "open": close - tick, "high": close + tick, "low": close - 2 * tick,
            "close": close, "tick_volume": 100, "real_volume": None,
            "buy_volume": None, "sell_volume": None,
        })
    validate_request(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instrument", choices=("WIN", "WDO"), required=True)
    parser.add_argument("--broker-symbol", required=True)
    parser.add_argument("--bid", required=True, type=float)
    parser.add_argument("--ask", required=True, type=float)
    args = parser.parse_args()
    if args.bid <= 0 or args.ask < args.bid:
        parser.error("require 0 < bid <= ask")
    print(json.dumps(make_snapshot(args.instrument, args.broker_symbol, args.bid, args.ask), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
