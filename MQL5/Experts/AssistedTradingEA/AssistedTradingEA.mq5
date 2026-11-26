#property strict
#property version   "1.00"
#property description "Captura dados M5, consulta backend FastAPI e executa decisões após ativação manual."

#include "Include/Config.mqh"
#include "Include/Types.mqh"
#include "Include/MarketData.mqh"
#include "Include/BackendClient.mqh"
#include "Include/Panel.mqh"
#include "Include/AuditLog.mqh"
#include "Include/DailyRisk.mqh"
#include "Include/Execution.mqh"

AnalysisData g_analysis;
string g_symbol = "";
string g_status = "Inicializando";
string g_last_request_id = "";
bool g_automation_enabled = false;
bool g_execution_blocked = false;
bool g_execution_pending = false;
bool g_analysis_in_progress = false;
bool g_manual_execution_pending = false;
ulong g_pending_order_ticket = 0;
ulong g_pending_deal_ticket = 0;
string g_execution_lock_name = "";
double g_execution_lock_token = 0.0;
double g_contracts = 0.0;
int g_poll_interval_minutes = 1;
string g_risk_reward_preference = "1:2";
double g_max_stop_points = 0.0;
double g_max_loss_per_trade = 0.0;
double g_round_trip_cost_per_contract = 0.0;
double g_daily_loss_limit = 0.0;
double g_daily_realized_pnl = 0.0;
double g_daily_floating_pnl = 0.0;
double g_daily_total_pnl = 0.0;
bool g_daily_limit_reached = false;
string g_daily_close_failure = "";
datetime g_daily_trade_day = 0;

string DailyBlockGlobalName()
  {
   return StringFormat("ATEA_DAILY_%I64u_%I64u",
                       (ulong)AccountInfoInteger(ACCOUNT_LOGIN), InpMagicNumber);
  }

bool LoadDailyBlock(const datetime trading_day)
  {
   string name = DailyBlockGlobalName();
   if(!GlobalVariableCheck(name))
      return false;
   datetime stored_day = (datetime)GlobalVariableGet(name);
   if(stored_day < trading_day)
     {
      GlobalVariableDel(name);
      return false;
     }
   return (stored_day >= trading_day);
  }

bool PersistDailyBlock(const datetime trading_day)
  {
   if(GlobalVariableSet(DailyBlockGlobalName(), (double)trading_day) <= 0)
      return false;
   GlobalVariablesFlush();
   return true;
  }

bool ValidateRiskPreferences(string &error)
  {
   error = "";
   if(g_risk_reward_preference != "1:2" && g_risk_reward_preference != "1:3")
     {
      error = "RR deve ser 1:2 ou 1:3";
      return false;
     }
   if(!MathIsValidNumber(g_max_stop_points) || g_max_stop_points <= 0)
     {
      error = "Configure stop máximo positivo em pontos";
      return false;
     }
   if(!MathIsValidNumber(g_max_loss_per_trade) || g_max_loss_per_trade <= 0)
     {
      error = "Configure perda máxima positiva por operação";
      return false;
     }
   if(!MathIsValidNumber(g_round_trip_cost_per_contract) || g_round_trip_cost_per_contract < 0)
     {
      error = "Custo de ida e volta não pode ser negativo";
      return false;
     }
   if(!MathIsValidNumber(g_daily_loss_limit) || g_daily_loss_limit <= 0)
     {
      error = "Configure perda máxima diária positiva";
      return false;
     }
   return true;
  }

bool RecordEvent(const string event_name, const string request_id, const string detail)
  {
   if(WriteAuditEvent(InpLogFileName, event_name, g_symbol, request_id, detail))
      return true;
   g_execution_blocked = true;
   g_status = "Falha no registro local; novas operações automáticas bloqueadas";
   Print(g_status, " (", GetLastError(), ")");
   return false;
  }

void UpdateDailyRisk()
  {
   datetime trading_day = TradingDayStart();
   if(trading_day <= 0)
     {
      g_execution_blocked = true;
      g_status = "Data de negociação indisponível · execução bloqueada";
      return;
     }
   if(g_daily_trade_day != trading_day)
     {
      g_daily_trade_day = trading_day;
      g_daily_limit_reached = LoadDailyBlock(trading_day);
      g_daily_close_failure = "";
     }
   string calculation_error;
   if(!CalculateDailyPnl(InpMagicNumber, g_daily_realized_pnl, g_daily_floating_pnl,
                         g_daily_total_pnl, calculation_error))
     {
      g_execution_blocked = true;
      g_status = "Apuração diária indisponível · execução bloqueada";
      RecordEvent("daily_pnl_error", "", calculation_error);
      return;
     }
   if(g_daily_loss_limit <= 0)
      return;
   if(g_daily_total_pnl <= -g_daily_loss_limit && !g_daily_limit_reached)
     {
      g_daily_limit_reached = true;
      if(!PersistDailyBlock(trading_day))
        {
         g_execution_blocked = true;
         g_status = "Limite diário atingido · falha ao persistir bloqueio";
         RecordEvent("daily_loss_state_persist_failed", "", DailyBlockGlobalName());
        }
      RecordEvent("daily_loss_limit_reached", "",
                  StringFormat("day=%s; realized=%.2f; floating=%.2f; total=%.2f",
                               TimeToString(trading_day, TIME_DATE), g_daily_realized_pnl,
                               g_daily_floating_pnl, g_daily_total_pnl));
     }
   if(!g_daily_limit_reached)
      return;

   g_automation_enabled = false;
   PanelSetAutomation(false);
   int closed_count = 0;
   string close_error;
   string previous_close_failure = g_daily_close_failure;
   bool all_closed = CloseManagedPositions(InpMagicNumber, InpDeviationPoints, closed_count, close_error);
   if(all_closed)
     {
      g_daily_close_failure = "";
      g_status = StringFormat("Limite diário atingido · %.2f · automação suspensa", g_daily_total_pnl);
      if(closed_count > 0)
         RecordEvent("daily_loss_positions_closed", "", StringFormat("closed=%d", closed_count));
      else if(StringLen(previous_close_failure) > 0)
         RecordEvent("daily_loss_close_resolved", "", "all managed positions are closed");
     }
   else
     {
      g_daily_close_failure = close_error;
      g_status = "Limite diário atingido · falha ao fechar posição: " + close_error;
      if(close_error != previous_close_failure)
         RecordEvent("daily_loss_close_failed", "", close_error);
     }
  }

bool ResolveConfiguredSymbol(string &symbol, string &error)
  {
   symbol = ConfiguredSymbol();
   error = "";
   string expected = LogicalSymbolName();
   string normalized = symbol;
   StringToUpper(normalized);
   if(StringFind(normalized, expected) < 0)
     {
      error = "Mapeie " + expected + " para o nome negociável correspondente do broker";
      return false;
     }
   if(!SymbolSelect(symbol, true) || SymbolInfoInteger(symbol, SYMBOL_SELECT) == 0)
     {
      error = "Símbolo configurado não está disponível: " + symbol;
      return false;
     }
   return true;
  }

bool ValidateConfiguredVolume(const double volume, string &error)
  {
   error = "";
   double min_volume = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN);
   double max_volume = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP);
   if(!MathIsValidNumber(volume) || volume <= 0 || volume < min_volume || volume > max_volume || step <= 0 ||
      MathAbs((volume - min_volume) / step - MathRound((volume - min_volume) / step)) > 0.000001)
     {
      error = StringFormat("Quantidade deve respeitar mínimo %s, máximo %s e passo %s",
                           DoubleToString(min_volume, 4), DoubleToString(max_volume, 4), DoubleToString(step, 4));
      return false;
     }
   return true;
  }

bool CanEnableAutomation(string &error)
  {
   if(InpUseFixture)
     {
      error = "Fixture de teste não pode habilitar execução automática";
      return false;
     }
   if(StringLen(InpBackendUrl) == 0 ||
      (StringFind(InpBackendUrl, "http://") != 0 && StringFind(InpBackendUrl, "https://") != 0))
     {
      error = "Configure a URL da REST API FastAPI";
      return false;
     }
   if(g_poll_interval_minutes < 1 || g_poll_interval_minutes > 5)
     {
      error = "Intervalo de polling deve ser de 1 a 5 minutos";
      return false;
     }
   if(InpHttpTimeoutMs < 250 || InpHttpTimeoutMs > 30000)
     {
      error = "Timeout HTTP deve ficar entre 250 e 30000 ms";
      return false;
     }
   if(InpDeviationPoints < 0)
     {
      error = "Desvio de preço não pode ser negativo";
      return false;
     }
   if(StringLen(g_symbol) == 0 || !SymbolSelect(g_symbol, true) || SymbolInfoInteger(g_symbol, SYMBOL_SELECT) == 0)
     {
      error = "Símbolo negociável não está selecionado/disponível";
      return false;
     }
   if(HasActiveOrderForSymbol(g_symbol))
     {
      error = "Existe ordem ativa para o símbolo; resolva-a antes de ligar a automação";
      return false;
     }
   if(g_daily_limit_reached)
     {
      error = "Limite diário atingido; aguarde o próximo dia do servidor e reative manualmente";
      return false;
     }
   if(!ValidateRiskPreferences(error))
      return false;
   if(!ValidateConfiguredVolume(g_contracts, error))
      return false;
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED) ||
      !AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))
     {
      error = "Ative negociação algorítmica no terminal e na conta";
      return false;
     }
   return true;
  }

void UpdatePanel()
  {
   if(g_analysis.valid && !g_analysis.fixture && g_analysis.expires_at > 0 && TimeGMT() >= g_analysis.expires_at)
     {
      g_analysis.valid = false;
      g_analysis.actionable = false;
      g_status = "Análise expirada · solicite uma nova análise";
     }
   bool position_open = (StringLen(g_symbol) > 0 && (HasPositionForSymbol(g_symbol) || HasActiveOrderForSymbol(g_symbol)));
   PanelUpdate(g_symbol, g_status, g_analysis, g_automation_enabled, g_poll_interval_minutes,
               g_contracts, position_open, g_execution_blocked,
               g_daily_realized_pnl, g_daily_floating_pnl, g_daily_total_pnl,
               g_daily_loss_limit, g_daily_limit_reached, g_daily_close_failure,
               g_analysis_in_progress, g_execution_pending,
               (!InpUseFixture && StringLen(InpBackendUrl) > 0 && !g_daily_limit_reached));
  }

void InvalidateAnalysisForChangedSettings()
  {
   if(g_execution_pending)
     {
      // Preserve request_id and expected SL/TP for OnTradeTransaction.
      g_analysis.valid = false;
      g_analysis.actionable = false;
     }
   else
      ZeroMemory(g_analysis);
  }

void BuildFixtureAnalysis()
  {
   ZeroMemory(g_analysis);
   string symbol_error;
   if(!ResolveConfiguredSymbol(g_symbol, symbol_error))
     {
      g_status = symbol_error;
      return;
     }
   g_analysis.valid = true;
   g_analysis.fixture = true;
   g_analysis.request_id = "FIXTURE-ONLY";
   g_analysis.symbol = g_symbol;
   g_analysis.direction = "NONE";
   g_analysis.created_at = TimeGMT();
   g_analysis.expires_at = g_analysis.created_at + 60;
   g_analysis.sources_summary = "fixture local identificada";
   if(InpFixtureNoSignal)
     {
      g_analysis.actionable = false;
      g_analysis.scenario = "Fixture sem sinal; não representa análise ao vivo";
      g_analysis.confidence = "low";
      g_status = "FIXTURE DE TESTE · sem sinal · nenhuma ordem será enviada";
      return;
     }
   MqlTick tick;
   double tick_size = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);
   int digits = (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);
   if(!SymbolInfoTick(g_symbol, tick) || tick_size <= 0)
     {
      g_analysis.valid = false;
      g_status = "Fixture indisponível: cotação ausente";
      return;
     }
   g_analysis.actionable = true;
   g_analysis.direction = "BUY";
   g_analysis.reference_price = NormalizeDouble(tick.ask, digits);
   g_analysis.stop_loss = NormalizeDouble(g_analysis.reference_price - 10 * tick_size, digits);
   g_analysis.take_profit = NormalizeDouble(g_analysis.reference_price + 20 * tick_size, digits);
   g_analysis.risk_reward = "1:2";
   g_analysis.scenario = "Exemplo local para validar interface; não representa análise ao vivo";
   g_analysis.confidence = "low";
   g_status = "FIXTURE DE TESTE · nenhuma ordem será enviada";
  }

bool ApplyCurrentAnalysis(const bool manual)
  {
   string source = (manual ? "manual" : "automatic");
   if(manual && (g_automation_enabled || g_analysis_in_progress || g_execution_pending ||
                 g_execution_blocked || g_daily_limit_reached || HasPositionForSymbol(g_symbol) || HasActiveOrderForSymbol(g_symbol)))
     {
      g_status = (g_daily_limit_reached ? "Aplicação manual bloqueada: limite diário atingido" :
                  "Aplicação manual bloqueada: automação, exposição ou execução pendente");
      RecordEvent("manual_apply_blocked", g_analysis.request_id, g_status);
      UpdatePanel();
      return false;
     }
   if(TimeGMT() >= g_analysis.expires_at)
     {
      g_status = "Aplicação bloqueada: recomendação expirada; solicite uma nova análise";
      if(manual) RecordEvent("manual_apply_blocked", g_analysis.request_id, g_status);
      UpdatePanel();
      return false;
     }
   if(!g_analysis.valid || !g_analysis.actionable || g_analysis.fixture || g_analysis.symbol != g_symbol ||
      g_analysis.request_id == "")
     {
      g_status = (!g_analysis.valid || !g_analysis.actionable ? "Aplicação bloqueada: recomendação sem sinal ou inválida" :
                  "Aplicação bloqueada: símbolo da recomendação mudou ou identificador ausente");
      if(manual)
         RecordEvent("manual_apply_blocked", g_analysis.request_id, g_status);
      UpdatePanel();
      return false;
     }
   if(manual && !RecordEvent("manual_apply_requested", g_analysis.request_id,
                             StringFormat("direction=%s; volume=%s; SL=%s; TP=%s; rr=%s",
                                          g_analysis.direction, DoubleToString(g_contracts, 4),
                                          DoubleToString(g_analysis.stop_loss, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)),
                                          DoubleToString(g_analysis.take_profit, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)),
                                          g_analysis.risk_reward)))
     {
      UpdatePanel();
      return false;
     }
   if(HasPositionForSymbol(g_symbol) || HasActiveOrderForSymbol(g_symbol))
     {
      g_status = "Posição/ordem ativa; recomendação não aplicada";
      if(manual) RecordEvent("manual_apply_blocked", g_analysis.request_id, g_status);
      UpdatePanel();
      return false;
     }
   MqlTradeResult result;
   bool ambiguous;
   string execution_error;
   string lock_name;
   double lock_token = 0.0;
   if(!AcquireExecutionLock(g_symbol, lock_name, lock_token))
     {
      g_status = "Outra instância está processando uma ordem para este símbolo";
      RecordEvent(manual ? "manual_apply_blocked" : "execution_lock_unavailable", g_analysis.request_id, g_status);
      UpdatePanel();
      return false;
     }
   // Revalidate mode and exposure immediately before the shared validation/send routine.
   if(manual && (g_automation_enabled || g_execution_pending || g_daily_limit_reached ||
                 HasPositionForSymbol(g_symbol) || HasActiveOrderForSymbol(g_symbol)))
     {
      ReleaseExecutionLock(lock_name, lock_token);
      g_status = "Aplicação manual bloqueada: o estado operacional mudou antes do envio";
      RecordEvent("manual_apply_blocked", g_analysis.request_id, g_status);
      UpdatePanel();
      return false;
     }
   bool sent = ValidateAndSendMarketOrder(g_analysis, g_symbol, g_contracts, g_max_loss_per_trade,
                                          g_max_stop_points, g_round_trip_cost_per_contract,
                                          InpMagicNumber, InpDeviationPoints, g_poll_interval_minutes * 60,
                                          result, ambiguous, execution_error);
   if(!sent)
     {
      if(ambiguous)
        {
         g_execution_blocked = true;
         g_execution_lock_name = lock_name;
         g_execution_lock_token = lock_token;
        }
      else
         ReleaseExecutionLock(lock_name, lock_token);
      g_status = (ambiguous ? "Resultado da ordem ambíguo: " : "Ordem bloqueada/rejeitada: ") + execution_error;
      string failed_event = (manual ? (ambiguous ? "manual_order_ambiguous" : "manual_order_rejected") :
                             (ambiguous ? "order_result_ambiguous" : "order_not_executed"));
      RecordEvent(failed_event, g_analysis.request_id,
                  execution_error + "; retcode=" + IntegerToString((int)result.retcode));
      UpdatePanel();
      return false;
     }
   g_status = StringFormat("Ordem enviada · retcode %u · deal %I64u", result.retcode, result.deal);
   bool logged_order = RecordEvent(manual ? "manual_order_accepted" : "order_executed", g_analysis.request_id,
                                   StringFormat("source=%s; direction=%s; volume=%s; SL=%s; TP=%s; retcode=%u; order=%I64u; deal=%I64u; %s",
                                                source, g_analysis.direction, DoubleToString(g_contracts, 4),
                                                DoubleToString(g_analysis.stop_loss, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)),
                                                DoubleToString(g_analysis.take_profit, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)),
                                                result.retcode, result.order, result.deal, result.comment));
   g_execution_pending = true;
   g_manual_execution_pending = manual;
   g_execution_lock_name = lock_name;
   g_execution_lock_token = lock_token;
   g_pending_order_ticket = result.order;
   g_pending_deal_ticket = result.deal;
   if(logged_order)
      g_status = "Ordem aceita; aguardando confirmação da transação";
   UpdatePanel();
   return true;
  }

void RunAnalysis(const bool manual)
  {
   if(manual)
     {
      if(g_automation_enabled || g_analysis_in_progress || g_execution_pending ||
         HasPositionForSymbol(g_symbol) || HasActiveOrderForSymbol(g_symbol))
        {
         if(g_automation_enabled)
            g_status = "Análise manual indisponível com automação ligada";
         else if(g_analysis_in_progress)
            g_status = "Análise manual já está em andamento";
         else if(g_execution_pending)
            g_status = "Análise manual indisponível: execução pendente";
         else
            g_status = "Análise manual indisponível: posição ou ordem ativa";
         UpdatePanel();
         return;
        }
      if(InpUseFixture || StringLen(InpBackendUrl) == 0)
        {
         g_status = (InpUseFixture ? "Análise manual indisponível na fixture de teste" :
                     "Análise manual indisponível: configure a URL do backend");
         UpdatePanel();
         return;
        }
     }
   else if(!g_automation_enabled)
      return;
   if(g_daily_limit_reached)
     {
      g_automation_enabled = false;
      g_status = "Limite diário atingido · novas consultas e ordens suspensas";
      PanelSetAutomation(false);
      UpdatePanel();
      return;
     }
   if(g_execution_blocked)
     {
      g_status = "Execução bloqueada; verifique ordem/posição antes de reiniciar o EA";
      UpdatePanel();
      return;
     }
   if(g_execution_pending)
     {
      g_status = "Aguardando confirmação da transação do servidor; polling pausado";
      UpdatePanel();
      return;
     }
   if(g_analysis_in_progress)
     {
      g_status = "Consulta já está em andamento";
      UpdatePanel();
      return;
     }
   if(HasPositionForSymbol(g_symbol) || HasActiveOrderForSymbol(g_symbol))
     {
      g_status = "Posição/ordem ativa; polling pausado";
      UpdatePanel();
      return;
     }
   string volume_error;
   if(!ValidateConfiguredVolume(g_contracts, volume_error))
     {
      g_status = volume_error;
      UpdatePanel();
      return;
     }

   if(InpUseFixture)
     {
      BuildFixtureAnalysis();
      UpdatePanel();
      return;
     }

   g_analysis_in_progress = true;
   ZeroMemory(g_analysis);
   g_status = (manual ? "Análise manual pendente · aguardando backend" : "Consulta automática pendente");
   UpdatePanel();
   string body;
   string build_error;
   if(!BuildMarketSnapshot(g_symbol, g_poll_interval_minutes, g_contracts,
                           g_risk_reward_preference, g_max_stop_points, g_max_loss_per_trade,
                           g_round_trip_cost_per_contract, g_daily_loss_limit,
                           g_last_request_id, body, build_error))
     {
      ZeroMemory(g_analysis);
      g_analysis_in_progress = false;
      g_status = "Erro de captura: " + build_error;
      RecordEvent(manual ? "manual_capture_error" : "capture_error", g_last_request_id, build_error);
      UpdatePanel();
      return;
     }
   if(!RecordEvent(manual ? "manual_analysis_requested" : "snapshot_sent", g_last_request_id,
                   "POST snapshot M5/7d; payload_bytes=" + IntegerToString(StringLen(body))))
     {
      g_analysis_in_progress = false;
      UpdatePanel();
      return;
     }

   string response;
   string http_error;
   int http_status;
   if(!PostMarketSnapshot(InpBackendUrl, InpHttpTimeoutMs, body, response, http_status, http_error))
     {
      ZeroMemory(g_analysis);
      g_analysis_in_progress = false;
      g_status = "Erro do backend: " + http_error;
      RecordEvent(manual ? "manual_backend_error" : "backend_error", g_last_request_id,
                  http_error + "; HTTP=" + IntegerToString(http_status));
      UpdatePanel();
      return;
     }
   if(!RecordEvent(manual ? "manual_backend_response" : "backend_response", g_last_request_id,
                   "HTTP " + IntegerToString(http_status) + "; response=" + response))
     {
      g_analysis_in_progress = false;
      UpdatePanel();
      return;
     }

   string parse_error;
   double tick_size = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);
   if(!ParseAnalysisResponse(response, g_last_request_id, g_symbol, tick_size, g_analysis, parse_error))
     {
      ZeroMemory(g_analysis);
      g_analysis_in_progress = false;
      g_status = "Erro de resposta: " + parse_error;
      RecordEvent(manual ? "manual_response_rejected" : "response_rejected", g_last_request_id, parse_error);
      UpdatePanel();
      return;
     }
   g_analysis_in_progress = false;
   if(!g_analysis.actionable)
     {
      g_status = "Sem sinal · " + g_analysis.reason_code + ": " + g_analysis.reason;
      RecordEvent(manual ? "manual_no_signal" : "no_signal", g_last_request_id, g_analysis.sources_summary);
      UpdatePanel();
      return;
     }

   if(!RecordEvent("decision_payload", g_last_request_id, "request=" + body + "; response=" + response))
     {
      UpdatePanel();
      return;
     }

   if(manual)
     {
      g_status = "Recomendação pronta · revise os níveis e aplique para enviar ordem";
      UpdatePanel();
      return;
     }
   if(HasPositionForSymbol(g_symbol) || HasActiveOrderForSymbol(g_symbol))
     {
      g_status = "Posição/ordem apareceu durante consulta; entrada descartada";
      RecordEvent("entry_skipped_position_open", g_last_request_id, "position guard");
      UpdatePanel();
      return;
     }
   ApplyCurrentAnalysis(false);
  }

int OnInit()
  {
   g_automation_enabled = false;
   g_execution_blocked = false;
   g_execution_pending = false;
   g_pending_order_ticket = 0;
   g_pending_deal_ticket = 0;
   g_contracts = InpInitialContracts;
   g_poll_interval_minutes = InpPollingIntervalMinutes;
   g_risk_reward_preference = InpRiskRewardPreference;
   g_max_stop_points = InpMaxStopPoints;
   g_max_loss_per_trade = InpMaxLossPerTrade;
   g_round_trip_cost_per_contract = InpRoundTripCostPerContract;
   g_daily_loss_limit = InpDailyLossLimit;
   string symbol_error;
   if(!ResolveConfiguredSymbol(g_symbol, symbol_error))
      g_status = symbol_error;
   else
      g_status = "Automação desligada · aguardando ativação manual";
   if(StringLen(g_symbol) > 0 && HasActiveOrderForSymbol(g_symbol))
     {
      g_execution_blocked = true;
      g_status = "Ordem ativa detectada na inicialização; confira o estado antes de reiniciar automação";
     }
   if(InpPollingIntervalMinutes < 1 || InpPollingIntervalMinutes > 5)
      g_status = "Intervalo inválido: configure entre 1 e 5 minutos";
   PanelCreate(g_contracts, g_poll_interval_minutes, g_automation_enabled,
               g_risk_reward_preference, g_max_stop_points, g_max_loss_per_trade,
               g_round_trip_cost_per_contract, g_daily_loss_limit);
   UpdateDailyRisk();
   UpdatePanel();
   if(!EventSetTimer(MathMax(60, MathMin(300, g_poll_interval_minutes * 60))))
     {
      g_status = "Não foi possível iniciar o timer";
      UpdatePanel();
      return INIT_FAILED;
     }
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   PanelRemove();
  }

void OnTick()
  {
   // A coleta e o polling ocorrem somente pelo timer, nunca a cada tick.
  }

void OnTimer()
  {
   UpdateDailyRisk();
   if(InpUseFixture)
     {
      BuildFixtureAnalysis();
      UpdatePanel();
      return;
     }
   if(g_automation_enabled)
      RunAnalysis(false);
   UpdatePanel();
  }

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   double requested_volume = g_contracts;
   int requested_interval = g_poll_interval_minutes;
   string requested_risk_reward = g_risk_reward_preference;
   double requested_max_stop = g_max_stop_points;
   double requested_max_loss = g_max_loss_per_trade;
   double requested_cost = g_round_trip_cost_per_contract;
   double requested_daily_loss = g_daily_loss_limit;
   bool was_enabled = g_automation_enabled;
   bool manual_analysis_requested = false;
   bool manual_apply_requested = false;
   if(!PanelHandleChartEvent(id, sparam, g_automation_enabled, requested_volume, requested_interval,
                             requested_risk_reward, requested_max_stop, requested_max_loss,
                             requested_cost, requested_daily_loss,
                             manual_analysis_requested, manual_apply_requested))
      return;
   if(manual_analysis_requested)
     {
      if(g_automation_enabled)
        {
         g_status = "Análise manual indisponível com automação ligada";
         UpdatePanel();
         return;
        }
      if(HasPositionForSymbol(g_symbol) || HasActiveOrderForSymbol(g_symbol))
        {
         g_status = "Análise manual indisponível enquanto houver posição ou ordem ativa";
         UpdatePanel();
         return;
        }
      RunAnalysis(true);
      return;
     }
   if(manual_apply_requested)
     {
      ApplyCurrentAnalysis(true);
      return;
     }
   bool risk_setting_changed = (id == CHARTEVENT_OBJECT_ENDEDIT &&
                                (sparam == "ATEA_RR" || sparam == "ATEA_MAX_STOP" ||
                                 sparam == "ATEA_MAX_LOSS" || sparam == "ATEA_ROUND_TRIP_COST" ||
                                 sparam == "ATEA_DAILY_LOSS"));
   if(risk_setting_changed)
     {
      bool risk_values_changed = (requested_risk_reward != g_risk_reward_preference ||
                                  requested_max_stop != g_max_stop_points ||
                                  requested_max_loss != g_max_loss_per_trade ||
                                  requested_cost != g_round_trip_cost_per_contract ||
                                  requested_daily_loss != g_daily_loss_limit);
      if(risk_values_changed)
         InvalidateAnalysisForChangedSettings();
      g_risk_reward_preference = requested_risk_reward;
      g_max_stop_points = requested_max_stop;
      g_max_loss_per_trade = requested_max_loss;
      g_round_trip_cost_per_contract = requested_cost;
      g_daily_loss_limit = requested_daily_loss;
      string risk_error;
      if(!ValidateRiskPreferences(risk_error))
        {
         g_automation_enabled = false;
         g_status = "Preferência inválida: " + risk_error;
         PanelSetAutomation(false);
        }
      else
        {
         g_status = (risk_values_changed ? "Risco atualizado · solicite nova análise" :
                     "Preferências de risco conferidas");
         RecordEvent("risk_preferences_changed", g_last_request_id,
                     "rr=" + g_risk_reward_preference + "; max_stop_points=" + DoubleToString(g_max_stop_points, 2) +
                     "; max_loss=" + DoubleToString(g_max_loss_per_trade, 2) +
                     "; round_trip_cost=" + DoubleToString(g_round_trip_cost_per_contract, 2) +
                     "; daily_loss=" + DoubleToString(g_daily_loss_limit, 2));
        }
     }
   if(id == CHARTEVENT_OBJECT_ENDEDIT)
     {
      bool volume_changed = (sparam == "ATEA_VOLUME" && requested_volume != g_contracts);
      if(volume_changed)
         InvalidateAnalysisForChangedSettings();
      g_contracts = requested_volume;
      string volume_error;
      if(sparam == "ATEA_VOLUME" && !ValidateConfiguredVolume(g_contracts, volume_error))
         g_status = volume_error;
      else if(sparam == "ATEA_VOLUME")
        {
         g_status = "Quantidade atualizada para " + DoubleToString(g_contracts, 2) +
                    (volume_changed ? " · solicite nova análise" : "");
         RecordEvent("volume_changed", g_last_request_id, DoubleToString(g_contracts, 4));
        }
     }
   if(id == CHARTEVENT_OBJECT_ENDEDIT && sparam == "ATEA_INTERVAL")
     {
      g_poll_interval_minutes = requested_interval;
      if(g_poll_interval_minutes < 1 || g_poll_interval_minutes > 5)
        {
         g_status = "Intervalo inválido: escolha de 1 a 5 minutos";
         g_automation_enabled = false;
         PanelSetAutomation(false);
        }
      else
        {
         EventKillTimer();
         EventSetTimer(g_poll_interval_minutes * 60);
         g_status = "Intervalo de polling definido para " + IntegerToString(g_poll_interval_minutes) + " minuto(s)";
         RecordEvent("poll_interval_changed", "", IntegerToString(g_poll_interval_minutes));
        }
     }
   if(g_automation_enabled && !was_enabled)
     {
      string enable_error;
      if(!CanEnableAutomation(enable_error))
        {
         g_automation_enabled = false;
         g_status = "Automação não ativada: " + enable_error;
         PanelSetAutomation(false);
        }
      else
        {
         g_status = "Automação ativa · primeira consulta no próximo intervalo";
         RecordEvent("automation_enabled", "", "interval_minutes=" + IntegerToString(g_poll_interval_minutes));
        }
     }
   else if(!g_automation_enabled && was_enabled)
     {
      g_status = "Automação desligada manualmente";
      RecordEvent("automation_disabled", "", "manual toggle");
     }
   UpdatePanel();
  }

void OnTradeTransaction(const MqlTradeTransaction &transaction, const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(transaction.symbol != g_symbol)
      return;
   string detail = StringFormat("type=%d; order=%I64u; deal=%I64u; position=%I64u; retcode=%u; comment=%s",
                                transaction.type, transaction.order, transaction.deal,
                                transaction.position, result.retcode, result.comment);
   if(transaction.type == TRADE_TRANSACTION_DEAL_ADD && transaction.deal > 0 && HistoryDealSelect(transaction.deal))
     {
      detail += StringFormat("; deal_entry=%d; deal_type=%d; volume=%s; price=%s; profit=%s; commission=%s; swap=%s; magic=%I64u",
                             (int)HistoryDealGetInteger(transaction.deal, DEAL_ENTRY),
                             (int)HistoryDealGetInteger(transaction.deal, DEAL_TYPE),
                             DoubleToString(HistoryDealGetDouble(transaction.deal, DEAL_VOLUME), 4),
                             DoubleToString(HistoryDealGetDouble(transaction.deal, DEAL_PRICE), (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)),
                             DoubleToString(HistoryDealGetDouble(transaction.deal, DEAL_PROFIT), 2),
                             DoubleToString(HistoryDealGetDouble(transaction.deal, DEAL_COMMISSION), 2),
                             DoubleToString(HistoryDealGetDouble(transaction.deal, DEAL_SWAP), 2),
                             (ulong)HistoryDealGetInteger(transaction.deal, DEAL_MAGIC));
     }
   string transaction_request_id = (g_execution_pending ? g_analysis.request_id : g_last_request_id);
   bool transaction_logged = RecordEvent("trade_transaction", transaction_request_id, detail);
   bool matching_transaction = ((g_pending_order_ticket > 0 && transaction.order == g_pending_order_ticket) ||
                                (g_pending_deal_ticket > 0 && transaction.deal == g_pending_deal_ticket) ||
                                (g_pending_order_ticket == 0 && g_pending_deal_ticket == 0 && transaction.type == TRADE_TRANSACTION_DEAL_ADD));
   if(g_execution_pending && (matching_transaction || HasPositionForSymbol(g_symbol)) && PositionSelect(g_symbol))
     {
      double actual_sl = PositionGetDouble(POSITION_SL);
      double actual_tp = PositionGetDouble(POSITION_TP);
      double tolerance = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);
      bool protected_position = (actual_sl > 0 && actual_tp > 0 && tolerance > 0 &&
                                 MathAbs(actual_sl - g_analysis.stop_loss) <= tolerance &&
                                 MathAbs(actual_tp - g_analysis.take_profit) <= tolerance);
      g_execution_pending = false;
      g_pending_order_ticket = 0;
      g_pending_deal_ticket = 0;
      if(!protected_position)
        {
         g_execution_blocked = true;
         g_status = "ERRO: posição aberta sem SL/TP confirmados; automação bloqueada";
         RecordEvent("protection_missing", g_last_request_id,
                     StringFormat("position_sl=%s; position_tp=%s; expected_sl=%s; expected_tp=%s",
                                  DoubleToString(actual_sl, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)),
                                  DoubleToString(actual_tp, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)),
                                  DoubleToString(g_analysis.stop_loss, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)),
                                  DoubleToString(g_analysis.take_profit, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS))));
         if(g_manual_execution_pending)
            RecordEvent("manual_order_ambiguous", g_last_request_id, "ordem sem proteção SL/TP confirmada na posição");
        }
      else
        {
         ReleaseExecutionLock(g_execution_lock_name, g_execution_lock_token);
         g_execution_lock_name = "";
         g_execution_lock_token = 0.0;
         if(transaction_logged)
            g_status = "Execução confirmada com SL/TP ativos";
         if(g_manual_execution_pending)
            RecordEvent("manual_order_confirmed", g_last_request_id,
                        "posição e proteções SL/TP confirmadas após transação");
        }
      g_manual_execution_pending = false;
     }
   if(transaction_logged && !g_execution_blocked && !HasPositionForSymbol(g_symbol) &&
      !HasActiveOrderForSymbol(g_symbol) && g_automation_enabled)
      g_status = "Posição encerrada · polling será retomado no próximo intervalo";
   UpdatePanel();
  }
