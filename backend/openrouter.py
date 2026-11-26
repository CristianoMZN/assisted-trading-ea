"""OpenRouter structured-output client with fail-closed candidate validation."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from urllib.parse import urlsplit
from typing import Any, Callable

import httpx

from backend.config import openrouter_model, openrouter_timeout_seconds
from backend.prompts import load_prompt


OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
DECISION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "action": {"type": "string", "enum": ["BUY", "SELL", "NO_SIGNAL"]},
        "reference_price": {"type": ["number", "null"]},
        "stop_loss": {"type": ["number", "null"]},
        "take_profit": {"type": ["number", "null"]},
        "risk_reward": {"type": ["string", "null"], "enum": ["1:2", "1:3", None]},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "scenario": {"type": "string", "maxLength": 240},
    },
    "required": ["action", "reference_price", "stop_loss", "take_profit", "risk_reward", "confidence", "scenario"],
}
TECHNICAL_INTERPRETATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "trend": {"type": "string", "enum": ["bullish", "bearish", "sideways", "unclear"]},
        "momentum": {"type": "string", "enum": ["positive", "negative", "mixed", "unclear"]},
        "summary": {"type": "string", "maxLength": 240},
    },
    "required": ["trend", "momentum", "summary"],
}
NEWS_ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {"type": "string", "enum": ["available", "no_relevant_news", "unavailable"], "description": "Use exactly one enum value: available with items, no_relevant_news after a completed empty search, unavailable if research failed."},
        "summary": {"type": "string", "maxLength": 600},
        "items": {
            "type": "array",
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string", "maxLength": 240},
                    "url": {"type": "string", "maxLength": 1000},
                    "published_at": {"type": ["string", "null"]},
                    "confirmation": {"type": "string", "enum": ["official_confirmation", "independently_reported", "single_report", "unverified_rumor"], "description": "Use exactly one enum value. Official primary source, independent corroboration, one attributed report, or unverified rumor respectively."},
                    "relevance": {"type": "string", "enum": ["high", "medium"]},
                    "instrument_effect": {"type": "string", "enum": ["supports_upside", "supports_downside", "mixed", "unclear"]},
                    "fact_summary": {"type": "string", "maxLength": 500},
                    "transmission_channel": {"type": "string", "maxLength": 300},
                },
                "required": ["title", "url", "published_at", "confirmation", "relevance", "instrument_effect", "fact_summary", "transmission_channel"],
            },
        },
    },
    "required": ["status", "summary", "items"],
}

MACRO_NEWS_DOMAINS = [
    "bcb.gov.br", "ibge.gov.br", "gov.br", "tesourotransparente.gov.br", "b3.com.br",
    "federalreserve.gov", "fred.stlouisfed.org", "bls.gov", "bea.gov", "home.treasury.gov", "census.gov", "cftc.gov",
    "ecb.europa.eu", "imf.org", "bis.org", "oecd.org", "worldbank.org", "opec.org",
    "reuters.com", "bloomberg.com", "ft.com", "wsj.com", "valor.globo.com", "estadao.com.br", "apnews.com",
]
MACRO_PRIMARY_DOMAINS = {
    "bcb.gov.br", "ibge.gov.br", "gov.br", "tesourotransparente.gov.br", "b3.com.br",
    "federalreserve.gov", "fred.stlouisfed.org", "bls.gov", "bea.gov", "home.treasury.gov", "census.gov", "cftc.gov",
    "ecb.europa.eu", "imf.org", "bis.org", "oecd.org", "worldbank.org", "opec.org",
}
MACRO_NEWS_TOOLS = [
    {
        "type": "openrouter:web_search",
        "parameters": {
            "engine": "exa",
            "mode": "fast",
            "max_results": 4,
            "max_uses": 3,
            "max_total_results": 8,
            "search_context_size": "low",
            "allowed_domains": MACRO_NEWS_DOMAINS,
        },
    },
    {
        "type": "openrouter:web_fetch",
        "parameters": {
            "engine": "openrouter",
            "max_uses": 4,
            "max_content_tokens": 3500,
            "allowed_domains": MACRO_NEWS_DOMAINS,
        },
    },
]


class OpenRouterError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def validate_candidate(value: Any) -> dict:
    if not isinstance(value, dict) or set(value) != set(DECISION_SCHEMA["properties"]):
        raise OpenRouterError("invalid_model_output", "Model output does not match the required decision schema.", retryable=False)
    action = value.get("action")
    if action not in ("BUY", "SELL", "NO_SIGNAL"):
        raise OpenRouterError("invalid_model_output", "Model output contains an unsupported action.", retryable=False)
    if value.get("confidence") not in ("low", "medium", "high"):
        raise OpenRouterError("invalid_model_output", "Model output contains an unsupported confidence value.", retryable=False)
    if not isinstance(value.get("scenario"), str) or not value["scenario"].strip() or len(value["scenario"]) > 240:
        raise OpenRouterError("invalid_model_output", "Model output explanation is missing or too long.", retryable=False)
    if action == "NO_SIGNAL":
        if any(value.get(field) is not None for field in ("reference_price", "stop_loss", "take_profit", "risk_reward")):
            raise OpenRouterError("invalid_model_output", "No-signal model output must not contain actionable prices.", retryable=False)
        return value
    if value.get("risk_reward") not in ("1:2", "1:3"):
        raise OpenRouterError("invalid_model_output", "Model output contains an unsupported risk-reward value.", retryable=False)
    prices = [value.get(field) for field in ("reference_price", "stop_loss", "take_profit")]
    if any(isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0 for price in prices):
        raise OpenRouterError("invalid_model_output", "Model output prices must be finite positive numbers.", retryable=False)
    return value


class OpenRouterClient:
    def __init__(
        self,
        api_key_provider: Callable[[], str | None],
        *,
        model: str | None = None,
        news_model: str | None = None,
        technical_model: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.api_key_provider = api_key_provider
        self.model = model if model is not None else openrouter_model("decision")
        self.news_model = news_model if news_model is not None else openrouter_model("news_analysis")
        self.technical_model = (
            technical_model
            if technical_model is not None
            else (model if model is not None else openrouter_model("technical_interpretation"))
        )
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else openrouter_timeout_seconds()
        self.transport = transport

    async def _complete(self, context: dict, *, agent: str, model: str, schema: dict, prompt: str, schema_name: str) -> dict:
        api_key = self.api_key_provider()
        if not api_key:
            raise OpenRouterError("provider_key_missing", "OpenRouter credential is not configured.", retryable=False)
        if not model:
            setting_by_agent = {
                "news_analysis": "OPENROUTER_MODEL_NEWS_ANALYSIS",
                "technical_interpretation": "OPENROUTER_MODEL_TECHNICAL_INTERPRETATION",
                "decision": "OPENROUTER_MODEL_DECISION",
            }
            setting_name = setting_by_agent[agent]
            raise OpenRouterError("model_not_configured", f"{setting_name} is not configured.", retryable=False)
        body = {
            "model": model,
            "temperature": 0,
            "stream": False,
            "provider": {"require_parameters": True},
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False, allow_nan=False)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
        }
        if agent == "news_analysis":
            body["tools"] = MACRO_NEWS_TOOLS
            body["tool_choice"] = "required"
            body["max_tool_calls"] = 7
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = await client.post(OPENROUTER_CHAT_COMPLETIONS_URL, headers=headers, json=body)
        except httpx.TimeoutException as exc:
            raise OpenRouterError("provider_timeout", "OpenRouter request timed out.", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise OpenRouterError("provider_unavailable", "OpenRouter could not be reached.", retryable=True) from exc
        if response.status_code < 200 or response.status_code >= 300:
            if response.status_code == 404:
                try:
                    provider_message = response.json().get("error", {}).get("message", "")
                except (ValueError, TypeError, AttributeError):
                    provider_message = ""
                if isinstance(provider_message, str) and "No endpoints found that can handle the requested parameters" in provider_message:
                    raise OpenRouterError(
                        "model_parameters_unsupported",
                        "The configured OpenRouter model has no endpoint supporting the requested tools and structured output.",
                        retryable=False,
                    )
            retryable = response.status_code == 429 or response.status_code >= 500
            detail = f"OpenRouter returned HTTP {response.status_code}."
            if response.status_code == 429:
                try:
                    error = response.json().get("error", {})
                    metadata = error.get("metadata", {}) if isinstance(error, dict) else {}
                    limit_source = metadata.get("limit_source") if isinstance(metadata, dict) else None
                except (ValueError, TypeError, AttributeError):
                    limit_source = None
                if isinstance(limit_source, str) and re.fullmatch(r"[a-z0-9_]{1,80}", limit_source):
                    detail = f"OpenRouter returned HTTP 429 (limit_source={limit_source})."
            raise OpenRouterError("provider_unavailable", detail, retryable=retryable)
        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            candidate = json.loads(content) if isinstance(content, str) else content
        except (ValueError, TypeError, KeyError, IndexError):
            raise OpenRouterError("invalid_model_output", "OpenRouter response did not contain structured JSON.", retryable=False) from None
        if agent == "decision":
            result = validate_candidate(candidate)
        elif agent == "technical_interpretation":
            result = validate_technical_interpretation(candidate)
        else:
            result = validate_news_analysis(candidate, instrument=context.get("instrument", {}).get("logical_symbol"))
            usage = payload.get("usage") if isinstance(payload, dict) else None
            tool_use = None
            if isinstance(usage, dict):
                # Current OpenRouter responses use server_tool_use_details; keep
                # the older field for responses recorded by previous versions.
                tool_use = usage.get("server_tool_use_details") or usage.get("server_tool_use")
            if isinstance(tool_use, dict):
                result["tool_use"] = {
                    name: count for name in ("web_search_requests", "web_fetch_requests")
                    if isinstance((count := tool_use.get(name)), int) and not isinstance(count, bool) and count >= 0
                }
        result["model_id"] = payload.get("model", model)
        return result

    async def analyze_news(self, context: dict) -> dict:
        return await self._complete(
            context,
            agent="news_analysis",
            model=self.news_model,
            schema=NEWS_ANALYSIS_SCHEMA,
            prompt=load_prompt("news_analysis", instrument=context.get("instrument", {}).get("logical_symbol")),
            schema_name="macroeconomic_news_analysis",
        )

    async def interpret_technical(self, context: dict) -> dict:
        return await self._complete(
            context,
            agent="technical_interpretation",
            model=self.technical_model,
            schema=TECHNICAL_INTERPRETATION_SCHEMA,
            prompt=load_prompt("technical_interpretation"),
            schema_name="technical_interpretation",
        )

    async def decide(self, context: dict) -> dict:
        return await self._complete(
            context,
            agent="decision",
            model=self.model,
            schema=DECISION_SCHEMA,
            prompt=load_prompt("decision"),
            schema_name="trading_decision_candidate",
        )


def validate_technical_interpretation(value: Any) -> dict:
    if not isinstance(value, dict) or set(value) != set(TECHNICAL_INTERPRETATION_SCHEMA["properties"]):
        raise OpenRouterError("invalid_model_output", "Technical interpretation does not match the required schema.", retryable=False)
    if value.get("trend") not in ("bullish", "bearish", "sideways", "unclear"):
        raise OpenRouterError("invalid_model_output", "Technical interpretation contains an unsupported trend.", retryable=False)
    if value.get("momentum") not in ("positive", "negative", "mixed", "unclear"):
        raise OpenRouterError("invalid_model_output", "Technical interpretation contains unsupported momentum.", retryable=False)
    if not isinstance(value.get("summary"), str) or not value["summary"].strip() or len(value["summary"]) > 240:
        raise OpenRouterError("invalid_model_output", "Technical interpretation summary is missing or too long.", retryable=False)
    return value


def validate_news_analysis(value: Any, instrument: str | None = None) -> dict:
    if instrument not in ("WIN", "WDO"):
        raise OpenRouterError("invalid_model_output", "A WIN or WDO instrument is required for macro research.", retryable=False)
    expected = set(NEWS_ANALYSIS_SCHEMA["properties"])
    if not isinstance(value, dict) or set(value) != expected:
        if isinstance(value, dict):
            missing = ", ".join(sorted(expected - set(value))) or "none"
            extra_count = len(set(value) - expected)
            detail = f"missing fields: {missing}; unexpected field count: {extra_count}"
        else:
            detail = f"output type: {type(value).__name__}"
        raise OpenRouterError("invalid_model_output", f"Macroeconomic news output does not match the required schema ({detail}).", retryable=False)
    if value["status"] not in ("available", "no_relevant_news", "unavailable"):
        raise OpenRouterError("invalid_model_output", "Macroeconomic news output contains an unsupported status.", retryable=False)
    items = value["items"]
    if not isinstance(items, list) or len(items) > 4:
        raise OpenRouterError("invalid_model_output", "Macroeconomic news items are invalid.", retryable=False)
    item_keys = set(NEWS_ANALYSIS_SCHEMA["properties"]["items"]["items"]["properties"])
    allowed_hosts = tuple(MACRO_NEWS_DOMAINS)
    normalized_items = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise OpenRouterError("invalid_model_output", f"Macroeconomic news item {index} has an invalid type.", retryable=False)
        if set(item) != item_keys:
            detail = f"missing fields: {', '.join(sorted(item_keys - set(item))) or 'none'}; unexpected field count: {len(set(item) - item_keys)}"
            raise OpenRouterError("invalid_model_output", f"Macroeconomic news item {index} does not match the required schema ({detail}).", retryable=False)
        try:
            parsed_url = urlsplit(item["url"] if isinstance(item["url"], str) else "")
        except ValueError:
            parsed_url = urlsplit("")
        host = (parsed_url.hostname or "").lower()
        if parsed_url.scheme != "https" or parsed_url.username or parsed_url.password or not any(host == domain or host.endswith("." + domain) for domain in allowed_hosts) or len(item["url"]) > 1000:
            raise OpenRouterError("invalid_model_output", "A macroeconomic news URL is outside the allowed source list.", retryable=False)
        is_primary = any(host == domain or host.endswith("." + domain) for domain in MACRO_PRIMARY_DOMAINS)
        if item["confirmation"] not in ("official_confirmation", "independently_reported", "single_report", "unverified_rumor"):
            raise OpenRouterError("invalid_model_output", "A macroeconomic news item has an unsupported confirmation level.", retryable=False)
        if item["relevance"] not in ("high", "medium"):
            raise OpenRouterError("invalid_model_output", "A macroeconomic news item has an unsupported assessment.", retryable=False)
        if item["instrument_effect"] not in ("supports_upside", "supports_downside", "mixed", "unclear"):
            raise OpenRouterError("invalid_model_output", "A macroeconomic news item has an unsupported instrument effect.", retryable=False)
        if item["confirmation"] == "unverified_rumor" and item["instrument_effect"] != "unclear":
            raise OpenRouterError("invalid_model_output", "An unverified rumor cannot carry a directional instrument assessment.", retryable=False)
        published_at_value = item["published_at"]
        if published_at_value is not None:
            if not isinstance(published_at_value, str):
                raise OpenRouterError("invalid_model_output", "A macroeconomic news item has an invalid publication time type.", retryable=False)
            try:
                published_at = datetime.fromisoformat(published_at_value.replace("Z", "+00:00"))
            except ValueError:
                published_at = None
            if published_at is None or published_at.tzinfo is None:
                published_at_value = None
        for field, limit in (("title", 240), ("fact_summary", 500), ("transmission_channel", 300)):
            field_value = item[field]
            if not isinstance(field_value, str):
                problem = "must be a string"
            elif not field_value.strip():
                problem = "must be non-empty"
            elif len(field_value) > limit:
                problem = f"exceeds {limit} characters"
            else:
                continue
            raise OpenRouterError("invalid_model_output", f"A macroeconomic news item has invalid {field} text ({problem}).", retryable=False)
        normalized_items.append({**item, "published_at": published_at_value, "source_name": host, "source_type": "primary_official" if is_primary else "financial_news", "instrument": instrument})
    if value["status"] == "available" and not items:
        raise OpenRouterError("invalid_model_output", "Available macroeconomic news must include at least one item.", retryable=False)
    if value["status"] != "available" and items:
        raise OpenRouterError("invalid_model_output", "Non-available macroeconomic news must not include items.", retryable=False)
    value = {**value, "items": normalized_items}
    summary = value["summary"]
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 600:
        raise OpenRouterError("invalid_model_output", "Macroeconomic news summary is missing or invalid.", retryable=False)
    return value
