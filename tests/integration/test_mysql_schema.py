"""Verify that SQLAlchemy models produce correct MySQL schema.

These tests use SQLite for CI (no MySQL required) but check invariants
that must hold on MySQL: no message.sequence column, message_ordinal exists, etc.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from mental_health_api.database.base import Base
from mental_health_api.database.models import *  # noqa: F401,F403


@pytest.fixture
async def engine():
    """In-memory SQLite engine for schema verification."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_all_tables_created(engine) -> None:
    """All expected tables exist after create_all."""
    async with engine.connect() as conn:

        def get_tables(sync_conn):
            insp = inspect(sync_conn)
            return set(insp.get_table_names())

        tables = await conn.run_sync(get_tables)
    expected = {
        "users",
        "guest_subjects",
        "guest_sessions",
        "device_sessions",
        "consents",
        "conversations",
        "messages",
        "outbox_events",
        "emotion_results",
    }
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


@pytest.mark.asyncio
async def test_message_has_no_sequence_column(engine) -> None:
    """Messages table MUST NOT have a `sequence` column."""
    async with engine.connect() as conn:

        def get_columns(sync_conn, table_name):
            insp = inspect(sync_conn)
            return {c["name"] for c in insp.get_columns(table_name)}

        cols = await conn.run_sync(get_columns, "messages")
    assert "sequence" not in cols, "messages must NOT have 'sequence' column"
    assert "message_ordinal" in cols, "messages must have 'message_ordinal' column"


@pytest.mark.asyncio
async def test_outbox_has_sequence_column(engine) -> None:
    """Outbox events table MUST have a `sequence` column."""
    async with engine.connect() as conn:

        def get_columns(sync_conn, table_name):
            insp = inspect(sync_conn)
            return {c["name"] for c in insp.get_columns(table_name)}

        cols = await conn.run_sync(get_columns, "outbox_events")
    assert "sequence" in cols, "outbox_events must have 'sequence' column"
    assert "conversation_id" in cols


@pytest.mark.asyncio
async def test_conversation_has_next_event_sequence(engine) -> None:
    """Conversations must have next_event_sequence for B's sequence allocation."""
    async with engine.connect() as conn:

        def get_columns(sync_conn):
            insp = inspect(sync_conn)
            return {c["name"] for c in insp.get_columns("conversations")}

        cols = await conn.run_sync(get_columns)
    assert "next_event_sequence" in cols
    assert "persistence_mode" in cols


@pytest.mark.asyncio
async def test_unique_constraints(engine) -> None:
    """Key unique constraints are enforced."""
    async with engine.connect() as conn:

        def get_unique(sync_conn, table_name):
            insp = inspect(sync_conn)
            return {c["name"] for c in insp.get_unique_constraints(table_name)}

        msg_unique = await conn.run_sync(get_unique, "messages")
        assert "uq_message_ordinal" in msg_unique

        outbox_unique = await conn.run_sync(get_unique, "outbox_events")
        assert "uq_outbox_sequence" in outbox_unique
