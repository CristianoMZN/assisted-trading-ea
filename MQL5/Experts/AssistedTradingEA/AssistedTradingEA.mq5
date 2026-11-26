#property strict
#property version   "1.00"
#property description "Captura dados M5, consulta backend FastAPI e executa decisões após ativação manual."

#include "Include/Config.mqh"
#include "Include/Types.mqh"
#include "Include/MarketData.mqh"
#include "Include/BackendClient.mqh"
#include "Include/Panel.mqh"
#include "Include/AuditLog.mqh"
#include "Include/Execution.mqh"

AnalysisData g_analysis;
string g_symbol = "";
string g_status = "Inicializando";
string g_last_request_id = "";
bool g_automation_enabled = false;
bool g_execution_blocked = false;
bool g_execution_pending = false;
ulong g_pending_order_ticket = 0;
ulong g_pending_deal_ticket = 0;
string g_execution_lock_name = "";
double g_execution_lock_token = 0.0;
double g_contracts = 0.0;
int g_poll_interval_minutes = 1;

bool RecordEvent(const string event_name, const string request_id, const string detail)
  {
   if(WriteAuditEvent(InpLogFileName, event_name, g_symbol, request_id, detail))
      return true;
   g_execution_blocked = true;
   g_status = "Falha no registro local; novas operações automáticas bloqueadas";
   Print(g_status, " (", GetLastError(), ")");
   return false;
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
   if(volume <= 0 || volume < min_volume || volume > max_volume || step <= 0 ||
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
   if(InpMaxLossPerTrade <= 0)
     {
      error = "Configure uma perda máxima positiva por operação";
      return false;
     }
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
      g_status = "Análise vencida · sem sinal atual";
     }
   bool position_open = (StringLen(g_symbol) > 0 && (HasPositionForSymbol(g_symbol) || HasActiveOrderForSymbol(g_symbol)));
   PanelUpdate(g_symbol, g_status, g_analysis, g_automation_enabled, g_poll_interval_minutes,
               g_contracts, position_open, g_execution_blocked);
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

void HandleAnalysisCycle()
  {
   if(!g_automation_enabled)
      return;
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

   string body;
   string build_error;
   if(!BuildMarketSnapshot(g_symbol, g_poll_interval_minutes, g_last_request_id, body, build_error))
     {
      ZeroMemory(g_analysis);
      g_status = "Captura indisponível: " + build_error;
      RecordEvent("capture_error", g_last_request_id, build_error);
      UpdatePanel();
      return;
     }
   if(!RecordEvent("snapshot_sent", g_last_request_id,
                   "POST snapshot M5/7d; payload_bytes=" + IntegerToString(StringLen(body))))
     {
      UpdatePanel();
      return;
     }

   string response;
   string http_error;
   int http_status;
   if(!PostMarketSnapshot(InpBackendUrl, InpHttpTimeoutMs, body, response, http_status, http_error))
     {
      ZeroMemory(g_analysis);
      g_status = http_error;
      RecordEvent("backend_error", g_last_request_id, http_error + "; HTTP=" + IntegerToString(http_status));
      UpdatePanel();
      return;
     }
   if(!RecordEvent("backend_response", g_last_request_id,
                   "HTTP " + IntegerToString(http_status) + "; response=" + response))
     {
      UpdatePanel();
      return;
     }

   string parse_error;
   double tick_size = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);
   if(!ParseAnalysisResponse(response, g_last_request_id, g_symbol, tick_size, g_analysis, parse_error))
     {
      ZeroMemory(g_analysis);
      g_status = "Resposta recusada: " + parse_error;
      RecordEvent("response_rejected", g_last_request_id, parse_error);
      UpdatePanel();
      return;
     }
   if(!g_analysis.actionable)
     {
      g_status = "Backend retornou sem sinal";
      RecordEvent("no_signal", g_last_request_id, g_analysis.sources_summary);
      UpdatePanel();
      return;
     }

   if(!RecordEvent("decision_payload", g_last_request_id, "request=" + body + "; response=" + response))
     {
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
   MqlTradeResult result;
   bool ambiguous;
   string execution_error;
   string lock_name;
   double lock_token = 0.0;
   if(!AcquireExecutionLock(g_symbol, lock_name, lock_token))
     {
      g_status = "Outra instância está processando uma ordem para este símbolo";
      RecordEvent("execution_lock_unavailable", g_last_request_id, g_status);
      UpdatePanel();
      return;
     }
   bool sent = ValidateAndSendMarketOrder(g_analysis, g_symbol, g_contracts, InpMaxLossPerTrade,
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
      g_status = "Ordem bloqueada/rejeitada: " + execution_error;
      RecordEvent("order_not_executed", g_last_request_id,
                  execution_error + "; retcode=" + IntegerToString((int)result.retcode));
      UpdatePanel();
      return;
     }
   g_status = StringFormat("Ordem enviada · retcode %u · deal %I64u", result.retcode, result.deal);
   bool logged_order = RecordEvent("order_executed", g_last_request_id,
                                   StringFormat("direction=%s; volume=%s; SL=%s; TP=%s; retcode=%u; order=%I64u; deal=%I64u; %s",
                                                g_analysis.direction, DoubleToString(g_contracts, 4),
                                                DoubleToString(g_analysis.stop_loss, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)),
                                                DoubleToString(g_analysis.take_profit, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS)),
                                                result.retcode, result.order, result.deal, result.comment));
   g_execution_pending = true;
   g_execution_lock_name = lock_name;
   g_execution_lock_token = lock_token;
   g_pending_order_ticket = result.order;
   g_pending_deal_ticket = result.deal;
   if(logged_order)
      g_status = "Ordem aceita; aguardando confirmação da transação";
   UpdatePanel();
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
   PanelCreate(g_contracts, g_poll_interval_minutes, g_automation_enabled);
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
   if(InpUseFixture)
     {
      BuildFixtureAnalysis();
      UpdatePanel();
      return;
     }
   if(g_automation_enabled)
      HandleAnalysisCycle();
   UpdatePanel();
  }

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   double requested_volume = g_contracts;
   int requested_interval = g_poll_interval_minutes;
   bool was_enabled = g_automation_enabled;
   if(!PanelHandleChartEvent(id, sparam, g_automation_enabled, requested_volume, requested_interval))
      return;
   if(id == CHARTEVENT_OBJECT_ENDEDIT)
     {
      g_contracts = requested_volume;
      string volume_error;
      if(sparam == "ATEA_VOLUME" && !ValidateConfiguredVolume(g_contracts, volume_error))
         g_status = volume_error;
      else if(sparam == "ATEA_VOLUME")
        {
         g_status = "Quantidade atualizada para " + DoubleToString(g_contracts, 2);
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
   bool transaction_logged = RecordEvent("trade_transaction", g_last_request_id, detail);
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
        }
      else
        {
         ReleaseExecutionLock(g_execution_lock_name, g_execution_lock_token);
         g_execution_lock_name = "";
         g_execution_lock_token = 0.0;
         if(transaction_logged)
            g_status = "Execução confirmada com SL/TP ativos";
        }
     }
   if(transaction_logged && !g_execution_blocked && !HasPositionForSymbol(g_symbol) &&
      !HasActiveOrderForSymbol(g_symbol) && g_automation_enabled)
      g_status = "Posição encerrada · polling será retomado no próximo intervalo";
   UpdatePanel();
  }
