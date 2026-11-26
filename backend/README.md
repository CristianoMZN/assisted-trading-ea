# Local FastAPI backend

## Start

From the repository root, create an isolated Python environment and install the service dependencies. Copy `.env.example` to `.env` and fill in the model and OpenRouter key once; the service and Alembic load this file automatically:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
# Edit .env and set the agent models and OPENROUTER_API_KEY
.venv/bin/alembic upgrade head
.venv/bin/python -m backend refresh-macro --instrument WDO
.venv/bin/python -m backend refresh-macro --instrument WIN
.venv/bin/python -m backend
```

Run `refresh-macro` again before its context expires. It uses the same `DATABASE_URL`, OpenRouter credential, and news-model configuration as the API, and does not start Uvicorn. Successful output includes the instrument, state, cache ID, and `valid_until`; a failure exits nonzero with a safe error code. A failed run leaves the prior successful result available only until its original expiry. Set `MACRO_VALIDITY_MINUTES` to 1–1440 (default 15); validity starts when research completes. Apply `.venv/bin/alembic upgrade head` before either the command or server; migration `0004_macro_executions` adds the cache without removing previous analyses.

Keep `.env` local; it is excluded from Git. Environment variables exported by the shell take precedence over values in `.env`. For the OpenRouter key, `OPENROUTER_API_KEY` from the environment or `.env` takes precedence over a credential previously saved in the OS vault/database. The key is sent only by the backend to OpenRouter; never put it in EA inputs or request payloads.

The service version is `0.1.0` and the contract version is `1.1`. It binds to `127.0.0.1:9000` by default. Override the bind address with `BACKEND_HOST`, the port with `BACKEND_PORT`, and the Uvicorn log level with `BACKEND_LOG_LEVEL` (`critical`, `error`, `warning`, `info`, `debug`, or `trace`). `BACKEND_PORT` must be an integer from 1 through 65535.

Set environment variables in the shell that launches the service, for example:

```bash
BACKEND_HOST=127.0.0.1 BACKEND_PORT=8123 BACKEND_LOG_LEVEL=debug .venv/bin/python -m backend
```

Check service health at `GET /health`. Submit contract version 1.1 snapshots to `POST /v1/analyze` as JSON. The endpoint rejects unsupported versions with HTTP 400 (`unsupported_schema_version`) and malformed or invalid snapshots with HTTP 422 (`invalid_request`).

## Current analysis status

`GET /health` reports service and contract versions. `POST /v1/analyze` accepts schema 1.1. With insufficient candles it returns `no_signal` (`insufficient_market_data`). With adequate data it calculates SMA5/SMA20/RSI14/ATR14, reads valid macro context for the same instrument, calls the technical interpretation agent, then calls the decision agent. It does not query RSS or the web. Missing or expired macro context returns HTTP 503 `macro_context_unavailable`. A stale snapshot or quote returns `no_signal` with `stale_market_snapshot`; the clock is checked again after both model calls. An actionable response is returned only after deterministic price, tick, stop, RR, loss, cost, and positive net return checks. Other errors use the contract envelope with `schema_version`, `message_type: error`, `request_id`, and an `error` object containing `code`, `message`, and `retryable`.

Each online analysis stores the macro cache ID, the original macro/RSS evidence and model/prompt versions, plus technical and decision model versions. Server logs include stage durations for indicators, cache read, technical interpretation, decision, and persistence. They omit provider credentials and raw model output.

The decision prompt is versioned as `market-decision-v2`. Its `scenario` explanation must be a non-empty string of at most 240 characters. If OpenRouter returns a malformed decision, the backend responds with `invalid_model_output` and a safe validation reason; this is a local rejection of the model's content, not an OpenRouter HTTP error. The raw model response is not persisted.

An OpenRouter key can alternatively be saved encrypted in the local database, with its encryption key held in the operating system credential vault. The environment or `.env` value takes precedence. Do not put provider credentials in EA inputs or request payloads.

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

Run this under the same OS account and with the same `DATABASE_URL` as the service. If the OS vault is unavailable, configure the key in `.env` instead.

News feeds are configured with a comma-separated `NEWS_RSS_URLS` list of up to five HTTPS RSS or Atom URLs. The refresh command collects them with a four-second timeout and a two-megabyte response limit. It stores `available`, `empty`, `unavailable`, or `not_configured` per source with collection timestamps. A failed feed remains distinct from a completed macro search with `no_relevant_news`.

Set `OPENROUTER_MODEL_NEWS_ANALYSIS`, `OPENROUTER_MODEL_TECHNICAL_INTERPRETATION`, and `OPENROUTER_MODEL_DECISION` to Chat Completions models that support strict JSON-schema output; the news model must also support server-side web search and fetch tools. They may use the same model or different models. The Decider family uses OpenRouter's separate Decisions API and cannot serve as `OPENROUTER_MODEL_DECISION` in this backend. If the news model is unset, it falls back to the technical-interpretation model, then the legacy `OPENROUTER_MODEL`. The refresh command uses versioned prompts `news_analysis_wdo_v7.txt` and `news_analysis_win_v7.txt`. Its hosted web tools allow up to three searches (eight total results) and four page fetches (3,500 content tokens each), restricted to the official and financial domains in `backend/openrouter.py`. It returns at most four selected items so each can be opened. The prompts exclude static contract pages and historical facts without a currently relevant macroeconomic channel. Each item must contain the exact consulted HTTPS URL, fact, and effect relative to the requested instrument. The v7 prompts require short, non-empty `transmission_channel` text backed by the consulted source; unsupported items must be discarded. `invalid_model_output` reports field names/counts or safe validation errors without raw content. The command retries this error once with safe format feedback, then records a failed execution; it never fabricates missing facts or URLs. A completed search with no relevant items is usable as `no_relevant_news`; web failure is `unavailable` and cannot feed a decision. The web search engine and model token usage may incur OpenRouter charges. `OPENROUTER_TIMEOUT_SECONDS` sets the shared request timeout (0.5–120 seconds; default 60). The old `OPENROUTER_MODEL` value remains a fallback for existing installations when an agent-specific model is blank.

## Environment settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `BACKEND_HOST` | `127.0.0.1` | Bind address. |
| `BACKEND_PORT` | `9000` | Bind port (1–65535). |
| `BACKEND_LOG_LEVEL` | `info` | Uvicorn log level. |
| `DATABASE_URL` | `sqlite:///./data/assisted_trading.db` | Local SQLAlchemy database. |
| `ANALYSIS_RETENTION_DAYS` | `30` | Retention period (1–3650 days). |
| `MACRO_VALIDITY_MINUTES` | `15` | Macro cache validity after research completion (1–1440 minutes). |
| `MARKET_SNAPSHOT_MAX_AGE_SECONDS` | `30` | Maximum age of `sent_at` and quote at arrival and completion (1–300 seconds). |
| `NEWS_RSS_URLS` | unset | Comma-separated list of up to five HTTPS RSS/Atom feeds; each has a 4-second timeout and 2 MB response cap. |
| `OPENROUTER_MODEL_NEWS_ANALYSIS` | unset | Model for macroeconomic news research using OpenRouter web search/fetch. |
| `OPENROUTER_MODEL_TECHNICAL_INTERPRETATION` | unset | Model for the technical interpretation agent. |
| `OPENROUTER_MODEL_DECISION` | unset | Model for the decision agent. |
| `OPENROUTER_MODEL` | unset | Deprecated compatibility fallback for all three agents. |
| `OPENROUTER_TIMEOUT_SECONDS` | `60` | Provider timeout (0.5–120 seconds). |
| `OPENROUTER_API_KEY` | unset | OpenRouter credential; environment/`.env` value takes precedence over a saved vault credential. |

The default database URL is `sqlite:///./data/assisted_trading.db`. Relative SQLite paths resolve from the repository root, independent of the service's working directory. Override it with `DATABASE_URL`, then apply schema updates with `.venv/bin/alembic upgrade head`. For SQLite the parent directory is created automatically. Database migrations are versioned under `backend/migrations/`. `ANALYSIS_RETENTION_DAYS` sets record retention (1–3650 days; default 30).
