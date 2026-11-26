#ifndef ASSISTED_TRADING_MARKET_DATA_MQH
#define ASSISTED_TRADING_MARKET_DATA_MQH

string JsonEscape(const string value)
  {
   string escaped = "";
   for(int i = 0; i < StringLen(value); i++)
     {
      string ch = StringSubstr(value, i, 1);
      if(ch == "\\") escaped += "\\\\";
      else if(ch == "\"") escaped += "\\\"";
      else if(ch == "\n") escaped += "\\n";
      else if(ch == "\r") escaped += "\\r";
      else if(ch == "\t") escaped += "\\t";
      else escaped += ch;
     }
   return escaped;
  }

string UtcIso8601(const datetime value)
  {
   MqlDateTime parts;
   TimeToStruct(value, parts);
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02dZ", parts.year, parts.mon, parts.day,
                       parts.hour, parts.min, parts.sec);
  }

string NewRequestId()
  {
   MathSrand((int)(GetTickCount() + TimeLocal()));
   uint a = (uint)TimeGMT();
   uint b = (uint)GetTickCount();
   uint c = (uint)MathRand();
   uint d = (uint)MathRand();
   uint e = (uint)MathRand();
   return StringFormat("%08X-%04X-4%03X-%04X-%08X%04X", a, (ushort)(b & 0xFFFF),
                       (ushort)(c & 0x0FFF), (ushort)(d & 0x3FFF), e, (ushort)MathRand());
  }

bool BuildMarketSnapshot(const string symbol, const int interval_minutes, string &request_id, string &body, string &error)
  {
   error = "";
   request_id = NewRequestId();
   datetime to_time = TimeGMT();
   datetime from_time = to_time - 7 * 24 * 60 * 60;
   int server_utc_offset = (int)(TimeTradeServer() - TimeGMT());
   datetime from_server_time = from_time + server_utc_offset;
   datetime to_server_time = to_time + server_utc_offset;
   if(!SymbolSelect(symbol, true))
     {
      error = "Símbolo não disponível no terminal: " + symbol;
      return false;
     }
   if(!SeriesInfoInteger(symbol, PERIOD_M5, SERIES_SYNCHRONIZED))
     {
      error = "Histórico M5 ainda não sincronizado para " + symbol;
      return false;
     }
   long first_history_time = 0;
   if(!SeriesInfoInteger(symbol, PERIOD_M5, SERIES_FIRSTDATE, first_history_time) ||
      first_history_time == 0 || first_history_time > (long)from_server_time)
     {
      error = "Histórico M5 não cobre o início da janela móvel de sete dias";
      return false;
     }

   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int copied = CopyRates(symbol, PERIOD_M5, from_server_time, to_server_time, rates);
   if(copied <= 0)
     {
      error = StringFormat("Sem candles M5 para a janela solicitada (erro %d)", GetLastError());
      return false;
     }

   MqlTick current_quote;
   if(!SymbolInfoTick(symbol, current_quote) || current_quote.bid <= 0 || current_quote.ask < current_quote.bid)
     {
      error = "Cotação bid/ask atual indisponível ou inconsistente";
      return false;
     }
   datetime quote_utc_time = current_quote.time - server_utc_offset;
   if(quote_utc_time <= 0 || to_time - quote_utc_time > MathMax(60, interval_minutes * 60))
     {
      error = "Última cotação está desatualizada para o intervalo de polling";
      return false;
     }

   datetime flow_from_utc = to_time - MathMax(60, interval_minutes * 60);
   datetime flow_from_server = flow_from_utc + server_utc_offset;
   MqlTick trade_ticks[];
   double buy_volume = 0.0;
   double sell_volume = 0.0;
   bool directional_volume_available = false;
   int copied_ticks = CopyTicksRange(symbol, trade_ticks, COPY_TICKS_TRADE,
                                     (ulong)flow_from_server * 1000, (ulong)to_server_time * 1000);
   if(copied_ticks > 0)
     {
      for(int tick_index = 0; tick_index < copied_ticks; tick_index++)
        {
         double volume = (trade_ticks[tick_index].volume_real > 0 ? trade_ticks[tick_index].volume_real : (double)trade_ticks[tick_index].volume);
         if((trade_ticks[tick_index].flags & TICK_FLAG_BUY) != 0)
           {
            buy_volume += volume;
            directional_volume_available = true;
           }
         if((trade_ticks[tick_index].flags & TICK_FLAG_SELL) != 0)
           {
            sell_volume += volume;
            directional_volume_available = true;
           }
        }
     }

   string logical = LogicalSymbolName();
   string sent_at = UtcIso8601(to_time);
   string quote_real_volume = (current_quote.volume_real > 0 ? DoubleToString(current_quote.volume_real, 8) : "null");
   body = "{\"schema_version\":\"1.1\",\"message_type\":\"market_snapshot\",\"request_id\":\"" +
          request_id + "\",\"sent_at\":\"" + sent_at + "\",\"instrument\":{\"logical_symbol\":\"" +
          logical + "\",\"broker_symbol\":\"" + JsonEscape(symbol) + "\"},\"timeframe\":\"M5\",\"window\":{\"from\":\"" +
          UtcIso8601(from_time) + "\",\"to\":\"" + sent_at + "\"},\"server_utc_offset_seconds\":" + IntegerToString(server_utc_offset) +
          ",\"history_first_available_at\":\"" + UtcIso8601((datetime)first_history_time - server_utc_offset) + "\"" +
          ",\"current_quote\":{\"timestamp\":\"" + UtcIso8601(quote_utc_time) + "\",\"bid\":" + DoubleToString(current_quote.bid, 8) +
          ",\"ask\":" + DoubleToString(current_quote.ask, 8) + ",\"last\":" + DoubleToString(current_quote.last, 8) +
          ",\"volume\":" + IntegerToString(current_quote.volume) + ",\"volume_real\":" + quote_real_volume +
          ",\"flags\":" + IntegerToString((int)current_quote.flags) + "}" +
          ",\"tick_flow\":{\"from\":\"" + UtcIso8601(flow_from_utc) + "\",\"to\":\"" + sent_at +
          "\",\"classification_available\":" + (directional_volume_available ? "true" : "false") +
          ",\"buy_volume\":" + (directional_volume_available ? DoubleToString(buy_volume, 4) : "null") +
          ",\"sell_volume\":" + (directional_volume_available ? DoubleToString(sell_volume, 4) : "null") + "},\"candles\":[";

   int written = 0;
   bool has_real_volume = false;
   datetime previous_bar_time = 0;
   for(int i = 0; i < copied; i++)
     {
      datetime candle_utc_time = rates[i].time - server_utc_offset;
      if(candle_utc_time < from_time || candle_utc_time > to_time)
         continue;
      if(previous_bar_time > 0 && rates[i].time <= previous_bar_time)
        {
         error = "Candles retornados fora da ordem temporal";
         return false;
        }
      if(!MathIsValidNumber(rates[i].open) || !MathIsValidNumber(rates[i].high) ||
         !MathIsValidNumber(rates[i].low) || !MathIsValidNumber(rates[i].close) ||
         rates[i].low > MathMin(rates[i].open, rates[i].close) ||
         rates[i].high < MathMax(rates[i].open, rates[i].close))
        {
         error = "Candles OHLC inconsistentes na janela solicitada";
         return false;
        }
      previous_bar_time = rates[i].time;
      if(written > 0)
         body += ",";
      string real_volume = "null";
      if(rates[i].real_volume > 0)
        {
         real_volume = IntegerToString(rates[i].real_volume);
         has_real_volume = true;
        }
      body += StringFormat("{\"timestamp\":\"%s\",\"open\":%s,\"high\":%s,\"low\":%s,\"close\":%s,\"tick_volume\":%s,\"real_volume\":%s,\"buy_volume\":null,\"sell_volume\":null}",
                           UtcIso8601(candle_utc_time), DoubleToString(rates[i].open, 8),
                           DoubleToString(rates[i].high, 8), DoubleToString(rates[i].low, 8),
                           DoubleToString(rates[i].close, 8), IntegerToString(rates[i].tick_volume),
                           real_volume);
      written++;
     }
   if(written == 0)
     {
      error = "Nenhum candle M5 válido dentro da janela de sete dias";
      return false;
     }

   body += "],\"unavailable_fields\":[\"buy_volume\",\"sell_volume\"";
   if(!has_real_volume)
      body += ",\"real_volume\"";
   body += "],\"preferences\":{\"risk_reward\":\"" + JsonEscape(InpRiskRewardPreference) +
           "\",\"max_stop_points\":" + DoubleToString(InpMaxStopPoints, 8) +
           ",\"max_loss_per_trade\":" + DoubleToString(InpMaxLossPerTrade, 8) +
           ",\"round_trip_cost_per_contract\":" + DoubleToString(InpRoundTripCostPerContract, 8) +
           ",\"daily_loss_limit\":" + DoubleToString(InpDailyLossLimit, 8) + "}}";
   return true;
  }

#endif
