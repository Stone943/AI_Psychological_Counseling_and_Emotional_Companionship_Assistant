"""Retention worker child-first deletion tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from mental_health_api.database.base import Base
from mental_health_api.database.models import AssessmentResult, Conversation, GuestSession, GuestSubject, Message
from mental_health_api.privacy.retention_worker import RetentionWorker


@pytest.mark.asyncio
async def test_expired_guest_cleanup_leaves_no_sensitive_children() -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    expired = now - timedelta(seconds=1)
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add_all(
            [
                GuestSubject(guest_subject_id="guest", device_key_hash="hash", scopes="", expires_at=expired),
                GuestSession(
                    id=1,
                    guest_subject_id="guest",
                    token_digest="digest",
                    device_key_hash="hash",
                    scopes="",
                    expires_at=expired,
                    created_at=expired,
                ),
                Conversation(
                    conversation_id="conversation",
                    subject_id="guest",
                    subject_type="guest",
                    title="sensitive title",
                    persistence_mode="ephemeral",
                    expires_at=expired,
                ),
                Message(
                    message_id="message",
                    conversation_id="conversation",
                    role="user",
                    content_ciphertext="ciphertext",
                    message_ordinal=0,
                ),
                AssessmentResult(
                    assessment_result_id="assessment",
                    subject_id="guest",
                    conversation_id="conversation",
                    scale="PHQ9",
                    scale_version="v1",
                    answers_ciphertext="ciphertext",
                    score=1,
                    severity="minimal",
                    completed_at=expired,
                ),
            ]
        )
        await session.commit()

        report = await RetentionWorker(session, now=now).run_once()
        assert report.total_deleted >= 5
        for model in (GuestSubject, GuestSession, Conversation, Message, AssessmentResult):
            assert await session.scalar(select(func.count()).select_from(model)) == 0

    await engine.dispose()
