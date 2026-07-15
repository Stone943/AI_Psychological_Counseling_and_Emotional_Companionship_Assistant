"""Alembic environment — async MySQL/SQLite migration support."""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from pathlib import Path
from typing import TYPE_CHECKING

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

from mental_health_api.database.base import Base
from mental_health_api.database.models import *  # noqa: F401,F403 — register all models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    secret_path = os.environ.get("MENTAL_HEALTH_DATABASE_URL_FILE")
    if secret_path:
        path = Path(secret_path)
        if not path.is_absolute() or not path.is_file():
            raise RuntimeError("database URL secret file is unavailable")
        value = path.read_text(encoding="utf-8").strip()
        if not value:
            raise RuntimeError("database URL secret file is empty")
        return value
    return os.environ.get(
        "MENTAL_HEALTH_DATABASE_URL",
        config.get_main_option("sqlalchemy.url", "sqlite+aiosqlite:///./mental_health.db"),
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
