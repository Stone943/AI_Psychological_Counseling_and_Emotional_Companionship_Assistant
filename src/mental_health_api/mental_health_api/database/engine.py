# ruff: noqa: TC002, TC003
"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    from mental_health_api.config import Settings


SessionFactory = async_sessionmaker[AsyncSession]


def create_engine(settings: Settings) -> AsyncEngine:
    """Create the process-wide async engine.

    MySQL gets a bounded, pre-pinged pool. SQLite remains a test-only backend and
    deliberately does not receive QueuePool-only keyword arguments.
    """
    connect_args: dict[str, Any] = {}
    engine_kwargs: dict[str, Any] = {
        "echo": settings.debug,
        "pool_pre_ping": True,
    }
    if settings.database_backend.value == "sqlite":
        connect_args["check_same_thread"] = False
    else:
        connect_args["connect_timeout"] = settings.database_connect_timeout_seconds
        engine_kwargs.update(
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_recycle=settings.database_pool_recycle_seconds,
        )

    return create_async_engine(
        settings.database_url,
        connect_args=connect_args,
        **engine_kwargs,
    )


def create_session_factory(engine: AsyncEngine) -> SessionFactory:
    """Create an async session factory."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a session from the app-owned pool; never create an engine per request."""
    session_factory: SessionFactory = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
