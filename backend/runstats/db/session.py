"""SQLAlchemy engine and session helpers."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from runstats.config import Settings, get_settings

SessionFactory = sessionmaker[Session]


def create_sqlite_engine(settings: Settings | None = None) -> Engine:
    """Create the configured SQLite engine with local-first pragmas enabled."""

    resolved_settings = settings or get_settings()
    resolved_settings.ensure_local_directories()
    engine = create_engine(
        resolved_settings.database_url,
        connect_args={"check_same_thread": False},
        future=True,
    )
    event.listen(engine, "connect", _set_sqlite_pragmas)
    return engine


def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    """Enable SQLite behavior required by RunStats."""

    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
    finally:
        cursor.close()


def create_session_factory(engine: Engine) -> SessionFactory:
    """Create a session factory bound to the given engine."""

    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


def get_db_session(request: Request) -> Generator[Session, None, None]:
    """FastAPI dependency yielding one database session per request."""

    session_factory: SessionFactory = request.app.state.session_factory
    with session_factory() as session:
        yield session
