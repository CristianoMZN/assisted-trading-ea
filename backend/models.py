"""Persistent analysis, evidence, and version records."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class AnalysisRecord(Base):
    __tablename__ = "analyses"
    __table_args__ = (Index("ix_analyses_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    logical_symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    broker_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(96), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence: Mapped[list["AnalysisEvidence"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    versions: Mapped[list["AnalysisVersion"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")


class AnalysisEvidence(Base):
    __tablename__ = "analysis_evidence"
    __table_args__ = (Index("ix_analysis_evidence_analysis_id", "analysis_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str | None] = mapped_column(String(256), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    analysis: Mapped[AnalysisRecord] = relationship(back_populates="evidence")


class AnalysisVersion(Base):
    __tablename__ = "analysis_versions"
    __table_args__ = (
        UniqueConstraint("analysis_id", "component", name="uq_analysis_versions_component"),
        Index("ix_analysis_versions_analysis_id", "analysis_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    component: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(128), nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    configuration: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analysis: Mapped[AnalysisRecord] = relationship(back_populates="versions")


class ProviderCredential(Base):
    __tablename__ = "provider_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    encrypted_secret: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
