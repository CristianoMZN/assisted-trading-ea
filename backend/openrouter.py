"""OpenRouter structured-output client with fail-closed candidate validation."""

from __future__ import annotations

import json
import math
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
        technical_model: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.api_key_provider = api_key_provider
        self.model = model if model is not None else openrouter_model("decision")
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
            setting_name = "OPENROUTER_MODEL_TECHNICAL_INTERPRETATION" if agent == "technical_interpretation" else "OPENROUTER_MODEL_DECISION"
            raise OpenRouterError("model_not_configured", f"{setting_name} is not configured.", retryable=False)
        body = {
            "model": model,
            "temperature": 0,
            "stream": False,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False, allow_nan=False)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = await client.post(OPENROUTER_CHAT_COMPLETIONS_URL, headers=headers, json=body)
        except httpx.TimeoutException as exc:
            raise OpenRouterError("provider_timeout", "OpenRouter request timed out.", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise OpenRouterError("provider_unavailable", "OpenRouter could not be reached.", retryable=True) from exc
        if response.status_code < 200 or response.status_code >= 300:
            retryable = response.status_code == 429 or response.status_code >= 500
            raise OpenRouterError("provider_unavailable", "OpenRouter returned an unsuccessful response.", retryable=retryable)
        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            candidate = json.loads(content) if isinstance(content, str) else content
        except (ValueError, TypeError, KeyError, IndexError):
            raise OpenRouterError("invalid_model_output", "OpenRouter response did not contain structured decision JSON.", retryable=False) from None
        if agent == "decision":
            result = validate_candidate(candidate)
        else:
            result = validate_technical_interpretation(candidate)
        result["model_id"] = payload.get("model", model)
        return result

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
