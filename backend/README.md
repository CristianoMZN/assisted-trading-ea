# Local FastAPI backend

## Start

From the repository root, create an isolated Python environment and install the service dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m backend
```

The service binds to `127.0.0.1:8000` by default. Override the bind address with `BACKEND_HOST`, the port with `BACKEND_PORT`, and the Uvicorn log level with `BACKEND_LOG_LEVEL` (`critical`, `error`, `warning`, `info`, `debug`, or `trace`). `BACKEND_PORT` must be an integer from 1 through 65535.

Set environment variables in the shell that launches the service, for example:

```bash
BACKEND_HOST=127.0.0.1 BACKEND_PORT=8123 BACKEND_LOG_LEVEL=debug .venv/bin/python -m backend
```

Check service health at `GET /health`. Submit contract version 1.1 snapshots to `POST /v1/analyze` as JSON. The endpoint rejects unsupported versions with HTTP 400 (`unsupported_schema_version`) and malformed or invalid snapshots with HTTP 422 (`invalid_request`).

## Current analysis status

Until the analysis pipeline is configured, a valid snapshot receives HTTP 503 with `analysis_unavailable`. This is intentional fail-closed behavior: the service does not create a buy or sell decision when analysis is unavailable. Other errors use the contract envelope with `schema_version`, `message_type: error`, `request_id`, and an `error` object containing `code`, `message`, and `retryable`.

The OpenRouter credential store encrypts a saved key with a separate key held in the operating system credential vault. When that vault is unavailable, the explicit fallback is the `OPENROUTER_API_KEY` environment variable; this fallback is read at runtime and is never written to SQLite. Do not put provider credentials in EA inputs or request payloads. OpenRouter calls are not active until the analysis integration is implemented.

The default database URL is `sqlite:///./data/assisted_trading.db`. Override it with `DATABASE_URL`, then apply schema updates from the repository root with `.venv/bin/alembic upgrade head`. For SQLite the parent directory is created automatically. Database migrations are versioned under `backend/migrations/`.
