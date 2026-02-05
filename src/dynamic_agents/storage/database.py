"""Async SQLAlchemy engine helpers for the project."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..models import Base

ENV_KEYS = ("DATABASE_URL", "DYNAMIC_AGENTS_DATABASE_URL")

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _read_database_url() -> str:
    for key in ENV_KEYS:
        value = os.environ.get(key)
        if value:
            return value
    raise RuntimeError(
        "Database URL not configured. Set DATABASE_URL (or DYNAMIC_AGENTS_DATABASE_URL)."
    )


def _ensure_async_driver(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("sqlite+aiosqlite://"):
        return url
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def get_engine(database_url: str | None = None, *, echo: bool | None = None) -> AsyncEngine:
    """Return a process-wide async engine, creating it on first access."""

    global _engine
    if _engine is None:
        raw_url = database_url or _read_database_url()
        async_url = _ensure_async_driver(raw_url)
        _engine = create_async_engine(async_url, echo=bool(echo), pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory tied to the current engine."""

    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Provide an async session to be used inside FastAPI dependencies."""

    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db(engine: AsyncEngine | None = None) -> None:
    """Create database tables for all declarative metadata."""

    engine = engine or get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


__all__ = [
    "get_async_session",
    "get_engine",
    "get_session_factory",
    "init_db",
]
