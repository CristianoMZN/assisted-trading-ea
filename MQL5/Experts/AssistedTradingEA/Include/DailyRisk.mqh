#ifndef ASSISTED_TRADING_DAILY_RISK_MQH
#define ASSISTED_TRADING_DAILY_RISK_MQH

#include <Trade/Trade.mqh>

datetime TradingDayStart()
  {
   datetime server_now = TimeTradeServer();
   if(server_now <= 0)
      return 0;
   MqlDateTime parts;
   TimeToStruct(server_now, parts);
   parts.hour = 0;
   parts.min = 0;
   parts.sec = 0;
   return StructToTime(parts);
  }

bool CalculateDailyPnl(const ulong magic, double &realized, double &floating,
                        double &total, string &error)
  {
   realized = 0.0;
   floating = 0.0;
   total = 0.0;
   error = "";
   datetime day_start = TradingDayStart();
   datetime server_now = TimeTradeServer();
   if(day_start <= 0 || server_now < day_start)
     {
      error = "Horário do servidor indisponível para apuração diária";
      return false;
     }
   if(!HistorySelect(day_start, server_now))
     {
      error = StringFormat("Não foi possível selecionar histórico diário (%d)", GetLastError());
      return false;
     }
   int deals = HistoryDealsTotal();
   for(int i = 0; i < deals; i++)
     {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0 || (ulong)HistoryDealGetInteger(ticket, DEAL_MAGIC) != magic)
         continue;
      realized += HistoryDealGetDouble(ticket, DEAL_PROFIT) +
                  HistoryDealGetDouble(ticket, DEAL_SWAP) +
                  HistoryDealGetDouble(ticket, DEAL_COMMISSION) +
                  HistoryDealGetDouble(ticket, DEAL_FEE);
     }
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || (ulong)PositionGetInteger(POSITION_MAGIC) != magic)
         continue;
      floating += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
     }
   total = realized + floating;
   return MathIsValidNumber(realized) && MathIsValidNumber(floating) && MathIsValidNumber(total);
  }

bool CloseManagedPositions(const ulong magic, const int deviation_points,
                           int &closed_count, string &failure_summary)
  {
   closed_count = 0;
   failure_summary = "";
   CTrade trade;
   trade.SetAsyncMode(false);
   trade.SetExpertMagicNumber(magic);
   trade.SetDeviationInPoints((ulong)MathMax(0, deviation_points));
   bool all_closed = true;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || (ulong)PositionGetInteger(POSITION_MAGIC) != magic)
         continue;
      string symbol = PositionGetString(POSITION_SYMBOL);
      bool requested = trade.PositionClose(ticket, (ulong)MathMax(0, deviation_points));
      uint retcode = trade.ResultRetcode();
      bool remains_open = PositionSelectByTicket(ticket);
      if(requested && (retcode == TRADE_RETCODE_DONE || retcode == TRADE_RETCODE_DONE_PARTIAL) && !remains_open)
        {
         closed_count++;
         continue;
        }
      all_closed = false;
      string detail = StringFormat("%s ticket %I64u retcode %u: %s", symbol, ticket, retcode, trade.ResultRetcodeDescription());
      if(StringLen(failure_summary) > 0)
         failure_summary += " | ";
      failure_summary += detail;
     }
   return all_closed;
  }

#endif
