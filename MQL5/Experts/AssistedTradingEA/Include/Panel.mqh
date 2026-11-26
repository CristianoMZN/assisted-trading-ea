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

void PanelCreate(const double initial_volume, const int initial_interval, const bool automation_enabled)
  {
   string bg = PANEL_PREFIX + "BG";
   if(ObjectFind(0, bg) < 0)
      ObjectCreate(0, bg, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, bg, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, bg, OBJPROP_XDISTANCE, 8);
   ObjectSetInteger(0, bg, OBJPROP_YDISTANCE, 15);
   ObjectSetInteger(0, bg, OBJPROP_XSIZE, 500);
   ObjectSetInteger(0, bg, OBJPROP_YSIZE, 370);
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
   PanelCreateLabel(PANEL_PREFIX + "LEVELS", 154);
   PanelCreateLabel(PANEL_PREFIX + "CONFIDENCE", 178);
   PanelCreateLabel(PANEL_PREFIX + "SOURCES", 202);
   PanelCreateLabel(PANEL_PREFIX + "INTERVAL_LABEL", 238);
   PanelCreateLabel(PANEL_PREFIX + "VOLUME_LABEL", 272);
   PanelCreateLabel(PANEL_PREFIX + "POLL", 311);
   PanelCreateLabel(PANEL_PREFIX + "POSITION", 337);

   string interval_name = PANEL_PREFIX + "INTERVAL";
   if(ObjectFind(0, interval_name) < 0)
      ObjectCreate(0, interval_name, OBJ_EDIT, 0, 0, 0);
   ObjectSetInteger(0, interval_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, interval_name, OBJPROP_XDISTANCE, 120);
   ObjectSetInteger(0, interval_name, OBJPROP_YDISTANCE, 234);
   ObjectSetInteger(0, interval_name, OBJPROP_XSIZE, 58);
   ObjectSetInteger(0, interval_name, OBJPROP_YSIZE, 22);
   ObjectSetInteger(0, interval_name, OBJPROP_COLOR, clrBlack);
   ObjectSetInteger(0, interval_name, OBJPROP_BGCOLOR, clrWhite);
   ObjectSetInteger(0, interval_name, OBJPROP_FONTSIZE, 9);
   ObjectSetString(0, interval_name, OBJPROP_TEXT, IntegerToString(initial_interval));

   string edit_name = PANEL_PREFIX + "VOLUME";
   if(ObjectFind(0, edit_name) < 0)
      ObjectCreate(0, edit_name, OBJ_EDIT, 0, 0, 0);
   ObjectSetInteger(0, edit_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, edit_name, OBJPROP_XDISTANCE, 120);
   ObjectSetInteger(0, edit_name, OBJPROP_YDISTANCE, 268);
   ObjectSetInteger(0, edit_name, OBJPROP_XSIZE, 78);
   ObjectSetInteger(0, edit_name, OBJPROP_YSIZE, 22);
   ObjectSetInteger(0, edit_name, OBJPROP_COLOR, clrBlack);
   ObjectSetInteger(0, edit_name, OBJPROP_BGCOLOR, clrWhite);
   ObjectSetInteger(0, edit_name, OBJPROP_FONTSIZE, 9);
   ObjectSetString(0, edit_name, OBJPROP_TEXT, DoubleToString(initial_volume, 2));

   string button_name = PANEL_PREFIX + "AUTO";
   if(ObjectFind(0, button_name) < 0)
      ObjectCreate(0, button_name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, button_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, button_name, OBJPROP_XDISTANCE, 215);
   ObjectSetInteger(0, button_name, OBJPROP_YDISTANCE, 268);
   ObjectSetInteger(0, button_name, OBJPROP_XSIZE, 205);
   ObjectSetInteger(0, button_name, OBJPROP_YSIZE, 24);
   ObjectSetInteger(0, button_name, OBJPROP_FONTSIZE, 9);
   ObjectSetInteger(0, button_name, OBJPROP_BGCOLOR, (automation_enabled ? clrDarkGreen : clrMaroon));
   ObjectSetString(0, button_name, OBJPROP_TEXT, (automation_enabled ? "AUTOMAÇÃO: LIGADA" : "AUTOMAÇÃO: DESLIGADA"));
   ObjectSetInteger(0, button_name, OBJPROP_HIDDEN, true);

   ObjectSetString(0, PANEL_PREFIX + "TITLE", OBJPROP_TEXT, "BOLETA ASSISTIDA · MQL5 / BACKEND");
   ObjectSetString(0, PANEL_PREFIX + "INTERVAL_LABEL", OBJPROP_TEXT, "Polling (min):");
   ObjectSetString(0, PANEL_PREFIX + "VOLUME_LABEL", OBJPROP_TEXT, "Contratos:");
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

int PanelReadInterval()
  {
   string value = ObjectGetString(0, PANEL_PREFIX + "INTERVAL", OBJPROP_TEXT);
   return (int)StringToInteger(value);
  }

bool PanelHandleChartEvent(const int id, const string &object_name, bool &automation_enabled,
                           double &volume, int &interval_minutes)
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
   return false;
  }

void PanelUpdate(const string symbol, const string status, const AnalysisData &analysis,
                 const bool automation_enabled, const int interval_minutes, const double volume,
                 const bool position_open, const bool execution_blocked)
  {
   string display_status = status;
   ObjectSetString(0, PANEL_PREFIX + "SYMBOL", OBJPROP_TEXT,
                   "Ativo: " + LogicalSymbolName() + " → " + symbol + " · M5 · janela 7 dias");
   ObjectSetString(0, PANEL_PREFIX + "STATUS", OBJPROP_TEXT, "Estado: " + status);
   string decision = "Decisão: sem sinal";
   string levels = "Entrada: —  |  Stop Loss: —  |  Take Profit: —";
   string scenario = "Cenário: aguardando resposta do backend";
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
         decision = "Decisão: sem sinal · resposta válida do backend";
         confidence = "Atualizada: " + TimeToString(analysis.created_at, TIME_MINUTES | TIME_SECONDS);
         sources = "Fontes: " + analysis.sources_summary;
        }
      if(analysis.fixture)
         display_status = "FIXTURE DE TESTE · sem execução real";
     }
   ObjectSetString(0, PANEL_PREFIX + "STATUS", OBJPROP_TEXT, "Estado: " + display_status);
   ObjectSetString(0, PANEL_PREFIX + "DECISION", OBJPROP_TEXT, decision);
   ObjectSetString(0, PANEL_PREFIX + "SCENARIO", OBJPROP_TEXT, scenario);
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
