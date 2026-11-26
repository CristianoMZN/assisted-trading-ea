"""Environment-backed settings for the local backend process."""

from __future__ import annotations

import os


SERVICE_VERSION = "0.1.0"
CONTRACT_VERSION = "1.1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


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
