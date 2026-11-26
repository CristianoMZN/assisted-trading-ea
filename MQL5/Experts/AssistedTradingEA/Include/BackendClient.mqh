#ifndef ASSISTED_TRADING_BACKEND_CLIENT_MQH
#define ASSISTED_TRADING_BACKEND_CLIENT_MQH

#include "Json.mqh"
#include "Types.mqh"

datetime ParseUtcIso8601(const string value)
  {
   if(StringLen(value) != 20 || StringSubstr(value, 10, 1) != "T" || StringSubstr(value, 19, 1) != "Z")
      return 0;
   string date_part = StringSubstr(value, 0, 10);
   StringReplace(date_part, "-", ".");
   string time_part = StringSubstr(value, 11, 8);
   return StringToTime(date_part + " " + time_part);
  }

bool IsStableReasonCode(const string value)
  {
   int length = StringLen(value);
   if(length == 0 || StringSubstr(value, 0, 1) == "_" || StringSubstr(value, length - 1, 1) == "_")
      return false;
   for(int i = 0; i < length; i++)
     {
      ushort ch = StringGetCharacter(value, i);
      bool valid = ((ch >= 97 && ch <= 122) || (ch >= 48 && ch <= 57) || ch == 95);
      if(!valid)
         return false;
     }
   return true;
  }

bool ValidateSourceBlocks(const JsonToken &tokens[], int root, datetime now,
                          string &summary, datetime &source_expiry, string &error)
  {
   int sources_index = JsonFind(tokens, root, "sources");
   if(sources_index < 0 || tokens[sources_index].type != JSON_ARRAY)
     {
      error = "Resposta sem lista de fontes";
      return false;
     }
   bool technical_found = false;
   bool news_found = false;
   bool market_found = false;
   summary = "";
   source_expiry = 0;
   for(int i = 0; i < ArraySize(tokens); i++)
     {
      if(tokens[i].parent != sources_index || tokens[i].type != JSON_OBJECT)
         continue;
      string type = JsonString(tokens, i, "type");
      string status = JsonString(tokens, i, "status");
      string source = JsonString(tokens, i, "source");
      string observed_text = JsonString(tokens, i, "observed_at");
      string valid_text = JsonString(tokens, i, "valid_until");
      string detail = JsonString(tokens, i, "summary");
      datetime observed_at = ParseUtcIso8601(observed_text);
      datetime valid_until = ParseUtcIso8601(valid_text);
      if(type == "technical") technical_found = true;
      else if(type == "news") news_found = true;
      else if(type == "prediction_market") market_found = true;
      else
        {
         error = "Tipo de fonte desconhecido: " + type;
         return false;
        }
      bool not_relevant = (type == "prediction_market" && status == "not_relevant");
      bool informative_absence = ((type == "news" &&
                                   (status == "available" || status == "empty" || status == "unavailable" || status == "not_configured")) ||
                                  (type == "technical" && status == "insufficient"));
      if(status != "valid" && !not_relevant && !informative_absence)
        {
         error = "Fonte " + type + " inválida ou desatualizada: " + status;
         return false;
        }
      if(StringLen(source) == 0 || StringLen(detail) == 0 || observed_at == 0 || valid_until == 0 ||
         observed_at > now || (!not_relevant && valid_until <= now))
        {
         error = "Fonte " + type + " sem origem/horário válido ou vencida";
         return false;
        }
      if(status == "valid" || status == "available" || status == "insufficient")
         if(source_expiry == 0 || valid_until < source_expiry)
         source_expiry = valid_until;
      if(StringLen(summary) > 0)
         summary += " | ";
      summary += type + ": " + detail + " (" + source + ")";
     }
   if(!technical_found || !news_found || !market_found)
     {
      error = "Resposta precisa incluir blocos technical, news e prediction_market";
      return false;
     }
   return true;
  }

bool ParseAnalysisResponse(const string json, const string expected_id, const string expected_symbol,
                           const double tick_size, AnalysisData &analysis, string &error)
  {
   error = "";
   analysis.valid = false;
   analysis.actionable = false;
   analysis.fixture = false;
   analysis.reason_code = "";
   analysis.reason = "";
   if(StringLen(json) == 0 || StringLen(json) > 262144)
     {
      error = "Resposta JSON vazia ou excede o limite de 256 KiB";
      return false;
     }
   JsonToken tokens[];
   if(!JsonParse(json, tokens))
     {
      error = "JSON inválido na resposta do backend";
      return false;
     }
   if(JsonString(tokens, 0, "schema_version") != "1.1" ||
      JsonString(tokens, 0, "message_type") != "analysis_response")
     {
      error = "Versão ou tipo de mensagem incompatível";
      return false;
     }
   analysis.request_id = JsonString(tokens, 0, "request_id");
   if(analysis.request_id != expected_id)
     {
      error = "request_id da resposta não corresponde ao pedido";
      return false;
     }
   int instrument = JsonFind(tokens, 0, "instrument");
   if(instrument < 0 || tokens[instrument].type != JSON_OBJECT)
     {
      error = "Instrumento ausente na resposta";
      return false;
     }
   analysis.symbol = JsonString(tokens, instrument, "broker_symbol");
   if(analysis.symbol != expected_symbol)
     {
      error = "Símbolo da resposta não corresponde ao gráfico";
      return false;
     }
   analysis.created_at = ParseUtcIso8601(JsonString(tokens, 0, "created_at"));
   analysis.expires_at = ParseUtcIso8601(JsonString(tokens, 0, "expires_at"));
   datetime now = TimeGMT();
   if(analysis.created_at == 0 || analysis.expires_at == 0 || analysis.created_at > now || analysis.expires_at <= now)
     {
      error = "Resposta ausente, futura ou vencida";
      return false;
     }
   datetime source_expiry;
   if(!ValidateSourceBlocks(tokens, 0, now, analysis.sources_summary, source_expiry, error))
      return false;
   if(source_expiry > 0 && source_expiry < analysis.expires_at)
      analysis.expires_at = source_expiry;

   string status = JsonString(tokens, 0, "status");
   int decision = JsonFind(tokens, 0, "decision");
   if(status == "no_signal")
     {
      analysis.reason_code = JsonString(tokens, 0, "reason_code");
      analysis.reason = JsonString(tokens, 0, "reason");
      if(decision < 0 || tokens[decision].type != JSON_NULL || !IsStableReasonCode(analysis.reason_code) || StringLen(analysis.reason) == 0)
        {
         error = "Resposta no_signal deve conter motivo e não pode conter decisão";
         return false;
        }
      analysis.valid = true;
      analysis.actionable = false;
      analysis.direction = "NONE";
      return true;
     }
   int reason_code_index = JsonFind(tokens, 0, "reason_code");
   int reason_index = JsonFind(tokens, 0, "reason");
   if(reason_code_index < 0 || tokens[reason_code_index].type != JSON_NULL ||
      reason_index < 0 || tokens[reason_index].type != JSON_NULL)
     {
      error = "Resposta acionável não pode conter motivo de no_signal";
      return false;
     }
   if(status != "actionable" || decision < 0 || tokens[decision].type != JSON_OBJECT)
     {
      error = "Status ou boleta da resposta inválidos";
      return false;
     }

   analysis.direction = JsonString(tokens, decision, "direction");
   if((analysis.direction != "BUY" && analysis.direction != "SELL") ||
      JsonString(tokens, decision, "entry_type") != "MARKET")
     {
      error = "Direção ou tipo de entrada incompatível";
      return false;
     }
   analysis.reference_price = JsonNumber(tokens, decision, "reference_price", -1.0);
   analysis.stop_loss = JsonNumber(tokens, decision, "stop_loss", -1.0);
   analysis.take_profit = JsonNumber(tokens, decision, "take_profit", -1.0);
   analysis.risk_reward = JsonString(tokens, decision, "risk_reward");
   analysis.scenario = JsonString(tokens, decision, "scenario");
   analysis.confidence = JsonString(tokens, decision, "confidence");
   if(analysis.reference_price <= 0 || analysis.stop_loss <= 0 || analysis.take_profit <= 0 ||
      tick_size <= 0 || (analysis.risk_reward != "1:2" && analysis.risk_reward != "1:3") ||
      (analysis.confidence != "low" && analysis.confidence != "medium" && analysis.confidence != "high") ||
      StringLen(analysis.scenario) == 0)
     {
      error = "Preços ou relação risco-retorno inválidos";
      return false;
     }
   double risk = 0.0;
   double reward = 0.0;
   if(analysis.direction == "BUY")
     {
      if(analysis.stop_loss >= analysis.reference_price || analysis.take_profit <= analysis.reference_price)
        {
         error = "Preços da compra não estão na ordem esperada";
         return false;
        }
      risk = analysis.reference_price - analysis.stop_loss;
      reward = analysis.take_profit - analysis.reference_price;
     }
   else
     {
      if(analysis.take_profit >= analysis.reference_price || analysis.stop_loss <= analysis.reference_price)
        {
         error = "Preços da venda não estão na ordem esperada";
         return false;
        }
      risk = analysis.stop_loss - analysis.reference_price;
      reward = analysis.reference_price - analysis.take_profit;
     }
   double ratio = (analysis.risk_reward == "1:2" ? 2.0 : 3.0);
   double reference_steps = analysis.reference_price / tick_size;
   double stop_steps = analysis.stop_loss / tick_size;
   double target_steps = analysis.take_profit / tick_size;
   if(MathAbs(reference_steps - MathRound(reference_steps)) > 0.000001 ||
      MathAbs(stop_steps - MathRound(stop_steps)) > 0.000001 ||
      MathAbs(target_steps - MathRound(target_steps)) > 0.000001 ||
      MathAbs(reward - risk * ratio) > tick_size)
     {
      error = "Preços não respeitam tick size ou relação risco-retorno declarada";
      return false;
     }
   analysis.valid = true;
   analysis.actionable = true;
   return true;
  }

bool PostMarketSnapshot(const string endpoint, const int timeout_ms, const string body,
                        string &response, int &http_status, string &error)
  {
   response = "";
   error = "";
   http_status = -1;
   if(StringLen(endpoint) == 0 || (StringFind(endpoint, "http://") != 0 && StringFind(endpoint, "https://") != 0))
     {
      error = "Configure a URL HTTP/HTTPS da REST API FastAPI";
      return false;
     }
   char request_data[];
   int byte_count = StringToCharArray(body, request_data, 0, WHOLE_ARRAY, CP_UTF8);
   if(byte_count <= 1)
     {
      error = "Não foi possível codificar o snapshot em UTF-8";
      return false;
     }
   ArrayResize(request_data, byte_count - 1);
   char response_data[];
   string response_headers;
   http_status = WebRequest("POST", endpoint, "Content-Type: application/json\r\n", timeout_ms,
                            request_data, response_data, response_headers);
   if(http_status < 0)
     {
      error = StringFormat("WebRequest falhou (%d). Libere o endpoint nas opções do MetaTrader.", GetLastError());
      return false;
     }
   response = CharArrayToString(response_data, 0, -1, CP_UTF8);
   if(http_status < 200 || http_status >= 300)
     {
      error = StringFormat("Backend respondeu HTTP %d", http_status);
      return false;
     }
   return true;
  }

#endif
