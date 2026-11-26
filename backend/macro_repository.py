"""Atomic, append-only persistence for instrument-specific macro research."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import macro_validity_minutes
from backend.models import MacroExecution
from backend.openrouter import NEWS_ANALYSIS_SCHEMA, OpenRouterError, validate_news_analysis


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Macro timestamps must have a timezone")
    return value.astimezone(timezone.utc)


def _stored_utc(value: datetime) -> datetime:
    # SQLite stores DateTime without its offset even when timezone=True.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _validated_content(instrument: str, state: str, summary: object, items: object) -> dict:
    if not isinstance(items, list):
        raise ValueError("Macro items must be a list")
    fields = set(NEWS_ANALYSIS_SCHEMA["properties"]["items"]["items"]["properties"])
    if any(not isinstance(item, dict) or item.get("instrument", instrument) != instrument for item in items):
        raise ValueError("Macro items do not match the instrument")
    stripped = [{key: item[key] for key in fields if key in item} for item in items]
    try:
        return validate_news_analysis({"status": state, "summary": summary, "items": stripped}, instrument)
    except OpenRouterError as exc:
        raise ValueError(exc.message) from exc


class MacroRepository:
    def __init__(self, session_factory: Callable[[], Session], validity_minutes: int | None = None):
        self.session_factory = session_factory
        self.validity_minutes = macro_validity_minutes() if validity_minutes is None else validity_minutes
        if not 1 <= self.validity_minutes <= 1440:
            raise ValueError("validity_minutes must be between 1 and 1440")

    def save_success(
        self,
        instrument: str,
        result: dict,
        *,
        rss_evidence: list[dict],
        as_of: datetime,
        completed_at: datetime,
        prompt_version: str,
    ) -> int:
        if instrument not in ("WIN", "WDO"):
            raise ValueError("instrument must be WIN or WDO")
        state = result.get("status")
        items = result.get("items")
        summary = result.get("summary")
        model_id = result.get("model_id")
        if state not in ("available", "no_relevant_news") or not isinstance(model_id, str) or not model_id:
            raise ValueError("A complete, usable macro result is required")
        if not isinstance(rss_evidence, list) or not prompt_version:
            raise ValueError("RSS evidence and prompt version are required")
        content = _validated_content(instrument, state, summary, items)
        as_of = _utc(as_of)
        completed_at = _utc(completed_at)
        valid_until = completed_at + timedelta(minutes=self.validity_minutes)
        with self.session_factory() as session:
            record = MacroExecution(
                logical_symbol=instrument, state=state, summary=content["summary"], items=content["items"],
                rss_evidence=rss_evidence, as_of=as_of, completed_at=completed_at,
                valid_until=valid_until, model_id=model_id, prompt_version=prompt_version,
            )
            session.add(record)
            session.commit()
            return record.id

    def save_failure(
        self, instrument: str, *, as_of: datetime, completed_at: datetime,
        error_code: str, error_detail: str | None = None,
        rss_evidence: list[dict] | None = None,
    ) -> int:
        if instrument not in ("WIN", "WDO"):
            raise ValueError("instrument must be WIN or WDO")
        # Callers provide only a safe error code/diagnostic, never raw provider output.
        with self.session_factory() as session:
            record = MacroExecution(
                logical_symbol=instrument, state="unavailable", as_of=_utc(as_of),
                completed_at=_utc(completed_at), error_code=error_code,
                error_detail=error_detail, rss_evidence=rss_evidence,
            )
            session.add(record)
            session.commit()
            return record.id

    def latest_usable(self, instrument: str, *, now: datetime | None = None) -> dict | None:
        if instrument not in ("WIN", "WDO"):
            raise ValueError("instrument must be WIN or WDO")
        current = _utc(now or datetime.now(timezone.utc))
        with self.session_factory() as session:
            # A later failure never masks an earlier success within its original validity.
            records = session.scalars(
                select(MacroExecution).where(
                    MacroExecution.logical_symbol == instrument,
                    MacroExecution.state.in_(("available", "no_relevant_news")),
                    MacroExecution.valid_until > current,
                    MacroExecution.completed_at <= current,
                ).order_by(MacroExecution.completed_at.desc(), MacroExecution.id.desc())
            )
            for record in records:
                if not record.model_id or not record.prompt_version:
                    continue
                try:
                    content = _validated_content(instrument, record.state, record.summary, record.items)
                except ValueError:
                    continue
                return {
                    "id": record.id, "instrument": record.logical_symbol, "status": record.state,
                    "summary": content["summary"], "items": content["items"],
                    "rss_evidence": record.rss_evidence or [],
                    "as_of": _stored_utc(record.as_of).isoformat(),
                    "completed_at": _stored_utc(record.completed_at).isoformat(),
                    "valid_until": _stored_utc(record.valid_until).isoformat(),
                    "model_id": record.model_id, "prompt_version": record.prompt_version,
                }
        return None
