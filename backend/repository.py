"""Persistence operations for analysis results and retention."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.config import analysis_retention_days
from backend.models import AnalysisEvidence, AnalysisRecord, AnalysisVersion


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


class AnalysisRepository:
    def __init__(self, session_factory: Callable[[], Session], retention_days: int | None = None):
        self.session_factory = session_factory
        self.retention_days = retention_days if retention_days is not None else analysis_retention_days()
        if not 1 <= self.retention_days <= 3650:
            raise ValueError("retention_days must be between 1 and 3650")

    def save(
        self,
        request: dict,
        response: dict,
        *,
        versions: list[dict] | None = None,
        evidence: list[dict] | None = None,
    ) -> None:
        request_id = request["request_id"]
        instrument = request["instrument"]
        status = response.get("status")
        decision = response.get("decision")
        error = response.get("error") if isinstance(response.get("error"), dict) else {}
        reason_code = response.get("reason_code") or error.get("code")
        reason = response.get("reason") or error.get("message")
        created_at = _parse_timestamp(response.get("created_at")) or datetime.now(timezone.utc)
        expires_at = _parse_timestamp(response.get("expires_at"))
        state = status if status in ("actionable", "no_signal") else "failed"

        with self.session_factory() as session:
            record = AnalysisRecord(
                request_id=request_id,
                logical_symbol=instrument["logical_symbol"],
                broker_symbol=instrument["broker_symbol"],
                state=state,
                request_snapshot=request,
                decision=decision,
                reason_code=reason_code,
                reason=reason,
                created_at=created_at,
                expires_at=expires_at,
            )
            for item in evidence if evidence is not None else response.get("sources", []):
                record.evidence.append(
                    AnalysisEvidence(
                        evidence_type=item["type"],
                        status=item["status"],
                        source=item.get("source"),
                        observed_at=_parse_timestamp(item.get("observed_at")),
                        valid_until=_parse_timestamp(item.get("valid_until")),
                        summary=item.get("summary", ""),
                        data=item.get("data"),
                    )
                )
            for item in versions or response.get("versions", []):
                record.versions.append(
                    AnalysisVersion(
                        component=item["component"],
                        version=item["version"],
                        model_id=item.get("model_id"),
                        configuration=item.get("configuration"),
                    )
                )
            session.add(record)
            session.commit()

    def get(self, request_id: str) -> dict | None:
        with self.session_factory() as session:
            record = session.scalar(
                select(AnalysisRecord).where(AnalysisRecord.request_id == request_id)
            )
            if record is None:
                return None
            return {
                "request_id": record.request_id,
                "instrument": {"logical_symbol": record.logical_symbol, "broker_symbol": record.broker_symbol},
                "state": record.state,
                "request_snapshot": record.request_snapshot,
                "decision": record.decision,
                "reason_code": record.reason_code,
                "reason": record.reason,
                "created_at": record.created_at.isoformat(),
                "expires_at": record.expires_at.isoformat() if record.expires_at else None,
                "evidence": [
                    {
                        "type": evidence.evidence_type,
                        "status": evidence.status,
                        "source": evidence.source,
                        "observed_at": evidence.observed_at.isoformat() if evidence.observed_at else None,
                        "valid_until": evidence.valid_until.isoformat() if evidence.valid_until else None,
                        "summary": evidence.summary,
                        "data": evidence.data,
                    }
                    for evidence in record.evidence
                ],
                "versions": [
                    {
                        "component": version.component,
                        "version": version.version,
                        "model_id": version.model_id,
                        "configuration": version.configuration,
                    }
                    for version in record.versions
                ],
            }

    def prune(self, *, now: datetime | None = None) -> int:
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=self.retention_days)
        with self.session_factory() as session:
            result = session.execute(delete(AnalysisRecord).where(AnalysisRecord.created_at < cutoff))
            deleted = int(result.rowcount or 0)
            session.commit()
            return deleted
