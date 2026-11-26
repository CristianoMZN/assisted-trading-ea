#ifndef ASSISTED_TRADING_EXECUTION_MQH
#define ASSISTED_TRADING_EXECUTION_MQH

#include "Types.mqh"

bool HasPositionForSymbol(const string symbol)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetSymbol(i) == symbol)
         return true;
   return false;
  }

bool HasActiveOrderForSymbol(const string symbol)
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong ticket = OrderGetTicket(i);
      if(ticket > 0 && OrderGetString(ORDER_SYMBOL) == symbol)
         return true;
     }
   return false;
  }

bool AcquireExecutionLock(const string symbol, string &lock_name, double &lock_token)
  {
   string safe_symbol = symbol;
   StringReplace(safe_symbol, ".", "_");
   StringReplace(safe_symbol, "#", "_");
   lock_name = "ATEA_" + IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN)) + "_" + StringSubstr(safe_symbol, 0, 30);
   if(!GlobalVariableCheck(lock_name) && !GlobalVariableTemp(lock_name) && !GlobalVariableCheck(lock_name))
      return false;
   double now = (double)TimeGMT();
   double observed = GlobalVariableGet(lock_name);
   if(observed > now)
      return false;
   lock_token = now + 1800.0 + (double)(GetTickCount() % 1000) / 1000.0;
   return GlobalVariableSetOnCondition(lock_name, lock_token, observed);
  }

void ReleaseExecutionLock(const string lock_name, const double lock_token)
  {
   if(StringLen(lock_name) > 0 && lock_token > 0 && GlobalVariableCheck(lock_name))
      GlobalVariableSetOnCondition(lock_name, 0.0, lock_token);
  }

bool IsPriceOnTick(const double price, const double tick_size)
  {
   if(tick_size <= 0)
      return false;
   double steps = price / tick_size;
   return (MathAbs(steps - MathRound(steps)) < 0.000001);
  }

bool ValidateAndSendMarketOrder(const AnalysisData &analysis, const string symbol, const double volume,
                                const double max_loss, const double max_stop_points,
                                const double round_trip_cost_per_contract,
                                const ulong magic, const int deviation_points,
                                const int max_quote_age_seconds, MqlTradeResult &result,
                                bool &ambiguous, string &error)
  {
   ZeroMemory(result);
   ambiguous = false;
   error = "";
   if(!analysis.valid || !analysis.actionable || analysis.fixture)
     {
      error = "Análise não pode ser executada";
      return false;
     }
   if(analysis.symbol != symbol || StringLen(symbol) == 0 ||
      !SymbolSelect(symbol, true) || SymbolInfoInteger(symbol, SYMBOL_SELECT) == 0)
     {
      error = "Símbolo da recomendação não corresponde ao símbolo negociável selecionado";
      return false;
     }
   if(TimeGMT() >= analysis.expires_at)
     {
      error = "Resposta do backend venceu antes do envio";
      return false;
     }
   if(HasPositionForSymbol(symbol) || HasActiveOrderForSymbol(symbol))
     {
      error = "Já existe posição ou ordem ativa neste símbolo";
      return false;
     }
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED) ||
      !AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))
     {
      error = "Negociação algorítmica não está habilitada no terminal/conta";
      return false;
     }
   if(!MathIsValidNumber(max_loss) || max_loss <= 0 ||
      !MathIsValidNumber(max_stop_points) || max_stop_points <= 0 ||
      !MathIsValidNumber(round_trip_cost_per_contract) || round_trip_cost_per_contract < 0)
     {
      error = "Configure perda máxima, stop máximo e custo válidos antes de ativar";
      return false;
     }

   double volume_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double volume_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double volume_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(volume < volume_min || volume > volume_max || volume_step <= 0 ||
      MathAbs((volume - volume_min) / volume_step - MathRound((volume - volume_min) / volume_step)) > 0.000001)
     {
      error = StringFormat("Quantidade inválida: mínimo %s, máximo %s, passo %s",
                           DoubleToString(volume_min, 4), DoubleToString(volume_max, 4), DoubleToString(volume_step, 4));
      return false;
     }

   MqlTick tick;
   if(!SymbolInfoTick(symbol, tick) || tick.bid <= 0 || tick.ask < tick.bid)
     {
      error = "Cotação atual indisponível ou inconsistente";
      return false;
     }
   datetime current_utc = TimeGMT();
   int server_utc_offset = (int)(TimeTradeServer() - current_utc);
   datetime tick_utc = tick.time - server_utc_offset;
   if(tick_utc <= 0 || current_utc - tick_utc > max_quote_age_seconds)
     {
      error = "Cotação ficou desatualizada antes do envio";
      return false;
     }
   double tick_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   long stops_level = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   if(tick_size <= 0 || point <= 0 || !IsPriceOnTick(analysis.stop_loss, tick_size) ||
      !IsPriceOnTick(analysis.take_profit, tick_size))
     {
      error = "Stop ou alvo não respeita o tick size do símbolo";
      return false;
     }

   ENUM_ORDER_TYPE order_type = (analysis.direction == "BUY" ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double market_price = (order_type == ORDER_TYPE_BUY ? tick.ask : tick.bid);
   double minimum_distance = (double)stops_level * point;
   if(order_type == ORDER_TYPE_BUY)
     {
      if(analysis.stop_loss >= market_price || analysis.take_profit <= market_price ||
         market_price - analysis.stop_loss < minimum_distance || analysis.take_profit - market_price < minimum_distance)
        {
         error = "Stop/alvo incompatível com a cotação atual ou distância mínima do broker";
         return false;
        }
     }
   else
     {
      if(analysis.stop_loss <= market_price || analysis.take_profit >= market_price ||
         analysis.stop_loss - market_price < minimum_distance || market_price - analysis.take_profit < minimum_distance)
        {
         error = "Stop/alvo incompatível com a cotação atual ou distância mínima do broker";
         return false;
        }
     }

   double actual_risk = 0.0;
   double actual_reward = 0.0;
   if(order_type == ORDER_TYPE_BUY)
     {
      actual_risk = market_price - analysis.stop_loss;
      actual_reward = analysis.take_profit - market_price;
     }
   else
     {
      actual_risk = analysis.stop_loss - market_price;
      actual_reward = market_price - analysis.take_profit;
     }
   double target_multiple = (analysis.risk_reward == "1:2" ? 2.0 : 3.0);
   if(MathAbs(actual_reward - actual_risk * target_multiple) > tick_size)
     {
      error = "Cotação de mercado mudou; relação risco-retorno saiu da faixa permitida";
      return false;
     }

   double actual_stop_points = actual_risk / point;
   if(actual_stop_points > max_stop_points + 0.000001)
     {
      error = StringFormat("Stop atual %.2f pontos excede limite %.2f pontos",
                           actual_stop_points, max_stop_points);
      return false;
     }

   double stop_profit = 0.0;
   if(!OrderCalcProfit(order_type, symbol, volume, market_price, analysis.stop_loss, stop_profit))
     {
      error = StringFormat("Não foi possível estimar a perda no stop (%d)", GetLastError());
      return false;
     }
   double total_cost = round_trip_cost_per_contract * volume;
   double estimated_loss = MathAbs(stop_profit) + total_cost;
   if(estimated_loss > max_loss)
     {
      error = StringFormat("Perda estimada %s excede limite configurado %s",
                           DoubleToString(estimated_loss, 2), DoubleToString(max_loss, 2));
      return false;
     }
   double estimated_target_profit = 0.0;
   if(!OrderCalcProfit(order_type, symbol, volume, market_price, analysis.take_profit, estimated_target_profit))
     {
      error = StringFormat("Não foi possível estimar o retorno no alvo (%d)", GetLastError());
      return false;
     }
   double net_expected_reward = estimated_target_profit - total_cost;
   if(net_expected_reward <= 0)
     {
      error = "Custos de ida e volta eliminam o retorno esperado";
      return false;
     }

   MqlTradeRequest request;
   MqlTradeCheckResult check;
   ZeroMemory(request);
   ZeroMemory(check);
   request.action = TRADE_ACTION_DEAL;
   request.symbol = symbol;
   request.magic = magic;
   request.volume = volume;
   request.type = order_type;
   request.price = NormalizeDouble(market_price, digits);
   request.sl = NormalizeDouble(analysis.stop_loss, digits);
   request.tp = NormalizeDouble(analysis.take_profit, digits);
   request.deviation = deviation_points;
   request.comment = "AssistedTradingEA";
   long fill_mode = SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   long order_modes = SymbolInfoInteger(symbol, SYMBOL_ORDER_MODE);
   if((order_modes & SYMBOL_ORDER_MARKET) != SYMBOL_ORDER_MARKET ||
      (order_modes & SYMBOL_ORDER_SL) != SYMBOL_ORDER_SL ||
      (order_modes & SYMBOL_ORDER_TP) != SYMBOL_ORDER_TP)
     {
      error = "Símbolo não permite ordem a mercado protegida por SL e TP";
      return false;
     }
   if((fill_mode & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      request.type_filling = ORDER_FILLING_FOK;
   else if((fill_mode & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      request.type_filling = ORDER_FILLING_IOC;
   else
     {
      error = "Broker não oferece política FOK/IOC para ordem a mercado";
      return false;
     }
   if(!OrderCheck(request, check) || check.retcode != 0)
     {
      error = StringFormat("OrderCheck rejeitou a ordem (%u): %s", check.retcode, check.comment);
      return false;
     }

   ResetLastError();
   bool sent = OrderSend(request, result);
   if(!sent)
     {
      ambiguous = true;
      error = StringFormat("OrderSend falhou (%d, retcode %u): %s", GetLastError(), result.retcode, result.comment);
      return false;
     }
   if(result.retcode != TRADE_RETCODE_DONE && result.retcode != TRADE_RETCODE_DONE_PARTIAL)
     {
      ambiguous = (result.retcode == TRADE_RETCODE_PLACED || result.retcode == TRADE_RETCODE_TIMEOUT ||
                   result.retcode == TRADE_RETCODE_CONNECTION);
      error = StringFormat("Servidor não confirmou execução (retcode %u): %s", result.retcode, result.comment);
      return false;
     }
   return true;
  }

#endif
