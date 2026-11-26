"""Environment-backed settings for the local backend process."""

from __future__ import annotations

import os


SERVICE_VERSION = "0.1.0"
CONTRACT_VERSION = "1.1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9000


def server_host() -> str:
    return os.getenv("BACKEND_HOST", DEFAULT_HOST)


def server_port() -> int:
    try:
        port = int(os.getenv("BACKEND_PORT", str(DEFAULT_PORT)))
    except ValueError as exc:
        raise ValueError("BACKEND_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("BACKEND_PORT must be between 1 and 65535")
    return port


def log_level() -> str:
    return os.getenv("BACKEND_LOG_LEVEL", "info").lower()


def analysis_retention_days() -> int:
    try:
        days = int(os.getenv("ANALYSIS_RETENTION_DAYS", "30"))
    except ValueError as exc:
        raise ValueError("ANALYSIS_RETENTION_DAYS must be an integer") from exc
    if not 1 <= days <= 3650:
        raise ValueError("ANALYSIS_RETENTION_DAYS must be between 1 and 3650")
    return days


def macro_validity_minutes() -> int:
    try:
        minutes = int(os.getenv("MACRO_VALIDITY_MINUTES", "15"))
    except ValueError as exc:
        raise ValueError("MACRO_VALIDITY_MINUTES must be an integer") from exc
    if not 1 <= minutes <= 1440:
        raise ValueError("MACRO_VALIDITY_MINUTES must be between 1 and 1440")
    return minutes


def market_snapshot_max_age_seconds() -> int:
    try:
        seconds = int(os.getenv("MARKET_SNAPSHOT_MAX_AGE_SECONDS", "30"))
    except ValueError as exc:
        raise ValueError("MARKET_SNAPSHOT_MAX_AGE_SECONDS must be an integer") from exc
    if not 1 <= seconds <= 300:
        raise ValueError("MARKET_SNAPSHOT_MAX_AGE_SECONDS must be between 1 and 300")
    return seconds


def openrouter_model(agent: str = "decision") -> str:
    """Return the configured OpenRouter model for an analysis agent.

    OPENROUTER_MODEL remains a compatibility fallback for existing installs.
    """
    setting_by_agent = {
        "news_analysis": "OPENROUTER_MODEL_NEWS_ANALYSIS",
        "technical_interpretation": "OPENROUTER_MODEL_TECHNICAL_INTERPRETATION",
        "decision": "OPENROUTER_MODEL_DECISION",
    }
    try:
        setting_name = setting_by_agent[agent]
    except KeyError as exc:
        raise ValueError(f"Unknown OpenRouter agent: {agent}") from exc
    configured = os.getenv(setting_name, "").strip()
    if agent == "news_analysis" and not configured:
        configured = os.getenv("OPENROUTER_MODEL_TECHNICAL_INTERPRETATION", "").strip()
    return configured or os.getenv("OPENROUTER_MODEL", "").strip()


def openrouter_timeout_seconds() -> float:
    try:
        timeout = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "60"))
    except ValueError as exc:
        raise ValueError("OPENROUTER_TIMEOUT_SECONDS must be a number") from exc
    if not 0.5 <= timeout <= 120:
        raise ValueError("OPENROUTER_TIMEOUT_SECONDS must be between 0.5 and 120")
    return timeout
