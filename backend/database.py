"""SQLAlchemy engine and declarative base for local persistence."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase


DEFAULT_DATABASE_URL = "sqlite:///./data/assisted_trading.db"


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def make_engine(url: str | None = None) -> Engine:
    resolved_url = url or database_url()
    connect_args = {}
    if resolved_url.startswith("sqlite:"):
        connect_args["check_same_thread"] = False
        if resolved_url.startswith("sqlite:///./"):
            Path(resolved_url.removeprefix("sqlite:///./")).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(resolved_url, connect_args=connect_args, pool_pre_ping=True)
