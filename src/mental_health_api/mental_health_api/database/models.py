# ruff: noqa: E501  # ORM column definitions are fine as-is
"""SQLAlchemy ORM models for all entities in PRD section 17.

Key invariants:
- messages.message_ordinal is the conversational order; NEVER named `sequence`.
- outbox_events has conversation_id + sequence (B-owned, allocated in transaction).
- Sensitive fields are encrypted at the application layer (AES-256-GCM).
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — needed by SQLAlchemy at runtime for Mapped[datetime]

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mental_health_api.database.base import Base, TimestampMixin

# ─── Identity & Sessions ─────────────────────────────────────────────────────


class User(Base, TimestampMixin):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    nickname_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)

    device_sessions: Mapped[list[DeviceSession]] = relationship(back_populates="user", cascade="all, delete-orphan")
    consents: Mapped[list[Consent]] = relationship(back_populates="user", cascade="all, delete-orphan")


class GuestSubject(Base, TimestampMixin):
    __tablename__ = "guest_subjects"

    guest_subject_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    device_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sessions: Mapped[list[GuestSession]] = relationship(back_populates="guest_subject", cascade="all, delete-orphan")


class GuestSession(Base):
    __tablename__ = "guest_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    guest_subject_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("guest_subjects.guest_subject_id"), nullable=False
    )
    token_digest: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    device_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    guest_subject: Mapped[GuestSubject] = relationship(back_populates="sessions")


class DeviceSession(Base, TimestampMixin):
    __tablename__ = "device_sessions"

    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    refresh_family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    refresh_token_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="device_sessions")


class Consent(Base, TimestampMixin):
    __tablename__ = "consents"

    consent_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consent_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="missing")
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="consents")

    __table_args__ = (
        UniqueConstraint("user_id", "consent_type", name="uq_user_consent_type"),
        Index("ix_consents_subject_type", "subject_id", "consent_type"),
    )


# ─── Conversations & Messages ────────────────────────────────────────────────


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    conversation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False, default="user")  # "user" | "guest"
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="chat")
    persistence_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="saved")
    risk_state: Mapped[str] = mapped_column(String(8), nullable=False, default="L0")
    next_event_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    messages: Mapped[list[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    outbox_events: Mapped[list[OutboxEvent]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.conversation_id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # "user" | "assistant" | "system"
    content_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="sent")
    message_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    emotion_results: Mapped[list[EmotionResult]] = relationship(back_populates="message")

    __table_args__ = (
        UniqueConstraint("conversation_id", "message_ordinal", name="uq_message_ordinal"),
        Index("ix_messages_conversation_ordinal", "conversation_id", "message_ordinal"),
    )


class OutboxEvent(Base, TimestampMixin):
    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.conversation_id"), nullable=False, index=True
    )
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    acked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="outbox_events")

    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence", name="uq_outbox_sequence"),
        Index("ix_outbox_acked_expires", "acked", "expires_at"),
    )


# ─── AI / Emotion / Safety ───────────────────────────────────────────────────


class EmotionResult(Base):
    __tablename__ = "emotion_results"

    emotion_result_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.conversation_id"), nullable=False, index=True
    )
    message_id: Mapped[str] = mapped_column(String(64), ForeignKey("messages.message_id"), nullable=False)
    primary_emotion: Mapped[str] = mapped_column(String(32), nullable=False)
    secondary_emotions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    intensity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="classified")
    evidence_summary: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    message: Mapped[Message] = relationship(back_populates="emotion_results")
    corrections: Mapped[list[EmotionCorrection]] = relationship(
        back_populates="emotion_result", cascade="all, delete-orphan"
    )


class EmotionCorrection(Base):
    __tablename__ = "emotion_corrections"

    correction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    emotion_result_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("emotion_results.emotion_result_id"), nullable=False
    )
    corrected_primary_emotion: Mapped[str] = mapped_column(String(32), nullable=False)
    corrected_intensity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correction_note_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    emotion_result: Mapped[EmotionResult] = relationship(back_populates="corrections")


class SafetyContext(Base):
    __tablename__ = "safety_contexts"

    safety_context_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # "assessment" | "free_text"
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.conversation_id"), nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="confirmation_required")
    current_risk_level: Mapped[str] = mapped_column(String(8), nullable=False, default="L1")
    question_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CrisisEvent(Base):
    __tablename__ = "crisis_events"

    crisis_event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.conversation_id"), nullable=False, index=True
    )
    risk_level: Mapped[str] = mapped_column(String(8), nullable=False)
    signal_category: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(16), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ─── Content / Exercises / Assessments ───────────────────────────────────────


class KnowledgeContent(Base):
    __tablename__ = "knowledge_contents"

    article_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    topics_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    source_refs_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    review_record_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False, default="CN-mainland")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)


class ExerciseDefinition(Base):
    __tablename__ = "exercise_definitions"

    exercise_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    steps_json: Mapped[str] = mapped_column(Text, nullable=False)
    review_record_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)


class ExerciseSession(Base, TimestampMixin):
    __tablename__ = "exercise_sessions"

    exercise_session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    exercise_id: Mapped[str] = mapped_column(String(64), nullable=False)
    definition_version: Mapped[str] = mapped_column(String(16), nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AssessmentDefinition(Base):
    __tablename__ = "assessment_definitions"

    scale: Mapped[str] = mapped_column(String(16), primary_key=True)  # "PHQ9" | "GAD7"
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    items_json: Mapped[str] = mapped_column(Text, nullable=False)
    scoring_rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    display_json: Mapped[str] = mapped_column(Text, nullable=False)
    review_record_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)


class AssessmentResult(Base, TimestampMixin):
    __tablename__ = "assessment_results"

    assessment_result_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scale: Mapped[str] = mapped_column(String(16), nullable=False)
    scale_version: Mapped[str] = mapped_column(String(16), nullable=False)
    answers_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    safety_trigger: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    result_release_state: Mapped[str] = mapped_column(String(32), nullable=False, default="released")
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AssessmentSafetyTrigger(Base):
    __tablename__ = "assessment_safety_triggers"

    trigger_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    assessment_result_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("assessment_results.assessment_result_id"), nullable=False
    )
    scale: Mapped[str] = mapped_column(String(16), nullable=False)
    scale_version: Mapped[str] = mapped_column(String(16), nullable=False)
    item_id: Mapped[str] = mapped_column(String(16), nullable=False)
    answer: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ─── Memory ──────────────────────────────────────────────────────────────────


class MemoryItem(Base, TimestampMixin):
    __tablename__ = "memory_items"

    memory_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    value_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    memory_version: Mapped[str] = mapped_column(String(16), nullable=False, default="v1")


# ─── Crisis Resources ────────────────────────────────────────────────────────


class CrisisResource(Base):
    __tablename__ = "crisis_resources"

    region: Mapped[str] = mapped_column(String(32), primary_key=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="zh-CN")
    resources_json: Mapped[str] = mapped_column(Text, nullable=False)
    bundle_version: Mapped[str] = mapped_column(String(16), nullable=False)
    resource_status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)


# ─── Feedback ────────────────────────────────────────────────────────────────


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"

    feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    comment_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted")


# ─── Privacy / Admin ─────────────────────────────────────────────────────────


class PrivacyJob(Base, TimestampMixin):
    __tablename__ = "privacy_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "export" | "deletion" | "account_closure"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    download_credential_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeletionTombstone(Base):
    __tablename__ = "deletion_tombstones"

    object_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class RecoveryToken(Base):
    __tablename__ = "recovery_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    token_digest: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    object_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    hash_chain: Mapped[str | None] = mapped_column(String(128), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
