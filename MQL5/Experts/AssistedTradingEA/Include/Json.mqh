#ifndef ASSISTED_TRADING_JSON_MQH
#define ASSISTED_TRADING_JSON_MQH

enum ENUM_JSON_TOKEN_TYPE
  {
   JSON_OBJECT = 1,
   JSON_ARRAY = 2,
   JSON_STRING = 3,
   JSON_NUMBER = 4,
   JSON_BOOL = 5,
   JSON_NULL = 6
  };

struct JsonToken
  {
   int parent;
   int type;
   string key;
   string value;
  };

void JsonSkipWhitespace(const string text, int &position)
  {
   int length = StringLen(text);
   while(position < length)
     {
      ushort c = StringGetCharacter(text, position);
      if(c != 32 && c != 9 && c != 10 && c != 13)
         break;
      position++;
     }
  }

bool JsonReadString(const string text, int &position, string &value)
  {
   int length = StringLen(text);
   if(position >= length || StringGetCharacter(text, position) != 34)
      return false;
   position++;
   value = "";
   while(position < length)
     {
      ushort c = StringGetCharacter(text, position++);
      if(c == 34)
         return true;
      if(c == 92)
        {
         if(position >= length)
            return false;
         ushort escaped = StringGetCharacter(text, position++);
         if(escaped == 34 || escaped == 92 || escaped == 47)
            value += StringSubstr(text, position - 1, 1);
         else if(escaped == 110)
            value += "\n";
         else if(escaped == 114)
            value += "\r";
         else if(escaped == 116)
            value += "\t";
         else if(escaped == 98)
            value += "\b";
         else if(escaped == 102)
            value += "\f";
         else if(escaped == 117)
           {
            if(position + 4 > length)
               return false;
            value += "\\u" + StringSubstr(text, position, 4);
            position += 4;
           }
         else
            return false;
        }
      else
         value += StringSubstr(text, position - 1, 1);
     }
   return false;
  }

int JsonAppendToken(JsonToken &tokens[], int parent, int type, string key, string value)
  {
   int index = ArraySize(tokens);
   if(ArrayResize(tokens, index + 1) != index + 1)
      return -1;
   tokens[index].parent = parent;
   tokens[index].type = type;
   tokens[index].key = key;
   tokens[index].value = value;
   return index;
  }

bool JsonIsNumberLiteral(const string raw)
  {
   int length = StringLen(raw);
   if(length == 0)
      return false;
   int i = 0;
   if(StringGetCharacter(raw, i) == 45)
      i++;
   if(i >= length)
      return false;
   ushort first = StringGetCharacter(raw, i);
   if(first == 48)
     {
      i++;
      if(i < length && StringGetCharacter(raw, i) >= 48 && StringGetCharacter(raw, i) <= 57)
         return false;
     }
   else
     {
      if(first < 49 || first > 57)
         return false;
      while(i < length && StringGetCharacter(raw, i) >= 48 && StringGetCharacter(raw, i) <= 57)
         i++;
     }
   if(i < length && StringGetCharacter(raw, i) == 46)
     {
      i++;
      int fraction_start = i;
      while(i < length && StringGetCharacter(raw, i) >= 48 && StringGetCharacter(raw, i) <= 57)
         i++;
      if(i == fraction_start)
         return false;
     }
   if(i < length && (StringGetCharacter(raw, i) == 101 || StringGetCharacter(raw, i) == 69))
     {
      i++;
      if(i < length && (StringGetCharacter(raw, i) == 43 || StringGetCharacter(raw, i) == 45))
         i++;
      int exponent_start = i;
      while(i < length && StringGetCharacter(raw, i) >= 48 && StringGetCharacter(raw, i) <= 57)
         i++;
      if(i == exponent_start)
         return false;
     }
   return (i == length);
  }

bool JsonReadValue(const string text, int &position, int parent, string key, JsonToken &tokens[])
  {
   JsonSkipWhitespace(text, position);
   int length = StringLen(text);
   if(position >= length)
      return false;
   ushort c = StringGetCharacter(text, position);
   if(c == 123 || c == 91)
     {
      int type = (c == 123 ? JSON_OBJECT : JSON_ARRAY);
      int node = JsonAppendToken(tokens, parent, type, key, "");
      if(node < 0)
         return false;
      position++;
      JsonSkipWhitespace(text, position);
      ushort closing = (c == 123 ? 125 : 93);
      if(position < length && StringGetCharacter(text, position) == closing)
        {
         position++;
         return true;
        }
      while(position < length)
        {
         JsonSkipWhitespace(text, position);
         if(type == JSON_OBJECT)
           {
            string child_key;
            if(!JsonReadString(text, position, child_key))
               return false;
            for(int token_index = 0; token_index < ArraySize(tokens); token_index++)
               if(tokens[token_index].parent == node && tokens[token_index].key == child_key)
                  return false;
            JsonSkipWhitespace(text, position);
            if(position >= length || StringGetCharacter(text, position++) != 58)
               return false;
            if(!JsonReadValue(text, position, node, child_key, tokens))
               return false;
           }
         else
           {
            if(!JsonReadValue(text, position, node, "", tokens))
               return false;
           }
         JsonSkipWhitespace(text, position);
         if(position >= length)
            return false;
         ushort separator = StringGetCharacter(text, position++);
         if(separator == closing)
            return true;
         if(separator != 44)
            return false;
        }
      return false;
     }
   if(c == 34)
     {
      string value;
      if(!JsonReadString(text, position, value))
         return false;
      return (JsonAppendToken(tokens, parent, JSON_STRING, key, value) >= 0);
     }
   int start = position;
   while(position < length)
     {
      c = StringGetCharacter(text, position);
      if(c == 44 || c == 125 || c == 93 || c == 32 || c == 9 || c == 10 || c == 13)
         break;
      position++;
     }
   if(start == position)
      return false;
   string raw = StringSubstr(text, start, position - start);
   if(raw == "null")
      return (JsonAppendToken(tokens, parent, JSON_NULL, key, raw) >= 0);
   if(raw == "true" || raw == "false")
      return (JsonAppendToken(tokens, parent, JSON_BOOL, key, raw) >= 0);
   if(!JsonIsNumberLiteral(raw))
      return false;
   double number = StringToDouble(raw);
   if(!MathIsValidNumber(number))
      return false;
   return (JsonAppendToken(tokens, parent, JSON_NUMBER, key, raw) >= 0);
  }

bool JsonParse(const string text, JsonToken &tokens[])
  {
   ArrayResize(tokens, 0);
   int position = 0;
   if(!JsonReadValue(text, position, -1, "", tokens))
      return false;
   JsonSkipWhitespace(text, position);
   return (position == StringLen(text) && ArraySize(tokens) > 0 && tokens[0].type == JSON_OBJECT);
  }

int JsonFind(const JsonToken &tokens[], int parent, const string key)
  {
   for(int i = 0; i < ArraySize(tokens); i++)
      if(tokens[i].parent == parent && tokens[i].key == key)
         return i;
   return -1;
  }

string JsonString(const JsonToken &tokens[], int parent, const string key, string fallback = "")
  {
   int index = JsonFind(tokens, parent, key);
   if(index < 0 || (tokens[index].type != JSON_STRING && tokens[index].type != JSON_NUMBER && tokens[index].type != JSON_BOOL))
      return fallback;
   return tokens[index].value;
  }

double JsonNumber(const JsonToken &tokens[], int parent, const string key, double fallback = 0.0)
  {
   int index = JsonFind(tokens, parent, key);
   if(index < 0 || tokens[index].type != JSON_NUMBER)
      return fallback;
   return StringToDouble(tokens[index].value);
  }

bool JsonHas(const JsonToken &tokens[], int parent, const string key)
  {
   return (JsonFind(tokens, parent, key) >= 0);
  }

#endif
