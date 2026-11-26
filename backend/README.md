# Local FastAPI backend

## Start

From the repository root, create an isolated Python environment and install the service dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m backend
```

The service version is `0.1.0` and the contract version is `1.1`. It binds to `127.0.0.1:8000` by default. Override the bind address with `BACKEND_HOST`, the port with `BACKEND_PORT`, and the Uvicorn log level with `BACKEND_LOG_LEVEL` (`critical`, `error`, `warning`, `info`, `debug`, or `trace`). `BACKEND_PORT` must be an integer from 1 through 65535.

Set environment variables in the shell that launches the service, for example:

```bash
BACKEND_HOST=127.0.0.1 BACKEND_PORT=8123 BACKEND_LOG_LEVEL=debug .venv/bin/python -m backend
```

Check service health at `GET /health`. Submit contract version 1.1 snapshots to `POST /v1/analyze` as JSON. The endpoint rejects unsupported versions with HTTP 400 (`unsupported_schema_version`) and malformed or invalid snapshots with HTTP 422 (`invalid_request`).

## Current analysis status

`GET /health` reports service and contract versions. `POST /v1/analyze` accepts schema 1.1. With insufficient candles it returns `no_signal` (`insufficient_market_data`). With adequate data it calculates SMA5/SMA20/RSI14/ATR14, attaches configured news evidence, requests a structured candidate from OpenRouter, and only returns an actionable response after deterministic price, tick, stop, RR, loss, cost, and positive net return checks. Missing model/key, timeout, invalid provider output, persistence errors, and other operational failures fail closed. Other errors use the contract envelope with `schema_version`, `message_type: error`, `request_id`, and an `error` object containing `code`, `message`, and `retryable`.

The OpenRouter credential store encrypts a saved key with a separate key held in the operating system credential vault. When that vault is unavailable, the explicit fallback is the `OPENROUTER_API_KEY` environment variable; this fallback is read at runtime and is never written to SQLite. Do not put provider credentials in EA inputs or request payloads.

To save a key in the OS vault, run this from the repository root after migrations. `getpass` prompts without echoing the key:

```bash
.venv/bin/python - <<'PY'
from getpass import getpass
from backend.database import get_session_factory
from backend.secrets import OpenRouterCredentialStore

with get_session_factory()() as session:
    OpenRouterCredentialStore(session).store(getpass("OpenRouter API key: "))
print("Credential saved encrypted in the local database; encryption key stored in the OS vault.")
PY
```

Run this under the same OS account and with the same `DATABASE_URL` as the service. If the OS vault is unavailable, use the environment fallback instead.

News feeds are configured with a comma-separated `NEWS_RSS_URLS` list of up to five HTTPS RSS or Atom URLs. Requests have a four-second timeout and a two-megabyte response limit. The adapter returns `available`, `empty`, `unavailable`, or `not_configured` per source and keeps source and collection timestamps with each result.

Set `OPENROUTER_MODEL` to a model identifier accepted by OpenRouter. `OPENROUTER_TIMEOUT_SECONDS` sets the request timeout (0.5–120 seconds; default 20). The client requests JSON Schema output and validates the candidate locally before deterministic risk validation.

## Environment settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `BACKEND_HOST` | `127.0.0.1` | Bind address. |
| `BACKEND_PORT` | `8000` | Bind port (1–65535). |
| `BACKEND_LOG_LEVEL` | `info` | Uvicorn log level. |
| `DATABASE_URL` | `sqlite:///./data/assisted_trading.db` | Local SQLAlchemy database. |
| `ANALYSIS_RETENTION_DAYS` | `30` | Retention period (1–3650 days). |
| `NEWS_RSS_URLS` | unset | Comma-separated list of up to five HTTPS RSS/Atom feeds; each has a 4-second timeout and 2 MB response cap. |
| `OPENROUTER_MODEL` | unset | OpenRouter model identifier; required for model decisions. |
| `OPENROUTER_TIMEOUT_SECONDS` | `20` | Provider timeout (0.5–120 seconds). |
| `OPENROUTER_API_KEY` | unset | Runtime-only fallback if the OS vault key is unavailable. |

The default database URL is `sqlite:///./data/assisted_trading.db`. Override it with `DATABASE_URL`, then apply schema updates from the repository root with `.venv/bin/alembic upgrade head`. For SQLite the parent directory is created automatically. Database migrations are versioned under `backend/migrations/`. `ANALYSIS_RETENTION_DAYS` sets record retention (1–3650 days; default 30).
