# ruff: noqa: TC002
"""Idempotent retention batches over the server-side data store."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from mental_health_api.database.models import (
    AssessmentResult,
    AssessmentSafetyTrigger,
    AuditLog,
    Conversation,
    CrisisEvent,
    DeletionTombstone,
    EmotionCorrection,
    EmotionResult,
    ExerciseSession,
    Feedback,
    GuestSession,
    GuestSubject,
    IdempotencyRecord,
    MemoryItem,
    Message,
    OutboxEvent,
    PrivacyJob,
    SafetyContext,
)

SAFETY_EVENT_TYPES = ("risk.status", "safety.question", "safety.resources")


@dataclass(frozen=True)
class RetentionReport:
    expired_guest_sessions: int = 0
    expired_guest_subjects: int = 0
    expired_ephemeral_conversations: int = 0
    expired_normal_outbox: int = 0
    expired_safety_outbox: int = 0
    expired_crisis_events: int = 0
    expired_audit_logs: int = 0
    expired_tombstones: int = 0
    expired_idempotency_records: int = 0
    expired_guest_business_records: int = 0
    expired_safety_contexts: int = 0
    scrubbed_conversation_records: int = 0

    @property
    def total_deleted(self) -> int:
        return sum(self.__dict__.values())


class RetentionWorker:
    """Delete only records whose frozen retention deadline has elapsed."""

    LOCK_NAME = "mental_health_retention_v1"

    def __init__(self, session: AsyncSession, *, now: datetime | None = None) -> None:
        self._session = session
        self._lock_connection: AsyncConnection | None = None
        self._now = now or datetime.now(UTC)
        if self._now.tzinfo is None:
            raise ValueError("retention clock must be timezone-aware")

    async def run_once(self) -> RetentionReport:
        acquired = await self._acquire_lock()
        if not acquired:
            return RetentionReport()
        try:
            guest_subject_ids = list(
                (
                    await self._session.scalars(
                        select(GuestSubject.guest_subject_id).where(
                            or_(GuestSubject.expires_at <= self._now, GuestSubject.revoked_at.is_not(None))
                        )
                    )
                ).all()
            )
            conversation_ids = list(
                (
                    await self._session.scalars(
                        select(Conversation.conversation_id).where(
                            or_(
                                (
                                    (Conversation.persistence_mode == "ephemeral")
                                    & Conversation.expires_at.is_not(None)
                                    & (Conversation.expires_at <= self._now)
                                ),
                                Conversation.subject_id.in_(guest_subject_ids),
                            )
                        )
                    )
                ).all()
            )
            guest_business = await self._delete_subject_business(guest_subject_ids)
            scrubbed_records = await self._delete_conversation_payloads(conversation_ids)
            values = {
                "expired_guest_sessions": await self._delete(
                    GuestSession, or_(GuestSession.expires_at <= self._now, GuestSession.revoked_at.is_not(None))
                ),
                "expired_ephemeral_conversations": 0,
                "expired_normal_outbox": await self._delete(
                    OutboxEvent,
                    OutboxEvent.acked.is_(True),
                    OutboxEvent.type.not_in(SAFETY_EVENT_TYPES),
                    OutboxEvent.occurred_at <= self._now - timedelta(days=7),
                ),
                "expired_safety_outbox": await self._delete(
                    OutboxEvent,
                    OutboxEvent.type.in_(SAFETY_EVENT_TYPES),
                    OutboxEvent.occurred_at <= self._now - timedelta(days=30),
                ),
                "expired_crisis_events": await self._delete(
                    CrisisEvent, CrisisEvent.occurred_at <= self._now - timedelta(days=30)
                ),
                "expired_safety_contexts": await self._delete(
                    SafetyContext, SafetyContext.created_at <= self._now - timedelta(days=30)
                ),
                "expired_audit_logs": await self._delete(
                    AuditLog, AuditLog.occurred_at <= self._now - timedelta(days=90)
                ),
                "expired_tombstones": await self._delete(DeletionTombstone, DeletionTombstone.expires_at <= self._now),
                "expired_idempotency_records": await self._delete(
                    IdempotencyRecord, IdempotencyRecord.expires_at <= self._now
                ),
                "expired_guest_business_records": guest_business,
                "scrubbed_conversation_records": scrubbed_records,
            }
            values["expired_ephemeral_conversations"] = await self._delete_empty_conversation_shells(conversation_ids)
            # Subjects are deleted after their session rows to preserve FK order.
            orphaned_or_expired = or_(
                GuestSubject.expires_at <= self._now,
                GuestSubject.revoked_at.is_not(None),
                ~select(GuestSession.id).where(GuestSession.guest_subject_id == GuestSubject.guest_subject_id).exists(),
            )
            values["expired_guest_subjects"] = await self._delete(GuestSubject, orphaned_or_expired)
            await self._session.commit()
            return RetentionReport(**values)
        except Exception:
            await self._session.rollback()
            raise
        finally:
            await self._release_lock()

    async def _delete_subject_business(self, subject_ids: list[str]) -> int:
        if not subject_ids:
            return 0
        deleted = 0
        # Child-first order is required because assessment trigger rows have a
        # real FK and MySQL bulk deletes do not run ORM cascades.
        deleted += await self._delete(AssessmentSafetyTrigger, AssessmentSafetyTrigger.subject_id.in_(subject_ids))
        for model in (AssessmentResult, ExerciseSession, Feedback, MemoryItem, PrivacyJob, IdempotencyRecord):
            deleted += await self._delete(model, model.subject_id.in_(subject_ids))
        return deleted

    async def _delete_conversation_payloads(self, conversation_ids: list[str]) -> int:
        if not conversation_ids:
            return 0
        emotion_ids = select(EmotionResult.emotion_result_id).where(EmotionResult.conversation_id.in_(conversation_ids))
        deleted = await self._delete(EmotionCorrection, EmotionCorrection.emotion_result_id.in_(emotion_ids))
        deleted += await self._delete(EmotionResult, EmotionResult.conversation_id.in_(conversation_ids))
        deleted += await self._delete(Message, Message.conversation_id.in_(conversation_ids))
        deleted += await self._delete(
            OutboxEvent,
            OutboxEvent.conversation_id.in_(conversation_ids),
            OutboxEvent.type.not_in(SAFETY_EVENT_TYPES),
        )
        # Assessment rows may bind a conversation without a database FK.
        result_ids = select(AssessmentResult.assessment_result_id).where(
            AssessmentResult.conversation_id.in_(conversation_ids)
        )
        deleted += await self._delete(
            AssessmentSafetyTrigger, AssessmentSafetyTrigger.assessment_result_id.in_(result_ids)
        )
        deleted += await self._delete(AssessmentResult, AssessmentResult.conversation_id.in_(conversation_ids))
        await self._session.execute(
            update(Conversation).where(Conversation.conversation_id.in_(conversation_ids)).values(title=None)
        )
        return deleted

    async def _delete_empty_conversation_shells(self, candidate_ids: list[str]) -> int:
        if not candidate_ids:
            return 0
        has_outbox = select(OutboxEvent.id).where(OutboxEvent.conversation_id == Conversation.conversation_id).exists()
        has_safety = (
            select(SafetyContext.safety_context_id)
            .where(SafetyContext.conversation_id == Conversation.conversation_id)
            .exists()
        )
        has_crisis = (
            select(CrisisEvent.crisis_event_id)
            .where(CrisisEvent.conversation_id == Conversation.conversation_id)
            .exists()
        )
        return await self._delete(
            Conversation,
            Conversation.conversation_id.in_(candidate_ids),
            ~has_outbox,
            ~has_safety,
            ~has_crisis,
        )

    async def _delete(self, model: type, *conditions: Any) -> int:
        result = await self._session.execute(delete(model).where(*conditions))
        return int(getattr(result, "rowcount", 0) or 0)

    async def _acquire_lock(self) -> bool:
        bind = self._session.get_bind()
        if bind.dialect.name != "mysql":
            return True
        async_bind = self._session.bind
        if isinstance(async_bind, AsyncConnection):
            engine = async_bind.engine
        elif isinstance(async_bind, AsyncEngine):
            engine = async_bind
        else:
            raise RuntimeError("retention session has no async engine binding")
        connection = await engine.connect()
        try:
            result = await connection.execute(text("SELECT GET_LOCK(:name, 0)"), {"name": self.LOCK_NAME})
            acquired = result.scalar_one_or_none() == 1
            if not acquired:
                await connection.rollback()
                await connection.close()
                return False
            self._lock_connection = connection
            return True
        except Exception:
            await connection.close()
            raise

    async def _release_lock(self) -> None:
        connection = self._lock_connection
        if connection is None:
            return
        self._lock_connection = None
        try:
            result = await connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": self.LOCK_NAME})
            if result.scalar_one_or_none() != 1:
                raise RuntimeError("retention advisory lock was not owned by the release connection")
            await connection.commit()
        finally:
            await connection.close()
