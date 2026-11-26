#ifndef ASSISTED_TRADING_TYPES_MQH
#define ASSISTED_TRADING_TYPES_MQH

struct AnalysisData
  {
   bool valid;
   bool actionable;
   bool fixture;
   string request_id;
   string symbol;
   string direction;
   string risk_reward;
   string reason_code;
   string reason;
   string scenario;
   string confidence;
   double reference_price;
   double stop_loss;
   double take_profit;
   datetime created_at;
   datetime expires_at;
   string sources_summary;
  };

#endif
