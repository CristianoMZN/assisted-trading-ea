#ifndef ASSISTED_TRADING_AUDIT_LOG_MQH
#define ASSISTED_TRADING_AUDIT_LOG_MQH

#include "MarketData.mqh"

bool WriteAuditEvent(const string file_name, const string event_name, const string symbol,
                     const string request_id, const string detail)
  {
   ResetLastError();
   int handle = FileOpen(file_name, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI |
                          FILE_SHARE_READ | FILE_SHARE_WRITE, 0, CP_UTF8);
   if(handle == INVALID_HANDLE)
      return false;
   if(!FileSeek(handle, 0, SEEK_END))
     {
      FileClose(handle);
      return false;
     }
   string line = "{\"schema_version\":\"1.0\",\"timestamp\":\"" + UtcIso8601(TimeGMT()) +
                 "\",\"event\":\"" + JsonEscape(event_name) + "\",\"symbol\":\"" +
                 JsonEscape(symbol) + "\",\"request_id\":\"" + JsonEscape(request_id) +
                 "\",\"detail\":\"" + JsonEscape(detail) + "\"}\r\n";
   uint written = FileWriteString(handle, line);
   FileFlush(handle);
   FileClose(handle);
   return (written > 0);
  }

#endif
