#ifndef ASSISTED_TRADING_CONFIG_MQH
#define ASSISTED_TRADING_CONFIG_MQH

enum ENUM_LOGICAL_INSTRUMENT
  {
   LOGICAL_WIN = 0,
   LOGICAL_WDO = 1
  };

input ENUM_LOGICAL_INSTRUMENT InpLogicalInstrument = LOGICAL_WDO;
input string InpBrokerSymbol = "";
input string InpBackendUrl = "";
input int InpPollingIntervalMinutes = 1;
input int InpHttpTimeoutMs = 3000;
input double InpMaxLossPerTrade = 0.0; // Moeda da conta; zero bloqueia a automação.
input string InpRiskRewardPreference = "1:2";
input double InpMaxStopPoints = 0.0;
input double InpRoundTripCostPerContract = 0.0;
input double InpDailyLossLimit = 0.0;
input double InpInitialContracts = 1.0;
input ulong InpMagicNumber = 72511025;
input int InpDeviationPoints = 10;
input bool InpUseFixture = false;
input bool InpFixtureNoSignal = false;
input string InpLogFileName = "AssistedTradingEA.jsonl";

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
