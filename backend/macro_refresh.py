"""Run macro research outside the HTTP request path."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError

from backend.database import get_session_factory
from backend.macro_repository import MacroRepository
from backend.news import RSSNewsAdapter
from backend.openrouter import OpenRouterClient, OpenRouterError
from backend.prompts import PROMPT_VERSIONS
from backend.secrets import OpenRouterCredentialStore


logger = logging.getLogger(__name__)


def _stamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _provider_key() -> str | None:
    with get_session_factory()() as session:
        return OpenRouterCredentialStore(session).get()


async def refresh_macro(instrument: str) -> tuple[bool, str]:
    if instrument not in ("WIN", "WDO"):
        raise ValueError("instrument must be WIN or WDO")
    as_of = datetime.now(timezone.utc)
    rss_evidence: list[dict] = []
    try:
        rss_evidence = [source.as_evidence() for source in RSSNewsAdapter().collect(instrument)]
        client = OpenRouterClient(_provider_key)
        context = {
            "instrument": {"logical_symbol": instrument},
            "as_of": _stamp(as_of),
            "timezone": "America/Sao_Paulo",
            "existing_news_evidence": rss_evidence,
        }
        for attempt in range(2):
            try:
                result = await client.analyze_news(context)
                break
            except OpenRouterError as exc:
                if exc.code != "invalid_model_output" or attempt:
                    raise
                logger.warning("Macro research invalid output; retrying once instrument=%s diagnostic=%s", instrument, exc.message)
                context = {**context, "format_feedback": exc.message}
        if result["status"] == "unavailable":
            tool_use = result.get("tool_use")
            counts = " ".join(f"{name}={tool_use[name]}" for name in ("web_search_requests", "web_fetch_requests") if isinstance(tool_use, dict) and name in tool_use)
            detail = "Web research could not be completed."
            if counts:
                detail += f" {counts}"
            raise OpenRouterError("research_unavailable", detail, retryable=True)
        completed = datetime.now(timezone.utc)
        repository = MacroRepository(get_session_factory())
        record_id = repository.save_success(
            instrument, result, rss_evidence=rss_evidence, as_of=as_of,
            completed_at=completed, prompt_version=PROMPT_VERSIONS["news_analysis"],
        )
        valid_until = _stamp(completed + timedelta(minutes=repository.validity_minutes))
        return True, f"instrument={instrument} state={result['status']} cache_id={record_id} valid_until={valid_until}"
    except OpenRouterError as exc:
        try:
            MacroRepository(get_session_factory()).save_failure(
                instrument, as_of=as_of, completed_at=datetime.now(timezone.utc),
                error_code=exc.code, error_detail=exc.message, rss_evidence=rss_evidence,
            )
        except SQLAlchemyError:
            return False, f"instrument={instrument} state=unavailable error=storage_unavailable"
        return False, f"instrument={instrument} state=unavailable error={exc.code} diagnostic={exc.message}"
    except SQLAlchemyError:
        return False, f"instrument={instrument} state=unavailable error=storage_unavailable"


def run_refresh_macro(instrument: str) -> int:
    success, message = asyncio.run(refresh_macro(instrument))
    print(message)
    return 0 if success else 1
