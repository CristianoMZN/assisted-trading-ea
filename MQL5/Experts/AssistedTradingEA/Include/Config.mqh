#ifndef ASSISTED_TRADING_CONFIG_MQH
#define ASSISTED_TRADING_CONFIG_MQH

enum ENUM_LOGICAL_INSTRUMENT
  {
   LOGICAL_WIN = 0,
   LOGICAL_WDO = 1
  };

input ENUM_LOGICAL_INSTRUMENT InpLogicalInstrument = LOGICAL_WDO; // Ativo lógico (WIN/WDO)
input string InpBrokerSymbol = ""; // Símbolo do broker (vazio = gráfico)
input string InpBackendUrl = "http://127.0.0.1:9000/v1/analyze"; // URL da API FastAPI
input int InpPollingIntervalMinutes = 1; // Intervalo da análise (minutos)
input int InpHttpTimeoutMs = 3000; // Timeout da API (ms)
input double InpMaxLossPerTrade = 0.0; // Perda máxima por operação (moeda da conta)
input string InpRiskRewardPreference = "1:2"; // RR geométrico (1:2 ou 1:3)
input double InpMaxStopPoints = 0.0; // Stop máximo (pontos MT5, não ticks)
input double InpRoundTripCostPerContract = 0.0; // Custo ida + volta/contrato (moeda da conta)
input double InpDailyLossLimit = 0.0; // Limite de perda diária (moeda da conta)
input double InpInitialContracts = 1.0; // Quantidade inicial de contratos
input ulong InpMagicNumber = 72511025; // Magic ID deste EA
input int InpDeviationPoints = 10; // Desvio máximo (pontos MT5)
input bool InpUseFixture = false; // Usar fixture (somente teste)
input bool InpFixtureNoSignal = false; // Fixture retorna sem sinal
input string InpLogFileName = "AssistedTradingEA.jsonl"; // Arquivo de auditoria

string LogicalSymbolName()
  {
   return (InpLogicalInstrument == LOGICAL_WIN ? "WIN" : "WDO");
  }

string ConfiguredSymbol()
  {
   if(StringLen(InpBrokerSymbol) > 0)
      return InpBrokerSymbol;
   return _Symbol;
  }

#endif
