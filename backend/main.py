"""FastAPI entry point coordinating model agents and deterministic risk checks."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.config import CONTRACT_VERSION, SERVICE_VERSION
from backend.database import get_session_factory
from backend.openrouter import OpenRouterClient, OpenRouterError
from backend.prompts import ANALYSIS_VERSIONS
from backend.macro_repository import MacroRepository
from backend.repository import AnalysisRepository
from backend.risk import RiskValidationError, validate_operational_candidate
from backend.secrets import OpenRouterCredentialStore
from scripts.backend_contract import ContractError, validate_request
from backend.technical import calculate_indicators


app = FastAPI(title="Assisted Trading Backend", version=SERVICE_VERSION)
# Uvicorn configures this logger for console output at INFO level. Reusing it
# keeps progress, warning, and error messages in the server terminal only.
logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)


def log_storage_failure(operation: str, request_id: object, exc: SQLAlchemyError) -> None:
    underlying = getattr(exc, "orig", None)
    detail = str(underlying) if underlying is not None else type(exc).__name__
    logger.error(
        "Local analysis storage failure: operation=%s request_id=%s error_type=%s detail=%s",
        operation,
        request_id if isinstance(request_id, str) else "unknown",
        type(exc).__name__,
        detail,
    )


def error_response(request_id: object, code: str, message: str, retryable: bool, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "schema_version": CONTRACT_VERSION,
            "message_type": "error",
            "request_id": request_id if isinstance(request_id, str) else None,
            "error": {"code": code, "message": message, "retryable": retryable},
        },
    )


def error_payload(request_id: object, code: str, message: str, retryable: bool) -> dict:
    return {
        "schema_version": CONTRACT_VERSION,
        "message_type": "error",
        "request_id": request_id if isinstance(request_id, str) else None,
        "error": {"code": code, "message": message, "retryable": retryable},
    }


def log_analysis_stage(
    request_id: object,
    stage: str,
    state: str,
    started_at: float | None = None,
) -> None:
    duration = ""
    if started_at is not None:
        duration = f" duration_ms={int((time.perf_counter() - started_at) * 1000)}"
    logger.info(
        "Analysis stage=%s state=%s request_id=%s%s",
        stage,
        state,
        request_id if isinstance(request_id, str) else "unknown",
        duration,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service_version": SERVICE_VERSION, "contract_version": CONTRACT_VERSION}


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _market_deadline(payload: dict) -> datetime:
    from backend.config import market_snapshot_max_age_seconds
    max_age = timedelta(seconds=market_snapshot_max_age_seconds())
    sent_at = datetime.fromisoformat(payload["sent_at"].replace("Z", "+00:00"))
    quote_at = datetime.fromisoformat(payload["current_quote"]["timestamp"].replace("Z", "+00:00"))
    return min(sent_at + max_age, quote_at + max_age)


def _analysis_result(payload: dict, sources: list[dict], *, now: datetime, status: str,
                     decision: dict | None = None, reason_code: str | None = None,
                     reason: str | None = None, deadline: datetime | None = None) -> dict:
    expiry = min(now + timedelta(minutes=1), deadline) if deadline and deadline > now else now + timedelta(minutes=1)
    return {
        "schema_version": CONTRACT_VERSION, "message_type": "analysis_response",
        "request_id": payload["request_id"], "created_at": _iso(now), "expires_at": _iso(expiry),
        "instrument": payload["instrument"], "status": status, "decision": decision,
        "reason_code": reason_code, "reason": reason, "sources": sources,
    }


@app.post("/v1/analyze")
async def analyze(payload: dict) -> JSONResponse:
    request_id = payload.get("request_id")
    if payload.get("schema_version") != CONTRACT_VERSION:
        return error_response(request_id, "unsupported_schema_version", f"Supported schema_version is {CONTRACT_VERSION}.", False, 400)
    try:
        validate_request(payload)
    except ContractError as exc:
        return error_response(request_id, "invalid_request", str(exc), False, 422)

    started = time.perf_counter()
    symbol = payload["instrument"]["logical_symbol"]
    logger.info("Analysis request started request_id=%s symbol=%s candles=%d", request_id, symbol, len(payload["candles"]))
    stage_started = time.perf_counter()
    indicators = calculate_indicators(payload)
    log_analysis_stage(request_id, "indicators", "completed", stage_started)
    market_deadline = _market_deadline(payload)
    observed = datetime.now(timezone.utc)
    technical_evidence = {
        "type": "technical", "status": "valid" if indicators["status"] == "ready" else "insufficient",
        "source": "backend-indicators", "observed_at": _iso(observed),
        "valid_until": _iso(market_deadline),
        "summary": json.dumps(indicators, ensure_ascii=False, allow_nan=False), "data": indicators,
    }
    sources = [technical_evidence]
    versions = [{"component": name, "version": version} for name, version in ANALYSIS_VERSIONS.items()]
    repository = AnalysisRepository(get_session_factory())
    macro_id = None

    def persist(response: dict) -> None:
        stage_started = time.perf_counter()
        repository.save(payload, response, versions=versions, macro_execution_id=macro_id)
        repository.prune()
        log_analysis_stage(request_id, "persistence", "completed", stage_started)

    if indicators["status"] != "ready" or observed >= market_deadline:
        reason_code = "insufficient_market_data" if indicators["status"] != "ready" else "stale_market_snapshot"
        reason = "Dados OHLC insuficientes para calcular os indicadores configurados." if indicators["status"] != "ready" else "Snapshot ou cotação venceram antes da análise."
        response = _analysis_result(payload, sources, now=observed, status="no_signal", reason_code=reason_code, reason=reason)
        try:
            persist(response)
        except SQLAlchemyError as exc:
            log_storage_failure("save_no_signal", request_id, exc)
            return error_response(request_id, "storage_unavailable", "Local analysis storage is unavailable; apply database migrations and check DATABASE_URL.", True, 503)
        return JSONResponse(status_code=200, content=response)

    try:
        stage_started = time.perf_counter()
        macro = MacroRepository(get_session_factory()).latest_usable(symbol, now=observed)
        log_analysis_stage(request_id, "macro_cache_read", "completed", stage_started)
    except SQLAlchemyError as exc:
        log_storage_failure("load_macro_cache", request_id, exc)
        return error_response(request_id, "storage_unavailable", "Local analysis storage is unavailable; apply database migrations and check DATABASE_URL.", True, 503)
    if macro is None:
        response = error_payload(request_id, "macro_context_unavailable", "Current macroeconomic context is unavailable for this instrument.", True)
        try:
            persist(response)
        except SQLAlchemyError as exc:
            log_storage_failure("save_macro_unavailable", request_id, exc)
            return error_response(request_id, "storage_unavailable", "Local analysis storage is unavailable; apply database migrations and check DATABASE_URL.", True, 503)
        return JSONResponse(status_code=503, content=response)

    macro_id = macro["id"]
    macro_deadline = datetime.fromisoformat(macro["valid_until"])
    sources.extend(macro["rss_evidence"])
    sources.append({
        "type": "macroeconomic_news", "status": macro["status"],
        "source": "macro-cache", "observed_at": macro["as_of"],
        "valid_until": macro["valid_until"], "summary": macro["summary"],
        "data": {"cache_id": macro_id, "instrument": symbol, "items": macro["items"],
                 "completed_at": macro["completed_at"], "model_id": macro["model_id"],
                 "prompt_version": macro["prompt_version"]},
    })
    versions.append({"component": "news_analysis_model", "version": macro["model_id"], "model_id": macro["model_id"]})
    versions.append({"component": "cached_news_prompt", "version": macro["prompt_version"]})

    def provider_key() -> str | None:
        try:
            with get_session_factory()() as session:
                return OpenRouterCredentialStore(session).get()
        except SQLAlchemyError as exc:
            log_storage_failure("load_openrouter_credential", request_id, exc)
            raise OpenRouterError("credential_storage_unavailable", "Local credential storage is unavailable.", retryable=True) from exc

    client = OpenRouterClient(provider_key)
    context = {"snapshot": payload, "indicators": indicators, "evidence": sources}
    provider_stage = "technical_interpretation"
    provider_started = time.perf_counter()
    try:
        technical_interpretation = await client.interpret_technical(context)
        log_analysis_stage(request_id, provider_stage, "completed", provider_started)
        versions.append({"component": "technical_interpretation_model", "version": technical_interpretation["model_id"], "model_id": technical_interpretation["model_id"]})
        provider_stage = "decision"
        provider_started = time.perf_counter()
        candidate = await client.decide({**context, "technical_interpretation": technical_interpretation})
        log_analysis_stage(request_id, provider_stage, "completed", provider_started)
        versions.append({"component": "decision_model", "version": candidate["model_id"], "model_id": candidate["model_id"]})
    except OpenRouterError as exc:
        logger.warning("Analysis stage=%s state=failed request_id=%s error_code=%s duration_ms=%d", provider_stage, request_id, exc.code, int((time.perf_counter() - provider_started) * 1000))
        response = error_payload(request_id, exc.code, exc.message, exc.retryable)
        try:
            repository.save(payload, response, versions=versions, evidence=sources, macro_execution_id=macro_id)
            repository.prune()
        except SQLAlchemyError as storage_exc:
            log_storage_failure("save_provider_error", request_id, storage_exc)
            return error_response(request_id, "storage_unavailable", "Local analysis storage is unavailable; apply database migrations and check DATABASE_URL.", True, 503)
        return JSONResponse(status_code=503, content=response)

    completed = datetime.now(timezone.utc)
    deadline = min(market_deadline, macro_deadline)
    if completed >= deadline:
        response = _analysis_result(payload, sources, now=completed, status="no_signal", reason_code="stale_market_snapshot", reason="Snapshot, cotação ou contexto macro venceram durante a análise.")
    elif candidate["action"] == "NO_SIGNAL":
        response = _analysis_result(payload, sources, now=completed, status="no_signal", reason_code="model_no_signal", reason=candidate["scenario"])
    else:
        try:
            decision = validate_operational_candidate(candidate, payload)
            response = _analysis_result(payload, sources, now=completed, status="actionable", decision=decision, deadline=deadline)
        except RiskValidationError as exc:
            response = _analysis_result(payload, sources, now=completed, status="no_signal", reason_code=exc.reason_code, reason=exc.message)
    from scripts.backend_contract import validate_response
    validate_response(response, now=completed, expected_request_id=request_id,
                      expected_instrument=payload["instrument"], tick_size=payload["symbol_properties"]["tick_size"])
    try:
        persist(response)
    except SQLAlchemyError as exc:
        log_storage_failure("save_analysis", request_id, exc)
        return error_response(request_id, "storage_unavailable", "Local analysis storage is unavailable; apply database migrations and check DATABASE_URL.", True, 503)
    logger.info("Analysis request completed request_id=%s status=%s duration_ms=%d", request_id, response["status"], int((time.perf_counter() - started) * 1000))
    return JSONResponse(status_code=200, content=response)
