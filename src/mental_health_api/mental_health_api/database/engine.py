"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    from mental_health_api.config import Settings


def create_engine(settings: Settings):
    """Create an async SQLAlchemy engine from application settings."""
    connect_args: dict = {}
    if settings.database_backend.value == "sqlite":
        connect_args["check_same_thread"] = False

    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args=connect_args,
    )
    return engine


def create_session_factory(engine):
    """Create an async session factory."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session(settings: Settings):
    """Dependency: yields an AsyncSession."""
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
