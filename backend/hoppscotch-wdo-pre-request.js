// Synthetic WDO transport test. Paste into Hoppscotch > Pre-request Script.
// The raw JSON request body must contain only: <<marketSnapshot>>
const now = new Date();
const iso = (milliseconds) => new Date(milliseconds).toISOString();
const minute = 60_000;
const tick = 0.5;
const bid = 5422.0;
const ask = 5422.5;
const base = Math.round(ask / tick) * tick;
const requestId = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
  ? crypto.randomUUID()
  : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (digit) => {
      const value = Math.floor(Math.random() * 16);
      return (digit === "x" ? value : (value & 3) | 8).toString(16);
    });

const candles = Array.from({ length: 20 }, (_, index) => {
  const close = base + (index - 19) * tick;
  return {
    timestamp: iso(now.getTime() - (20 - index) * 5 * minute),
    open: close - tick,
    high: close + tick,
    low: close - 2 * tick,
    close,
    tick_volume: 100,
    real_volume: null,
    buy_volume: null,
    sell_volume: null,
  };
});

const snapshot = {
  schema_version: "1.1",
  message_type: "market_snapshot",
  request_id: requestId,
  sent_at: now.toISOString(),
  instrument: { logical_symbol: "WDO", broker_symbol: "WDOZ26" },
  symbol_properties: {
    point: 0.01,
    tick_size: tick,
    tick_value_loss: 0.5,
    tick_value_profit: 0.5,
    stops_level_points: 0,
    digits: 1,
  },
  timeframe: "M5",
  window: {
    from: iso(now.getTime() - 7 * 24 * 60 * minute),
    to: now.toISOString(),
  },
  server_utc_offset_seconds: -10800,
  history_first_available_at: iso(now.getTime() - 7 * 24 * 60 * minute - 5 * minute),
  current_quote: {
    timestamp: now.toISOString(),
    bid,
    ask,
    last: ask,
    volume: 1,
    volume_real: null,
    flags: 6,
  },
  tick_flow: {
    from: iso(now.getTime() - minute),
    to: now.toISOString(),
    classification_available: false,
    buy_volume: null,
    sell_volume: null,
  },
  candles,
  unavailable_fields: ["real_volume", "buy_volume", "sell_volume"],
  preferences: {
    risk_reward: "1:2",
    max_stop_points: 100.0,
    max_loss_per_trade: 200.0,
    round_trip_cost_per_contract: 1.5,
    daily_loss_limit: 500.0,
    contracts: 1.0,
  },
};

pw.env.set("marketSnapshot", JSON.stringify(snapshot));
