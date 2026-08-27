"""SQLAlchemy 2.0 engine/session wiring. Engine-agnostic by policy (ADR-3):
no SQLite-specific SQL anywhere, so Postgres is a DB_URL change + Alembic."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: sessionmaker[Session] | None = None


def init_engine(db_url: str):
    global _engine, _session_factory
    _engine = create_engine(db_url, future=True)
    _session_factory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def get_engine():
    assert _engine is not None, "init_engine() not called"
    return _engine


def session() -> Session:
    assert _session_factory is not None, "init_engine() not called"
    return _session_factory()
