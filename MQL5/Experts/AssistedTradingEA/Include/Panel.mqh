#ifndef ASSISTED_TRADING_PANEL_MQH
#define ASSISTED_TRADING_PANEL_MQH

#include "Types.mqh"

string PANEL_PREFIX = "ATEA_";

void PanelCreateLabel(const string name, const int y)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 18);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 9);
   ObjectSetString(0, name, OBJPROP_FONT, "Tahoma");
  }

void PanelCreateEdit(const string name, const int x, const int y, const int width, const string value)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_EDIT, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, width);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, 22);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clrBlack);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, clrWhite);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 9);
   ObjectSetString(0, name, OBJPROP_TEXT, value);
  }

void PanelCreate(const double initial_volume, const int initial_interval, const bool automation_enabled,
                 const string initial_risk_reward, const double max_stop_points,
                 const double max_loss_per_trade, const double round_trip_cost,
                 const double daily_loss_limit)
  {
   string bg = PANEL_PREFIX + "BG";
   if(ObjectFind(0, bg) < 0)
      ObjectCreate(0, bg, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, bg, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, bg, OBJPROP_XDISTANCE, 8);
   ObjectSetInteger(0, bg, OBJPROP_YDISTANCE, 15);
   ObjectSetInteger(0, bg, OBJPROP_XSIZE, 500);
   ObjectSetInteger(0, bg, OBJPROP_YSIZE, 585);
   ObjectSetInteger(0, bg, OBJPROP_BGCOLOR, C'24,30,38');
   ObjectSetInteger(0, bg, OBJPROP_COLOR, C'72,82,94');
   ObjectSetInteger(0, bg, OBJPROP_BACK, false);
   ObjectSetInteger(0, bg, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, bg, OBJPROP_HIDDEN, true);

   PanelCreateLabel(PANEL_PREFIX + "TITLE", 24);
   ObjectSetInteger(0, PANEL_PREFIX + "TITLE", OBJPROP_FONTSIZE, 11);
   PanelCreateLabel(PANEL_PREFIX + "SYMBOL", 50);
   PanelCreateLabel(PANEL_PREFIX + "STATUS", 72);
   PanelCreateLabel(PANEL_PREFIX + "DECISION", 96);
   PanelCreateLabel(PANEL_PREFIX + "SCENARIO", 120);
   PanelCreateLabel(PANEL_PREFIX + "REASON_DETAIL", 138);
   PanelCreateLabel(PANEL_PREFIX + "LEVELS", 154);
   PanelCreateLabel(PANEL_PREFIX + "CONFIDENCE", 178);
   PanelCreateLabel(PANEL_PREFIX + "SOURCES", 202);
   PanelCreateLabel(PANEL_PREFIX + "RR_LABEL", 238);
   PanelCreateLabel(PANEL_PREFIX + "MAX_STOP_LABEL", 266);
   PanelCreateLabel(PANEL_PREFIX + "MAX_LOSS_LABEL", 294);
   PanelCreateLabel(PANEL_PREFIX + "COST_LABEL", 322);
   PanelCreateLabel(PANEL_PREFIX + "DAILY_LABEL", 350);
   PanelCreateLabel(PANEL_PREFIX + "VOLUME_LABEL", 378);
   PanelCreateLabel(PANEL_PREFIX + "INTERVAL_LABEL", 406);
   PanelCreateLabel(PANEL_PREFIX + "POLL", 464);
   PanelCreateLabel(PANEL_PREFIX + "POSITION", 490);
   PanelCreateLabel(PANEL_PREFIX + "DAILY_PNL", 516);
   PanelCreateLabel(PANEL_PREFIX + "DAILY_STATE", 538);
   PanelCreateLabel(PANEL_PREFIX + "DAILY_CLOSE", 560);

   PanelCreateEdit(PANEL_PREFIX + "RR", 270, 234, 100, initial_risk_reward);
   PanelCreateEdit(PANEL_PREFIX + "MAX_STOP", 270, 262, 100, DoubleToString(max_stop_points, 2));
   PanelCreateEdit(PANEL_PREFIX + "MAX_LOSS", 270, 290, 100, DoubleToString(max_loss_per_trade, 2));
   PanelCreateEdit(PANEL_PREFIX + "ROUND_TRIP_COST", 270, 318, 100, DoubleToString(round_trip_cost, 2));
   PanelCreateEdit(PANEL_PREFIX + "DAILY_LOSS", 270, 346, 100, DoubleToString(daily_loss_limit, 2));
   PanelCreateEdit(PANEL_PREFIX + "VOLUME", 270, 374, 100, DoubleToString(initial_volume, 2));
   PanelCreateEdit(PANEL_PREFIX + "INTERVAL", 270, 402, 72, IntegerToString(initial_interval));

   string button_name = PANEL_PREFIX + "AUTO";
   if(ObjectFind(0, button_name) < 0)
      ObjectCreate(0, button_name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, button_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, button_name, OBJPROP_XDISTANCE, 250);
   ObjectSetInteger(0, button_name, OBJPROP_YDISTANCE, 430);
   ObjectSetInteger(0, button_name, OBJPROP_XSIZE, 205);
   ObjectSetInteger(0, button_name, OBJPROP_YSIZE, 24);
   ObjectSetInteger(0, button_name, OBJPROP_FONTSIZE, 9);
   ObjectSetInteger(0, button_name, OBJPROP_BGCOLOR, (automation_enabled ? clrDarkGreen : clrMaroon));
   ObjectSetString(0, button_name, OBJPROP_TEXT, (automation_enabled ? "AUTOMAÇÃO: LIGADA" : "AUTOMAÇÃO: DESLIGADA"));
   ObjectSetInteger(0, button_name, OBJPROP_HIDDEN, true);

   ObjectSetString(0, PANEL_PREFIX + "TITLE", OBJPROP_TEXT, "BOLETA ASSISTIDA · MQL5 / BACKEND");
   ObjectSetString(0, PANEL_PREFIX + "RR_LABEL", OBJPROP_TEXT, "RR (1:2 ou 1:3):");
   ObjectSetString(0, PANEL_PREFIX + "MAX_STOP_LABEL", OBJPROP_TEXT, "Stop máximo (pontos):");
   ObjectSetString(0, PANEL_PREFIX + "MAX_LOSS_LABEL", OBJPROP_TEXT, "Perda/operação (moeda conta):");
   ObjectSetString(0, PANEL_PREFIX + "COST_LABEL", OBJPROP_TEXT, "Custo/contrato (moeda conta):");
   ObjectSetString(0, PANEL_PREFIX + "DAILY_LABEL", OBJPROP_TEXT, "Perda diária (moeda conta):");
   ObjectSetString(0, PANEL_PREFIX + "VOLUME_LABEL", OBJPROP_TEXT, "Contratos:");
   ObjectSetString(0, PANEL_PREFIX + "INTERVAL_LABEL", OBJPROP_TEXT, "Polling (min):");
   ChartRedraw(0);
  }

void PanelSetAutomation(const bool enabled)
  {
   string button_name = PANEL_PREFIX + "AUTO";
   if(ObjectFind(0, button_name) < 0)
      return;
   ObjectSetString(0, button_name, OBJPROP_TEXT, (enabled ? "AUTOMAÇÃO: LIGADA" : "AUTOMAÇÃO: DESLIGADA"));
   ObjectSetInteger(0, button_name, OBJPROP_BGCOLOR, (enabled ? clrDarkGreen : clrMaroon));
   ObjectSetInteger(0, button_name, OBJPROP_STATE, false);
   ChartRedraw(0);
  }

double PanelReadVolume()
  {
   string value = ObjectGetString(0, PANEL_PREFIX + "VOLUME", OBJPROP_TEXT);
   return StringToDouble(value);
  }

string PanelReadRiskReward()
  {
   return ObjectGetString(0, PANEL_PREFIX + "RR", OBJPROP_TEXT);
  }

double PanelReadMaxStop()
  {
   return StringToDouble(ObjectGetString(0, PANEL_PREFIX + "MAX_STOP", OBJPROP_TEXT));
  }

double PanelReadMaxLoss()
  {
   return StringToDouble(ObjectGetString(0, PANEL_PREFIX + "MAX_LOSS", OBJPROP_TEXT));
  }

double PanelReadRoundTripCost()
  {
   return StringToDouble(ObjectGetString(0, PANEL_PREFIX + "ROUND_TRIP_COST", OBJPROP_TEXT));
  }

double PanelReadDailyLoss()
  {
   return StringToDouble(ObjectGetString(0, PANEL_PREFIX + "DAILY_LOSS", OBJPROP_TEXT));
  }

int PanelReadInterval()
  {
   string value = ObjectGetString(0, PANEL_PREFIX + "INTERVAL", OBJPROP_TEXT);
   return (int)StringToInteger(value);
  }

bool PanelHandleChartEvent(const int id, const string &object_name, bool &automation_enabled,
                           double &volume, int &interval_minutes, string &risk_reward,
                           double &max_stop_points, double &max_loss_per_trade,
                           double &round_trip_cost, double &daily_loss_limit)
  {
   if(id == CHARTEVENT_OBJECT_CLICK && object_name == PANEL_PREFIX + "AUTO")
     {
      automation_enabled = !automation_enabled;
      PanelSetAutomation(automation_enabled);
      return true;
     }
   if(id == CHARTEVENT_OBJECT_ENDEDIT && object_name == PANEL_PREFIX + "VOLUME")
     {
      volume = PanelReadVolume();
      return true;
     }
   if(id == CHARTEVENT_OBJECT_ENDEDIT && object_name == PANEL_PREFIX + "INTERVAL")
     {
      interval_minutes = PanelReadInterval();
      return true;
     }
   if(id == CHARTEVENT_OBJECT_ENDEDIT && object_name == PANEL_PREFIX + "RR")
     {
      risk_reward = PanelReadRiskReward();
      return true;
     }
   if(id == CHARTEVENT_OBJECT_ENDEDIT && object_name == PANEL_PREFIX + "MAX_STOP")
     {
      max_stop_points = PanelReadMaxStop();
      return true;
     }
   if(id == CHARTEVENT_OBJECT_ENDEDIT && object_name == PANEL_PREFIX + "MAX_LOSS")
     {
      max_loss_per_trade = PanelReadMaxLoss();
      return true;
     }
   if(id == CHARTEVENT_OBJECT_ENDEDIT && object_name == PANEL_PREFIX + "ROUND_TRIP_COST")
     {
      round_trip_cost = PanelReadRoundTripCost();
      return true;
     }
   if(id == CHARTEVENT_OBJECT_ENDEDIT && object_name == PANEL_PREFIX + "DAILY_LOSS")
     {
      daily_loss_limit = PanelReadDailyLoss();
      return true;
     }
   return false;
  }

void PanelUpdate(const string symbol, const string status, const AnalysisData &analysis,
                 const bool automation_enabled, const int interval_minutes, const double volume,
                 const bool position_open, const bool execution_blocked,
                 const double daily_realized, const double daily_floating,
                 const double daily_total, const double daily_limit,
                 const bool daily_blocked, const string daily_close_failure)
  {
   string display_status = status;
   ObjectSetString(0, PANEL_PREFIX + "SYMBOL", OBJPROP_TEXT,
                   "Ativo: " + LogicalSymbolName() + " → " + symbol + " · M5 · janela 7 dias");
   ObjectSetString(0, PANEL_PREFIX + "STATUS", OBJPROP_TEXT, "Estado: " + status);
   string decision = "Decisão: sem sinal";
   string levels = "Entrada: —  |  Stop Loss: —  |  Take Profit: —";
   string scenario = "Cenário: aguardando resposta do backend";
   string reason_detail = "";
   string confidence = "Confiança: —";
   string sources = "Fontes: —";
   if(analysis.valid)
     {
      if(analysis.actionable)
        {
         decision = "Decisão: " + analysis.direction + " · mercado · RR " + analysis.risk_reward;
         levels = "Referência: " + DoubleToString(analysis.reference_price, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) +
                  "  |  SL: " + DoubleToString(analysis.stop_loss, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) +
                  "  |  TP: " + DoubleToString(analysis.take_profit, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
         scenario = "Cenário: " + analysis.scenario;
         confidence = "Confiança: " + analysis.confidence + " · expira " + TimeToString(analysis.expires_at, TIME_MINUTES | TIME_SECONDS);
         sources = "Fontes: " + analysis.sources_summary;
        }
      else
        {
         if(StringLen(analysis.reason_code) > 0)
           {
            decision = "Decisão: sem sinal · " + analysis.reason_code;
            string reason_text = "Motivo: " + analysis.reason;
            scenario = StringSubstr(reason_text, 0, 78);
            if(StringLen(reason_text) > 78)
               reason_detail = StringSubstr(reason_text, 78, 78);
           }
         else
           {
            decision = "Decisão: sem sinal · resposta válida do backend";
            scenario = "Cenário: " + analysis.scenario;
           }
         confidence = "Atualizada: " + TimeToString(analysis.created_at, TIME_MINUTES | TIME_SECONDS);
         sources = "Fontes: " + analysis.sources_summary;
        }
      if(analysis.fixture)
         display_status = "FIXTURE DE TESTE · sem execução real";
     }
   ObjectSetString(0, PANEL_PREFIX + "STATUS", OBJPROP_TEXT, "Estado: " + display_status);
   ObjectSetString(0, PANEL_PREFIX + "DECISION", OBJPROP_TEXT, decision);
   ObjectSetString(0, PANEL_PREFIX + "SCENARIO", OBJPROP_TEXT, scenario);
   ObjectSetString(0, PANEL_PREFIX + "REASON_DETAIL", OBJPROP_TEXT, reason_detail);
   ObjectSetString(0, PANEL_PREFIX + "LEVELS", OBJPROP_TEXT, levels);
   ObjectSetString(0, PANEL_PREFIX + "CONFIDENCE", OBJPROP_TEXT, confidence);
   ObjectSetString(0, PANEL_PREFIX + "SOURCES", OBJPROP_TEXT, sources);
   string poll_state = (automation_enabled ? "Automação ativa · polling a cada " + IntegerToString(interval_minutes) + " min" : "Automação desligada");
   if(position_open)
      poll_state = "Polling pausado · posição aberta no símbolo";
   if(execution_blocked)
      poll_state = "Execução bloqueada · verifique o estado da última solicitação";
   ObjectSetString(0, PANEL_PREFIX + "POLL", OBJPROP_TEXT, poll_state + " · volume " + DoubleToString(volume, 2));
   ObjectSetString(0, PANEL_PREFIX + "POSITION", OBJPROP_TEXT, position_open ? "Posição/ordem existente: nenhuma nova entrada será enviada" : "Sem posição ou ordem ativa no símbolo");
   ObjectSetString(0, PANEL_PREFIX + "DAILY_PNL", OBJPROP_TEXT,
                   StringFormat("P&L diário (%s) · realizado %.2f · flutuante %.2f · líquido %.2f",
                                AccountInfoString(ACCOUNT_CURRENCY), daily_realized, daily_floating, daily_total));
   ObjectSetString(0, PANEL_PREFIX + "DAILY_STATE", OBJPROP_TEXT,
                   StringFormat("Limite diário %.2f · estado: %s",
                                daily_limit, (daily_blocked ? "BLOQUEADO" : "normal")));
   string close_state = (StringLen(daily_close_failure) > 0 ?
                         "Falha ao fechar: " + StringSubstr(daily_close_failure, 0, 90) :
                         (daily_blocked ? "Posições deste EA fechadas ou nenhuma posição restante" : "Sem falha de fechamento"));
   ObjectSetString(0, PANEL_PREFIX + "DAILY_CLOSE", OBJPROP_TEXT, close_state);
   PanelSetAutomation(automation_enabled);
   ChartRedraw(0);
  }

void PanelRemove()
  {
   for(int i = ObjectsTotal(0) - 1; i >= 0; i--)
     {
      string name = ObjectName(0, i);
      if(StringFind(name, PANEL_PREFIX) == 0)
         ObjectDelete(0, name);
     }
  }

#endif
