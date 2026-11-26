"""FastAPI entry point. Analysis stays fail-closed until its pipeline is configured."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.config import CONTRACT_VERSION, SERVICE_VERSION
from backend.database import get_session_factory
from backend.news import RSSNewsAdapter
from backend.openrouter import OpenRouterClient, OpenRouterError
from backend.prompts import ANALYSIS_VERSIONS
from backend.repository import AnalysisRepository
from backend.risk import RiskValidationError, validate_operational_candidate
from backend.secrets import OpenRouterCredentialStore
from scripts.backend_contract import ContractError, validate_request
from backend.technical import calculate_indicators


app = FastAPI(title="Assisted Trading Backend", version=SERVICE_VERSION)


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service_version": SERVICE_VERSION, "contract_version": CONTRACT_VERSION}


@app.post("/v1/analyze")
async def analyze(payload: dict) -> JSONResponse:
    request_id = payload.get("request_id")
    if payload.get("schema_version") != CONTRACT_VERSION:
        return error_response(
            request_id,
            "unsupported_schema_version",
            f"Supported schema_version is {CONTRACT_VERSION}.",
            False,
            400,
        )
    try:
        validate_request(payload)
    except ContractError as exc:
        return error_response(request_id, "invalid_request", str(exc), False, 422)

    created = datetime.now(timezone.utc)
    expires = created + timedelta(minutes=1)
    observed_at = created.isoformat().replace("+00:00", "Z")
    expires_at = expires.isoformat().replace("+00:00", "Z")
    indicators = calculate_indicators(payload)
    technical_evidence = {
        "type": "technical",
        "status": "valid" if indicators["status"] == "ready" else "insufficient",
        "source": "backend-indicators",
        "observed_at": observed_at,
        "valid_until": expires_at,
        "summary": json.dumps(indicators, ensure_ascii=False, allow_nan=False),
        "data": indicators,
    }
    news_results = RSSNewsAdapter().collect(payload["instrument"]["logical_symbol"])
    news_evidence = [result.as_evidence() for result in news_results]
    sources = [technical_evidence, *news_evidence, {
        "type": "prediction_market",
        "status": "not_relevant",
        "source": "not_configured",
        "observed_at": observed_at,
        "valid_until": expires_at,
        "summary": "Nenhuma integração de mercado de previsão está configurada.",
    }]
    versions = [
        {"component": name, "version": version}
        for name, version in ANALYSIS_VERSIONS.items()
        if name in ("technical_indicators", "decision")
    ]

    if indicators["status"] != "ready":
        result = {
            "schema_version": CONTRACT_VERSION,
            "message_type": "analysis_response",
            "request_id": request_id,
            "created_at": observed_at,
            "expires_at": expires_at,
            "instrument": payload["instrument"],
            "status": "no_signal",
            "decision": None,
            "reason_code": "insufficient_market_data",
            "reason": "Dados OHLC insuficientes para calcular os indicadores configurados.",
            "sources": sources,
        }
        try:
            repository = AnalysisRepository(get_session_factory())
            repository.save(payload, result, versions=versions)
            repository.prune()
        except SQLAlchemyError:
            return error_response(request_id, "storage_unavailable", "Local analysis storage is unavailable; apply database migrations and check DATABASE_URL.", True, 503)
        return JSONResponse(status_code=200, content=result)

    def provider_key() -> str | None:
        try:
            with get_session_factory()() as session:
                return OpenRouterCredentialStore(session).get()
        except SQLAlchemyError as exc:
            raise OpenRouterError(
                "credential_storage_unavailable",
                "Local credential storage is unavailable; apply database migrations and check DATABASE_URL.",
                retryable=True,
            ) from exc

    client = OpenRouterClient(provider_key)
    context = {"snapshot": payload, "indicators": indicators, "evidence": sources}
    repository = AnalysisRepository(get_session_factory())
    try:
        candidate = await client.decide(context)
    except OpenRouterError as exc:
        fallback = error_payload(request_id, exc.code, exc.message, exc.retryable)
        try:
            repository.save(payload, fallback, versions=versions, evidence=sources)
            repository.prune()
        except SQLAlchemyError:
            return error_response(request_id, "storage_unavailable", "Local analysis storage is unavailable; apply database migrations and check DATABASE_URL.", True, 503)
        return JSONResponse(status_code=503, content=fallback)
    try:
        if candidate["action"] == "NO_SIGNAL":
            result = {
                "schema_version": CONTRACT_VERSION,
                "message_type": "analysis_response",
                "request_id": request_id,
                "created_at": observed_at,
                "expires_at": expires_at,
                "instrument": payload["instrument"],
                "status": "no_signal",
                "decision": None,
                "reason_code": "model_no_signal",
                "reason": candidate["scenario"],
                "sources": sources,
            }
        else:
            try:
                decision = validate_operational_candidate(candidate, payload)
                result = {
                    "schema_version": CONTRACT_VERSION,
                    "message_type": "analysis_response",
                    "request_id": request_id,
                    "created_at": observed_at,
                    "expires_at": expires_at,
                    "instrument": payload["instrument"],
                    "status": "actionable",
                    "decision": decision,
                    "reason_code": None,
                    "reason": None,
                    "sources": sources,
                }
            except RiskValidationError as exc:
                result = {
                    "schema_version": CONTRACT_VERSION,
                    "message_type": "analysis_response",
                    "request_id": request_id,
                    "created_at": observed_at,
                    "expires_at": expires_at,
                    "instrument": payload["instrument"],
                    "status": "no_signal",
                    "decision": None,
                    "reason_code": exc.reason_code,
                    "reason": exc.message,
                    "sources": sources,
                }
        from scripts.backend_contract import validate_response
        validate_response(
            result,
            now=created,
            expected_request_id=request_id,
            expected_instrument=payload["instrument"],
            tick_size=payload["symbol_properties"]["tick_size"],
        )
        repository.save(
            payload,
            result,
            versions=versions + [{"component": "model", "version": candidate["model_id"], "model_id": candidate["model_id"]}],
        )
        repository.prune()
    except SQLAlchemyError:
        return error_response(request_id, "storage_unavailable", "Local analysis storage is unavailable; apply database migrations and check DATABASE_URL.", True, 503)
    return JSONResponse(status_code=200, content=result)
