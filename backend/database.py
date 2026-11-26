"""SQLAlchemy engine and declarative base for local persistence."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker


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
    engine = create_engine(resolved_url, connect_args=connect_args, pool_pre_ping=True)
    if resolved_url.startswith("sqlite:"):
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


@lru_cache(maxsize=8)
def _session_factory_for_url(url: str):
    return sessionmaker(bind=make_engine(url), expire_on_commit=False)


def get_session_factory():
    return _session_factory_for_url(database_url())
