"""SQLAlchemy engine and declarative base for local persistence."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker


DEFAULT_DATABASE_URL = "sqlite:///./data/assisted_trading.db"


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    configured_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    parsed_url = make_url(configured_url)
    if parsed_url.get_backend_name() != "sqlite":
        return configured_url

    database_path = parsed_url.database
    if not database_path or database_path == ":memory:" or database_path.startswith("file:"):
        return configured_url

    path = Path(database_path)
    if path.is_absolute():
        return configured_url

    project_root = Path(__file__).resolve().parent.parent
    return parsed_url.set(database=str((project_root / path).resolve())).render_as_string(hide_password=False)


def make_engine(url: str | None = None) -> Engine:
    resolved_url = url or database_url()
    connect_args = {}
    if resolved_url.startswith("sqlite:"):
        connect_args["check_same_thread"] = False
        database_path = make_url(resolved_url).database
        if database_path and database_path != ":memory:" and not database_path.startswith("file:"):
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(resolved_url, connect_args=connect_args, pool_pre_ping=True)
    if resolved_url.startswith("sqlite:"):
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
    return engine


@lru_cache(maxsize=8)
def _session_factory_for_url(url: str):
    return sessionmaker(bind=make_engine(url), expire_on_commit=False)


def get_session_factory():
    return _session_factory_for_url(database_url())
