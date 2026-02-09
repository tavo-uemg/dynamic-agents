"""Alembic environment configuration supporting async migrations."""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from pathlib import Path

import sys

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dynamic_agents.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _coerce_async_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+" not in url.split("://", 1)[0]:
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def _get_database_url() -> str:
    env_url = (
        os.getenv("ALEMBIC_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or os.getenv("DYNAMIC_AGENTS_DATABASE_URL")
    )
    if env_url:
        return _coerce_async_url(env_url)
    return _coerce_async_url(config.get_main_option("sqlalchemy.url"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine."""

    connectable: AsyncEngine = create_async_engine(
        _get_database_url(),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
