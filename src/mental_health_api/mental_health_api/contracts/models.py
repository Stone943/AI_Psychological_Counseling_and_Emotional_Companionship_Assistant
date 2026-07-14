"""Strict Pydantic v2 models for all public API types.

These are the single source of truth for REST request/response bodies,
WebSocket command/event payloads, and OpenAPI/JSON Schema generation.

All models use extra="forbid" — unknown fields are rejected.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from datetime import datetime

# ─── Base ────────────────────────────────────────────────────────────────────


class BaseContract(BaseModel):
    """Every public contract model must forbid unknown fields."""

    model_config = ConfigDict(extra="forbid")


# ─── Enums ───────────────────────────────────────────────────────────────────


class RiskLevel(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class PersistenceMode(str, Enum):
    ephemeral = "ephemeral"
    saved = "saved"


class ConversationMode(str, Enum):
    chat = "chat"
    assessment_safety = "assessment_safety"
    free_text_safety = "free_text_safety"


class EmotionLabel(str, Enum):
    anxiety = "anxiety"
    depression = "depression"
    stress = "stress"
    sadness = "sadness"
    anger = "anger"
    fear = "fear"
    loneliness = "loneliness"
    calm = "calm"
    unknown = "unknown"


class EmotionStatus(str, Enum):
    classified = "classified"
    uncertain = "uncertain"
    unavailable = "unavailable"


class ConsentStatus(str, Enum):
    granted = "granted"
    withdrawn = "withdrawn"
    missing = "missing"


class ConsentType(str, Enum):
    cloud_model_processing = "cloud_model_processing"
    memory = "memory"
    trends = "trends"
    training = "training"


class ProviderPolicyStatus(str, Enum):
    disabled = "disabled"
    approved = "approved"
    expired = "expired"


class CrossBorderStatus(str, Enum):
    not_applicable = "not_applicable"
    approved = "approved"
    blocked = "blocked"


class FeedbackTarget(str, Enum):
    ai_response = "ai_response"
    knowledge_article = "knowledge_article"
    crisis_event = "crisis_event"


class FeedbackCategory(str, Enum):
    helpful = "helpful"
    not_helpful = "not_helpful"
    inaccurate = "inaccurate"
    uncomfortable = "uncomfortable"
    outdated = "outdated"
    unclear = "unclear"
    false_positive = "false_positive"


class SafetyContextKind(str, Enum):
    free_text = "free_text"
    assessment = "assessment"


class SafetyAnswerId(str, Enum):
    safe_now = "safe_now"
    not_safe = "not_safe"
    unsure = "unsure"


class ContentStatus(str, Enum):
    draft = "draft"
    pending_review = "pending_review"
    published = "published"
    withdrawn = "withdrawn"
    archived = "archived"


class ContentType(str, Enum):
    knowledge = "knowledge"
    exercise = "exercise"
    assessment = "assessment"
    crisis_resource = "crisis_resource"
    safety_ui = "safety_ui"


class ResourceStatus(str, Enum):
    active = "active"
    degraded = "degraded"


# ─── PublicError ─────────────────────────────────────────────────────────────


class PublicError(BaseContract):
    """Standardized error envelope. Never exposes internals."""

    code: str
    request_id: str = ""
    retryable: bool
    client_action: str
    retry_after_seconds: int | None = None


# ─── WebSocket Envelopes ─────────────────────────────────────────────────────


class ClientCommandEnvelope(BaseContract):
    """Client → Server WS command. NO sequence field."""

    protocol_version: Literal["v1"] = "v1"
    command_id: str
    conversation_id: str
    idempotency_key: str
    sent_at: datetime
    type: Literal["message.send", "generation.cancel", "session.resume", "session.ack", "safety.answer"]
    payload: dict[str, Any]


class ServerEventEnvelope(BaseContract):
    """Server → Client WS event. B is sole sequence allocator."""

    protocol_version: Literal["v1"] = "v1"
    event_id: str
    conversation_id: str
    message_id: str | None = None
    sequence: int = Field(ge=0)
    idempotency_key: str
    occurred_at: datetime
    type: Literal[
        "message.accepted",
        "risk.status",
        "emotion.result",
        "response.delta",
        "response.completed",
        "response.blocked",
        "safety.question",
        "safety.resources",
        "assessment.result.available",
        "memory.mode.changed",
        "error",
    ]
    payload: dict[str, Any]


# ─── Safety ──────────────────────────────────────────────────────────────────


class FreeTextSafetyRequest(BaseContract):
    """B constructs this for A's screen_text(). text lives in RAM only."""

    request_id: str
    subject_id: str
    conversation_id: str | None = None
    entry_point: str
    field_name: str
    context_ref: str
    text: str  # MUST NOT enter URL/ORM/log/outbox
    idempotency_key: str
    occurred_at: datetime


class FreeTextSafetyResult(BaseContract):
    """A returns this from screen_text()."""

    decision: Literal["allow", "block", "error"]
    screening_decision_id: str | None = None
    risk_decision: RiskLevel = RiskLevel.L0
    pii_result: dict[str, Any] = Field(default_factory=dict)
    safe_template_id: str | None = None
    safety_action_ids: list[str] = Field(default_factory=list)
    evidence_codes: list[str] = Field(default_factory=list)
    rule_version: str = "v1"
    model_version: str | None = None


class SafetyRequiredResponse(BaseContract):
    """Returned when any free-text or assessment entry triggers L1-L3."""

    status: Literal["safety_required"] = "safety_required"
    safety_event_id: str
    conversation_id: str
    risk_level: RiskLevel
    safety_context_kind: SafetyContextKind
    safety_context_id: str
    prompt_template_id: str
    action_ids: list[str] = Field(default_factory=list)
    resource_bundle_version: str = "v1"
    # free_text branch
    entry_point: str | None = None
    # assessment branch
    assessment_result_id: str | None = None
    scale: Literal["PHQ9"] | None = None
    item_id: Literal["PHQ9_Q9"] | None = None
    safety_required: bool | None = None
    result_release_state: Literal["held_for_safety"] | None = None
    result_visible: bool | None = None
    result: None = None


class SafetyQuestionPayload(BaseContract):
    """WS event payload for safety.question."""

    safety_context_kind: SafetyContextKind
    safety_context_id: str
    safety_state: Literal["confirmation_required"] = "confirmation_required"
    prompt_template_id: str
    action_ids: list[str] = Field(default_factory=list)
    resource_bundle_version: str = "v1"


class SafetyAnswerPayload(BaseContract):
    """WS command payload for safety.answer."""

    safety_event_id: str
    safety_context_kind: SafetyContextKind
    safety_context_id: str
    answer_id: SafetyAnswerId


# ─── Guest ───────────────────────────────────────────────────────────────────


class GuestSessionRequest(BaseContract):
    """Request body for POST /v1/guest-sessions."""

    device_key: str = ""


class GuestSessionResponse(BaseContract):
    """Response body for POST /v1/guest-sessions."""

    guest_subject_id: str
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_at: datetime
    scopes: list[str] = Field(default_factory=list)


class GuestSessionStatus(BaseContract):
    """Response body for GET /v1/guest-sessions/current."""

    guest_subject_id: str
    created_at: datetime
    expires_at: datetime
    scopes: list[str] = Field(default_factory=list)


class GuestMigrationRequest(BaseContract):
    """Request body for POST /v1/guest-migrations."""

    batch_id: str
    record_types: list[str] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)


class GuestMigrationResponse(BaseContract):
    """Response body for guest migration status."""

    batch_id: str
    status: Literal["committed", "safety_required", "in_progress"]
    commit_proof: dict[str, Any] | None = None
    safety_response: SafetyRequiredResponse | None = None


# ─── Consent ─────────────────────────────────────────────────────────────────


class ConsentSnapshot(BaseContract):
    """B's ConsentSnapshotPort adapter returns this to A."""

    subject_id: str
    consent_type: ConsentType
    policy_version: int = Field(ge=0)
    consent_version: int = Field(ge=0)
    status: ConsentStatus
    granted_at: datetime | None = None
    withdrawn_at: datetime | None = None
    loaded_at: datetime


class ProviderProcessingPolicySnapshot(BaseContract):
    """B's ProviderProcessingPolicyPort adapter returns this to A."""

    provider_id: str
    policy_version: int = Field(ge=1)
    status: ProviderPolicyStatus
    matrix_sha256: str | None = None
    processor_contract_ref: str | None = None
    independent_review_ref: str | None = None
    data_region: str = ""
    cross_border_status: CrossBorderStatus = CrossBorderStatus.not_applicable
    approved_at: datetime | None = None
    review_expires_at: datetime | None = None
    loaded_at: datetime


# ─── Auth / Account ──────────────────────────────────────────────────────────


class RegisterRequest(BaseContract):
    email: str
    password: str
    nickname: str | None = None


class LoginRequest(BaseContract):
    email: str
    password: str


class TokenResponse(BaseContract):
    access_token: str
    refresh_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int


class RefreshRequest(BaseContract):
    refresh_token: str


class RecoveryRequest(BaseContract):
    email: str


class RecoveryConfirmation(BaseContract):
    token: str
    new_password: str


# ─── Conversation / Message ──────────────────────────────────────────────────


class ConversationCreate(BaseContract):
    title: str | None = None
    persistence_mode: PersistenceMode = PersistenceMode.saved
    mode: ConversationMode = ConversationMode.chat


class ConversationResponse(BaseContract):
    conversation_id: str
    subject_id: str
    title: str | None = None
    mode: ConversationMode
    persistence_mode: PersistenceMode
    risk_state: RiskLevel = RiskLevel.L0
    next_event_sequence: int = 0
    created_at: datetime
    updated_at: datetime


class ConversationSummaryResponse(BaseContract):
    conversation_id: str
    summary: str
    generated_at: datetime


# ─── Emotion ─────────────────────────────────────────────────────────────────


class EmotionResultResponse(BaseContract):
    emotion_result_id: str
    conversation_id: str
    message_id: str
    primary_emotion: EmotionLabel
    secondary_emotions: list[EmotionLabel] = Field(default_factory=list, max_length=2)
    intensity: int = Field(ge=0, le=3)
    confidence: float = Field(ge=0.0, le=1.0)
    status: EmotionStatus
    evidence_summary: str = Field(min_length=1, max_length=160)
    model_version: str
    occurred_at: datetime


class EmotionCorrectionRequest(BaseContract):
    corrected_primary_emotion: EmotionLabel
    corrected_intensity: int | None = Field(default=None, ge=0, le=3)
    correction_note: str | None = None


class EmotionCorrectionResponse(BaseContract):
    correction_id: str
    emotion_result_id: str
    corrected_primary_emotion: EmotionLabel
    corrected_intensity: int | None = None
    accepted_at: datetime


# ─── Feedback ────────────────────────────────────────────────────────────────


class FeedbackRequest(BaseContract):
    target_id: str
    target_type: FeedbackTarget
    category: FeedbackCategory
    comment: str | None = None


class FeedbackResponse(BaseContract):
    feedback_id: str
    target_id: str
    target_type: FeedbackTarget
    category: FeedbackCategory
    status: str
    created_at: datetime


# ─── Memory ──────────────────────────────────────────────────────────────────


class MemoryCapabilityResponse(BaseContract):
    mode: Literal["controlled", "history_only"]
    reason: str
    policy_version: str
    effective_at: datetime
    memory_version: str


class MemoryContextProof(BaseContract):
    mode: Literal["controlled", "history_only"]
    included_memory_ids: list[str] = Field(default_factory=list)
    exclusion_reason_codes: list[str] = Field(default_factory=list)
    policy_version: str


class MemoryCreateRequest(BaseContract):
    value: str
    source: str = "conversation_summary"


class MemoryResponse(BaseContract):
    memory_id: str
    memory_type: str
    value_ciphertext: str
    source: str
    confirmed_at: datetime | None = None
    disabled_at: datetime | None = None
    created_at: datetime


# ─── Assessment ──────────────────────────────────────────────────────────────


class AssessmentSubmissionRequest(BaseContract):
    answers: list[dict[str, Any]]
    optional_note: str | None = None


class AssessmentResultResponse(BaseContract):
    assessment_result_id: str
    conversation_id: str | None = None
    scale: Literal["PHQ9", "GAD7"]
    scale_version: str
    score: int
    severity: str
    display: dict[str, Any]
    result_release_state: Literal["released", "held_for_safety"]
    safety_required: bool = False
    safety_event_id: str | None = None
    result_visible: bool = True
    completed_at: datetime


class AssessmentResultExport(BaseContract):
    export_version: Literal["assessment-result.v1"] = "assessment-result.v1"
    generated_at: datetime
    result: AssessmentResultResponse


# ─── Knowledge ───────────────────────────────────────────────────────────────


class KnowledgeSearchRequest(BaseContract):
    query: str
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeArticleResponse(BaseContract):
    article_id: str
    title: str
    body_markdown: str
    topics: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    version: str
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None


# ─── Crisis ──────────────────────────────────────────────────────────────────


class CrisisResourceResponse(BaseContract):
    region: str
    language: str
    bundle_version: str
    resource_status: ResourceStatus
    degraded_reason: str | None = None
    verified_at: datetime | None = None
    expires_at: datetime | None = None
    resources: list[dict[str, Any]] = Field(default_factory=list)


# ─── Privacy ─────────────────────────────────────────────────────────────────


class PrivacyJobStatus(BaseContract):
    job_id: str
    job_type: Literal["export", "deletion", "account_closure"]
    status: Literal["pending", "in_progress", "completed", "failed"]
    created_at: datetime
    completed_at: datetime | None = None
    download_url: str | None = None


# ─── WS Payloads ─────────────────────────────────────────────────────────────


class MessageSendPayload(BaseContract):
    client_message_id: str
    text: str
    mode: Literal["support", "clarify", "exercise", "knowledge"] | None = None


class GenerationCancelPayload(BaseContract):
    response_id: str


class SessionResumePayload(BaseContract):
    last_ack: int = Field(ge=-1)


class SessionAckPayload(BaseContract):
    acked_sequence: int = Field(ge=0)


class ResponseDeltaPayload(BaseContract):
    response_id: str
    chunk_index: int = Field(ge=0)
    text: str


class ResponseCompletedPayload(BaseContract):
    response_id: str
    total_chunks: int = Field(ge=0)
    response_source: str
    outcome: str
    feedback_target_id: str | None = None


class ResponseBlockedPayload(BaseContract):
    response_id: str
    outcome: str
    template_id: str
    public_error_code: str


class MessageAcceptedPayload(BaseContract):
    client_message_id: str
    accepted: Literal["normal", "safety_required"]
    safety_response: SafetyRequiredResponse | None = None


class RiskStatusPayload(BaseContract):
    risk_level: RiskLevel
    conversation_id: str


class EmotionResultPayload(BaseContract):
    emotion_result_id: str
    conversation_id: str
    message_id: str
    primary_emotion: EmotionLabel
    secondary_emotions: list[EmotionLabel] = Field(default_factory=list, max_length=2)
    intensity: int = Field(ge=0, le=3)
    confidence: float = Field(ge=0.0, le=1.0)
    status: EmotionStatus
    evidence_summary: str
    model_version: str
    occurred_at: datetime


class AssessmentResultAvailablePayload(BaseContract):
    assessment_result_id: str
    result_release_state: Literal["released"] = "released"


class MemoryModeChangedPayload(BaseContract):
    mode: Literal["controlled", "history_only"]
    memory_version: str
    reason: str
