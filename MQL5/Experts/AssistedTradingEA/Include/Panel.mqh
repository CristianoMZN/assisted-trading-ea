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

void PanelCreateSection(const string name, const int y, const int height, const color fill)
  {
   string section_name = PANEL_PREFIX + name;
   if(ObjectFind(0, section_name) < 0)
      ObjectCreate(0, section_name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, section_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, section_name, OBJPROP_XDISTANCE, 16);
   ObjectSetInteger(0, section_name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, section_name, OBJPROP_XSIZE, 504);
   ObjectSetInteger(0, section_name, OBJPROP_YSIZE, height);
   ObjectSetInteger(0, section_name, OBJPROP_BGCOLOR, fill);
   ObjectSetInteger(0, section_name, OBJPROP_COLOR, C'58,68,80');
   ObjectSetInteger(0, section_name, OBJPROP_BACK, false);
   ObjectSetInteger(0, section_name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, section_name, OBJPROP_HIDDEN, true);
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
   ObjectSetInteger(0, bg, OBJPROP_XSIZE, 520);
   ObjectSetInteger(0, bg, OBJPROP_YSIZE, 680);
   ObjectSetInteger(0, bg, OBJPROP_BGCOLOR, C'24,30,38');
   ObjectSetInteger(0, bg, OBJPROP_COLOR, C'72,82,94');
   ObjectSetInteger(0, bg, OBJPROP_BACK, false);
   ObjectSetInteger(0, bg, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, bg, OBJPROP_HIDDEN, true);

   // Keep the four operational areas visually distinct inside the chart panel.
   PanelCreateSection("MARKET_SECTION", 44, 66, C'31,39,49');
   PanelCreateSection("RECOMMENDATION_SECTION", 116, 136, C'31,39,49');
   PanelCreateSection("RISK_SECTION", 258, 220, C'31,39,49');
   PanelCreateSection("ACTIONS_SECTION", 484, 194, C'31,39,49');

   PanelCreateLabel(PANEL_PREFIX + "TITLE", 24);
   ObjectSetInteger(0, PANEL_PREFIX + "TITLE", OBJPROP_FONTSIZE, 11);
   PanelCreateLabel(PANEL_PREFIX + "MARKET_HEADER", 50);
   PanelCreateLabel(PANEL_PREFIX + "SYMBOL", 72);
   PanelCreateLabel(PANEL_PREFIX + "STATUS", 94);
   PanelCreateLabel(PANEL_PREFIX + "RECOMMENDATION_HEADER", 118);
   ObjectSetInteger(0, PANEL_PREFIX + "RECOMMENDATION_HEADER", OBJPROP_COLOR, clrLightSkyBlue);
   PanelCreateLabel(PANEL_PREFIX + "DECISION", 138);
   ObjectSetInteger(0, PANEL_PREFIX + "DECISION", OBJPROP_FONTSIZE, 11);
   ObjectSetInteger(0, PANEL_PREFIX + "DECISION", OBJPROP_COLOR, clrLime);
   PanelCreateLabel(PANEL_PREFIX + "SCENARIO", 162);
   PanelCreateLabel(PANEL_PREFIX + "REASON_DETAIL", 182);
   PanelCreateLabel(PANEL_PREFIX + "LEVELS", 202);
   ObjectSetInteger(0, PANEL_PREFIX + "LEVELS", OBJPROP_FONTSIZE, 10);
   ObjectSetInteger(0, PANEL_PREFIX + "LEVELS", OBJPROP_COLOR, clrLightSkyBlue);
   PanelCreateLabel(PANEL_PREFIX + "CONFIDENCE", 226);
   PanelCreateLabel(PANEL_PREFIX + "SOURCES", 246);
   PanelCreateLabel(PANEL_PREFIX + "RISK_HEADER", 264);
   PanelCreateLabel(PANEL_PREFIX + "RR_LABEL", 288);
   PanelCreateLabel(PANEL_PREFIX + "MAX_STOP_LABEL", 316);
   PanelCreateLabel(PANEL_PREFIX + "MAX_LOSS_LABEL", 344);
   PanelCreateLabel(PANEL_PREFIX + "COST_LABEL", 372);
   PanelCreateLabel(PANEL_PREFIX + "DAILY_LABEL", 400);
   PanelCreateLabel(PANEL_PREFIX + "VOLUME_LABEL", 428);
   PanelCreateLabel(PANEL_PREFIX + "INTERVAL_LABEL", 456);
   PanelCreateLabel(PANEL_PREFIX + "ACTIONS_HEADER", 490);
   PanelCreateLabel(PANEL_PREFIX + "POLL", 570);
   PanelCreateLabel(PANEL_PREFIX + "POSITION", 592);
   PanelCreateLabel(PANEL_PREFIX + "DAILY_PNL", 614);
   PanelCreateLabel(PANEL_PREFIX + "DAILY_STATE", 636);
   PanelCreateLabel(PANEL_PREFIX + "DAILY_CLOSE", 658);

   PanelCreateEdit(PANEL_PREFIX + "RR", 300, 284, 100, initial_risk_reward);
   PanelCreateEdit(PANEL_PREFIX + "MAX_STOP", 300, 312, 100, DoubleToString(max_stop_points, 2));
   PanelCreateEdit(PANEL_PREFIX + "MAX_LOSS", 300, 340, 100, DoubleToString(max_loss_per_trade, 2));
   PanelCreateEdit(PANEL_PREFIX + "ROUND_TRIP_COST", 300, 368, 100, DoubleToString(round_trip_cost, 2));
   PanelCreateEdit(PANEL_PREFIX + "DAILY_LOSS", 300, 396, 100, DoubleToString(daily_loss_limit, 2));
   PanelCreateEdit(PANEL_PREFIX + "VOLUME", 300, 424, 100, DoubleToString(initial_volume, 2));
   PanelCreateEdit(PANEL_PREFIX + "INTERVAL", 300, 452, 72, IntegerToString(initial_interval));

   string analyze_name = PANEL_PREFIX + "ANALYZE";
   if(ObjectFind(0, analyze_name) < 0)
      ObjectCreate(0, analyze_name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, analyze_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, analyze_name, OBJPROP_XDISTANCE, 24);
   ObjectSetInteger(0, analyze_name, OBJPROP_YDISTANCE, 514);
   ObjectSetInteger(0, analyze_name, OBJPROP_XSIZE, 220);
   ObjectSetInteger(0, analyze_name, OBJPROP_YSIZE, 26);
   ObjectSetInteger(0, analyze_name, OBJPROP_BGCOLOR, C'35,91,130');
   ObjectSetInteger(0, analyze_name, OBJPROP_COLOR, clrWhite);
   ObjectSetString(0, analyze_name, OBJPROP_TEXT, "ANALISAR AGORA");
   ObjectSetInteger(0, analyze_name, OBJPROP_HIDDEN, true);

   string apply_name = PANEL_PREFIX + "APPLY";
   if(ObjectFind(0, apply_name) < 0)
      ObjectCreate(0, apply_name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, apply_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, apply_name, OBJPROP_XDISTANCE, 255);
   ObjectSetInteger(0, apply_name, OBJPROP_YDISTANCE, 514);
   ObjectSetInteger(0, apply_name, OBJPROP_XSIZE, 230);
   ObjectSetInteger(0, apply_name, OBJPROP_YSIZE, 26);
   ObjectSetInteger(0, apply_name, OBJPROP_BGCOLOR, C'30,115,75');
   ObjectSetInteger(0, apply_name, OBJPROP_COLOR, clrWhite);
   ObjectSetString(0, apply_name, OBJPROP_TEXT, "APLICAR RECOMENDAÇÃO");
   ObjectSetInteger(0, apply_name, OBJPROP_HIDDEN, true);

   string button_name = PANEL_PREFIX + "AUTO";
   if(ObjectFind(0, button_name) < 0)
      ObjectCreate(0, button_name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, button_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, button_name, OBJPROP_XDISTANCE, 24);
   ObjectSetInteger(0, button_name, OBJPROP_YDISTANCE, 542);
   ObjectSetInteger(0, button_name, OBJPROP_XSIZE, 220);
   ObjectSetInteger(0, button_name, OBJPROP_YSIZE, 24);
   ObjectSetInteger(0, button_name, OBJPROP_FONTSIZE, 9);
   ObjectSetInteger(0, button_name, OBJPROP_BGCOLOR, (automation_enabled ? clrDarkGreen : clrMaroon));
   ObjectSetString(0, button_name, OBJPROP_TEXT, (automation_enabled ? "AUTOMAÇÃO: LIGADA" : "AUTOMAÇÃO: DESLIGADA"));
   ObjectSetInteger(0, button_name, OBJPROP_HIDDEN, true);

   ObjectSetString(0, PANEL_PREFIX + "TITLE", OBJPROP_TEXT, "BOLETA ASSISTIDA · MQL5 / BACKEND");
   ObjectSetString(0, PANEL_PREFIX + "MARKET_HEADER", OBJPROP_TEXT, "MERCADO E ESTADO");
   ObjectSetString(0, PANEL_PREFIX + "RECOMMENDATION_HEADER", OBJPROP_TEXT, "RECOMENDAÇÃO");
   ObjectSetString(0, PANEL_PREFIX + "RISK_HEADER", OBJPROP_TEXT, "CONFIGURAÇÕES DE RISCO E EXECUÇÃO");
   ObjectSetString(0, PANEL_PREFIX + "ACTIONS_HEADER", OBJPROP_TEXT, "AÇÕES");
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

void PanelSetActionAvailability(const bool analysis_enabled, const bool apply_enabled,
                                const string analysis_text, const string apply_text)
  {
   string analyze_name = PANEL_PREFIX + "ANALYZE";
   string apply_name = PANEL_PREFIX + "APPLY";
   if(ObjectFind(0, analyze_name) >= 0)
     {
      ObjectSetString(0, analyze_name, OBJPROP_TEXT, analysis_text);
      ObjectSetInteger(0, analyze_name, OBJPROP_SELECTABLE, analysis_enabled);
      ObjectSetInteger(0, analyze_name, OBJPROP_BGCOLOR, (analysis_enabled ? C'35,91,130' : C'65,70,76'));
      ObjectSetInteger(0, analyze_name, OBJPROP_STATE, false);
     }
   if(ObjectFind(0, apply_name) >= 0)
     {
      ObjectSetString(0, apply_name, OBJPROP_TEXT, apply_text);
      ObjectSetInteger(0, apply_name, OBJPROP_SELECTABLE, apply_enabled);
      ObjectSetInteger(0, apply_name, OBJPROP_BGCOLOR, (apply_enabled ? C'30,115,75' : C'65,70,76'));
      ObjectSetInteger(0, apply_name, OBJPROP_STATE, false);
     }
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
                           double &round_trip_cost, double &daily_loss_limit,
                           bool &manual_analysis_requested, bool &manual_apply_requested)
  {
   manual_analysis_requested = false;
   manual_apply_requested = false;
   if(id == CHARTEVENT_OBJECT_CLICK && object_name == PANEL_PREFIX + "ANALYZE")
     {
      manual_analysis_requested = true;
      ObjectSetInteger(0, object_name, OBJPROP_STATE, false);
      return true;
     }
   if(id == CHARTEVENT_OBJECT_CLICK && object_name == PANEL_PREFIX + "APPLY")
     {
      manual_apply_requested = true;
      ObjectSetInteger(0, object_name, OBJPROP_STATE, false);
      return true;
     }
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
                 const bool daily_blocked, const string daily_close_failure,
                 const bool analysis_in_progress, const bool execution_pending,
                 const bool manual_actions_allowed)
  {
   string display_status = status;
   ObjectSetString(0, PANEL_PREFIX + "SYMBOL", OBJPROP_TEXT,
                   "Ativo: " + LogicalSymbolName() + " → " + symbol + " · M5 · janela 7 dias");
   ObjectSetString(0, PANEL_PREFIX + "STATUS", OBJPROP_TEXT, "Estado: " + status);
   string decision = "Decisão: sem sinal";
   string levels = "Entrada: —  |  Stop Loss: —  |  Take Profit: —";
   string scenario = "Cenário: aguardando análise";
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
   if(analysis_in_progress)
      display_status = "Análise pendente · aguardando backend";
   else if(execution_pending)
      display_status = "Execução enviada · aguardando confirmação do servidor";
   color decision_color = C'180,190,200';
   if(analysis.valid && analysis.actionable)
      decision_color = (analysis.direction == "BUY" ? C'70,220,135' : C'255,105,105');
   else if(analysis.valid)
      decision_color = C'255,196,90';
   color status_color = clrWhite;
   if(analysis_in_progress)
      status_color = C'255,196,90';
   else if(execution_pending)
      status_color = C'120,190,255';
   else if(StringFind(display_status, "expirada") >= 0 || StringFind(display_status, "Expirada") >= 0)
      status_color = C'255,170,80';
   else if(execution_blocked || StringFind(display_status, "falha") >= 0 ||
           StringFind(display_status, "Falha") >= 0 || StringFind(display_status, "bloquead") >= 0 ||
           StringFind(display_status, "Bloquead") >= 0 || StringFind(display_status, "Erro") >= 0)
      status_color = C'255,115,115';
   else if(analysis.valid && !analysis.actionable)
      status_color = C'255,196,90';
   ObjectSetInteger(0, PANEL_PREFIX + "STATUS", OBJPROP_COLOR, status_color);
   ObjectSetInteger(0, PANEL_PREFIX + "DECISION", OBJPROP_COLOR, decision_color);
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
   bool has_current_actionable = (analysis.valid && analysis.actionable && !analysis.fixture &&
                                  analysis.symbol == symbol && analysis.expires_at > TimeGMT());
   bool analyze_enabled = manual_actions_allowed && !automation_enabled && !analysis_in_progress &&
                          !position_open && !execution_pending && !execution_blocked;
   bool apply_enabled = manual_actions_allowed && !automation_enabled && !analysis_in_progress &&
                        !position_open && !execution_pending &&
                        !execution_blocked && has_current_actionable;
   string analyze_text = (analysis_in_progress ? "ANÁLISE EM ANDAMENTO" : "ANALISAR AGORA");
   string apply_text = (has_current_actionable ? "APLICAR RECOMENDAÇÃO" : "SEM RECOMENDAÇÃO VÁLIDA");
   if(automation_enabled) { analyze_text = "DESLIGUE AUTOMAÇÃO"; apply_text = "MODO MANUAL DESATIVADO"; }
   else if(position_open) { analyze_text = "EXPOSIÇÃO ATIVA"; apply_text = "EXPOSIÇÃO ATIVA"; }
   else if(execution_pending) { analyze_text = "AGUARDANDO EXECUÇÃO"; apply_text = "AGUARDANDO EXECUÇÃO"; }
   else if(analysis_in_progress) { apply_text = "AGUARDANDO ANÁLISE"; }
   else if(daily_blocked) { analyze_text = "LIMITE DIÁRIO ATINGIDO"; apply_text = "LIMITE DIÁRIO ATINGIDO"; }
   else if(execution_blocked) { analyze_text = "EXECUÇÃO BLOQUEADA"; apply_text = "EXECUÇÃO BLOQUEADA"; }
   else if(!manual_actions_allowed) { analyze_text = "ANÁLISE INDISPONÍVEL"; apply_text = "APLICAÇÃO INDISPONÍVEL"; }
   PanelSetActionAvailability(analyze_enabled, apply_enabled, analyze_text, apply_text);
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
