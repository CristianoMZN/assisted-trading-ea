"""FastAPI entry point. Analysis stays fail-closed until its pipeline is configured."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.config import CONTRACT_VERSION, SERVICE_VERSION
from scripts.backend_contract import ContractError, validate_request


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

    # The analysis pipeline is added in subsequent implementation tasks. A
    # successful parse must never be represented as an actionable decision.
    return error_response(
        request_id,
        "analysis_unavailable",
        "Analysis service is not configured yet.",
        True,
        503,
    )
