// Synthetic WDO transport test. Paste into Hoppscotch > Pre-request Script.
// The raw JSON request body must contain only: <<freshMarketSnapshot>>
// Edit these inputs before pressing Send. A new snapshot is generated on every Send.
const input = {
  brokerSymbol: "WDOZ26",
  bid: 5422.0,
  ask: 5422.5,
  tickSize: 0.5,
  point: 0.01,
  tickValueLoss: 0.5,
  tickValueProfit: 0.5,
  stopsLevelPoints: 0,
  digits: 1,
  riskReward: "1:2",
  maxStopPoints: 100.0,
  maxLossPerTrade: 200.0,
  roundTripCostPerContract: 1.5,
  dailyLossLimit: 500.0,
  contracts: 1.0,
};

if (!(typeof input.brokerSymbol === "string" && input.brokerSymbol.length > 0 &&
      [input.bid, input.ask, input.tickSize, input.point, input.tickValueLoss,
       input.tickValueProfit, input.maxStopPoints, input.maxLossPerTrade,
       input.roundTripCostPerContract, input.dailyLossLimit, input.contracts].every(Number.isFinite) &&
      input.bid > 0 && input.ask >= input.bid && input.tickSize > 0 && input.point > 0 &&
      input.tickValueLoss > 0 && input.tickValueProfit > 0 && input.maxStopPoints > 0 &&
      input.maxLossPerTrade > 0 && input.roundTripCostPerContract >= 0 &&
      input.dailyLossLimit > 0 && input.contracts > 0 &&
      Number.isInteger(input.stopsLevelPoints) && input.stopsLevelPoints >= 0 &&
      Number.isInteger(input.digits) && input.digits >= 0 && input.digits <= 12 &&
      (input.riskReward === "1:2" || input.riskReward === "1:3"))) {
  throw new Error("Parâmetros de símbolo, cotação ou risco inválidos no script de teste");
}

const now = new Date();
const iso = (milliseconds) => new Date(milliseconds).toISOString();
const minute = 60_000;
const tick = input.tickSize;
const base = Math.round(input.ask / tick) * tick;
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
  instrument: { logical_symbol: "WDO", broker_symbol: input.brokerSymbol },
  symbol_properties: {
    point: input.point,
    tick_size: tick,
    tick_value_loss: input.tickValueLoss,
    tick_value_profit: input.tickValueProfit,
    stops_level_points: input.stopsLevelPoints,
    digits: input.digits,
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
    bid: input.bid,
    ask: input.ask,
    last: input.ask,
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
    risk_reward: input.riskReward,
    max_stop_points: input.maxStopPoints,
    max_loss_per_trade: input.maxLossPerTrade,
    round_trip_cost_per_contract: input.roundTripCostPerContract,
    daily_loss_limit: input.dailyLossLimit,
    contracts: input.contracts,
  },
};

pw.env.set("freshMarketSnapshot", JSON.stringify(snapshot));
