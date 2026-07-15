# ruff: noqa: TC003
"""Fail-closed adapter for Member A's free-text safety service."""

from __future__ import annotations

import asyncio
import inspect
import re
from collections.abc import Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

from mental_health_api.safety.free_text_registry import get_entry


class RiskDecision(StrEnum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class ScreeningDecision(StrEnum):
    allow = "allow"
    block = "block"
    error = "error"


@dataclass(frozen=True, repr=False)
class FreeTextSafetyRequest:
    """The exact in-process DTO sent to A; repr intentionally hides text."""

    request_id: str
    subject_id: str
    conversation_id: str | None
    entry_point: str
    field_name: str
    context_ref: str
    text: str
    idempotency_key: str
    occurred_at: datetime


@dataclass(frozen=True)
class ScreeningResult:
    decision: ScreeningDecision
    risk_level: RiskDecision = RiskDecision.L0
    screening_decision_id: str | None = None
    pii_result: dict[str, Any] | None = None
    safe_template_id: str | None = None
    safety_action_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_codes: tuple[str, ...] = field(default_factory=tuple)
    rule_version: str | None = None
    model_version: str | None = None

    @property
    def is_safe(self) -> bool:
        return (
            self.decision == ScreeningDecision.allow
            and self.risk_level == RiskDecision.L0
            and isinstance(self.screening_decision_id, str)
            and bool(self.screening_decision_id)
            and isinstance(self.pii_result, dict)
            and bool(self.rule_version)
        )

    @property
    def is_blocked(self) -> bool:
        return not self.is_safe


class TextScreener(Protocol):
    async def screen_text(self, request: FreeTextSafetyRequest) -> ScreeningResult | dict[str, Any]: ...


class ContextOwnershipVerifier(Protocol):
    async def owns_context(
        self,
        *,
        subject_id: str,
        entry_point: str,
        context_ref: str,
        conversation_id: str | None,
    ) -> bool | Awaitable[bool]: ...


_CONTEXT_PATTERNS: dict[str, re.Pattern[str]] = {
    "chat.message": re.compile(r"^conversation:[^:]+$"),
    "conversation.title": re.compile(r"^(conversation:[^:]+|subject:[^:]+:new-conversation)$"),
    "feedback.comment": re.compile(r"^(response|knowledge|crisis-event|exercise-session):[^:]+$"),
    "exercise.reflection": re.compile(r"^exercise-session:[^:]+:entry:[^:]+$"),
    "emotion.correction_note": re.compile(r"^emotion-result:[^:]+$"),
    "memory.value": re.compile(r"^(memory:[^:]+|subject:[^:]+:new-memory)$"),
    "knowledge.search": re.compile(r"^subject:[^:]+:knowledge-search$"),
    "assessment.optional_note": re.compile(r"^assessment:(PHQ9|GAD7):[^:]+$"),
    "profile.nickname": re.compile(r"^(profile:[^:]+|subject:[^:]+:registration)$"),
    "guest_migration.label": re.compile(r"^guest-migration:[^:]+:item:[^:]+$"),
}
_SAFETY_ACTIONS = frozenset(
    {
        "ask_safety_question",
        "show_crisis_resources",
        "call_110",
        "call_120",
        "call_12356",
        "contact_trusted_person",
        "open_nearest_emergency",
        "recheck_safety",
    }
)


class FreeTextSafetyGateway:
    """Validate B-owned context and delegate exactly once to A.

    No screener, invalid output, timeout, or exception returns an allow decision.
    """

    def __init__(
        self,
        screener: TextScreener | None = None,
        *,
        ownership_verifier: ContextOwnershipVerifier | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("safety dependency timeout must be positive")
        self._screener = screener
        self._ownership_verifier = ownership_verifier
        self._timeout_seconds = timeout_seconds
        self._screen_call_count: dict[str, int] = {}

    async def screen(self, request: FreeTextSafetyRequest | dict[str, Any]) -> ScreeningResult:
        try:
            dto = request if isinstance(request, FreeTextSafetyRequest) else FreeTextSafetyRequest(**request)
            self._validate_request(dto)
        except (KeyError, TypeError, ValueError):
            return self._error()

        try:
            owned = await self._is_owned_context(dto)
        except Exception:
            return self._error()
        if not owned:
            return self._error()
        self._screen_call_count[dto.entry_point] = self._screen_call_count.get(dto.entry_point, 0) + 1
        if self._screener is None:
            return self._error()

        try:
            raw = await self._call_dependency(self._screener.screen_text, dto)
            result = self._coerce_result(raw)
        except Exception:
            return self._error()
        return result if self._valid_result(result) else self._error()

    @staticmethod
    def _validate_request(request: FreeTextSafetyRequest) -> None:
        entry = get_entry(request.entry_point)
        if entry is None or request.field_name != entry.field_name:
            raise ValueError("unregistered or mismatched text entry")
        if not request.request_id or not request.subject_id or not request.idempotency_key:
            raise ValueError("missing server-owned request metadata")
        if not request.text or len(request.text) > entry.max_length:
            raise ValueError("text length outside registered boundary")
        if request.occurred_at.tzinfo is None or request.occurred_at.utcoffset() != timedelta(0):
            raise ValueError("occurred_at must be UTC")
        pattern = _CONTEXT_PATTERNS[request.entry_point]
        if pattern.fullmatch(request.context_ref) is None:
            raise ValueError("context_ref mismatch")
        if request.entry_point == "chat.message":
            expected = f"conversation:{request.conversation_id}"
            if request.conversation_id is None or request.context_ref != expected:
                raise ValueError("conversation binding mismatch")

    @staticmethod
    def _coerce_result(raw: ScreeningResult | dict[str, Any]) -> ScreeningResult:
        if isinstance(raw, ScreeningResult):
            return raw
        required = {
            "decision",
            "screening_decision_id",
            "risk_decision",
            "pii_result",
            "safe_template_id",
            "safety_action_ids",
            "evidence_codes",
            "rule_version",
            "model_version",
        }
        if set(raw) != required:
            raise ValueError("free-text safety result shape mismatch")
        return ScreeningResult(
            decision=ScreeningDecision(raw["decision"]),
            risk_level=RiskDecision(raw["risk_decision"]),
            screening_decision_id=raw["screening_decision_id"],
            pii_result=raw["pii_result"],
            safe_template_id=raw["safe_template_id"],
            safety_action_ids=tuple(raw["safety_action_ids"]),
            evidence_codes=tuple(raw["evidence_codes"]),
            rule_version=raw["rule_version"],
            model_version=raw["model_version"],
        )

    @staticmethod
    def _valid_result(result: ScreeningResult) -> bool:
        if (
            not isinstance(result.decision, ScreeningDecision)
            or not isinstance(result.risk_level, RiskDecision)
            or not isinstance(result.pii_result, dict)
            or not isinstance(result.rule_version, str)
            or not result.rule_version
            or not isinstance(result.safety_action_ids, tuple)
            or not all(isinstance(item, str) for item in result.safety_action_ids)
            or not isinstance(result.evidence_codes, tuple)
            or not all(isinstance(item, str) for item in result.evidence_codes)
            or (result.safe_template_id is not None and not isinstance(result.safe_template_id, str))
            or (result.model_version is not None and not isinstance(result.model_version, str))
        ):
            return False
        if result.decision == ScreeningDecision.allow:
            return result.is_safe
        if (
            result.decision != ScreeningDecision.block
            or result.risk_level == RiskDecision.L0
            or not isinstance(result.screening_decision_id, str)
            or not result.screening_decision_id
            or not isinstance(result.safe_template_id, str)
            or not result.safe_template_id
            or not result.safety_action_ids
            or not set(result.safety_action_ids).issubset(_SAFETY_ACTIONS)
        ):
            return False
        actions = set(result.safety_action_ids)
        if result.risk_level == RiskDecision.L1:
            return {"ask_safety_question", "show_crisis_resources"}.issubset(actions)
        return {"show_crisis_resources", "call_110", "call_120", "call_12356"}.issubset(actions)

    async def _is_owned_context(self, request: FreeTextSafetyRequest) -> bool:
        subject_contexts = {
            f"subject:{request.subject_id}:new-conversation",
            f"subject:{request.subject_id}:new-memory",
            f"subject:{request.subject_id}:knowledge-search",
            f"subject:{request.subject_id}:registration",
            f"profile:{request.subject_id}",
        }
        if request.context_ref in subject_contexts:
            return True
        if self._ownership_verifier is None:
            return False
        owned = await self._call_dependency(
            self._ownership_verifier.owns_context,
            subject_id=request.subject_id,
            entry_point=request.entry_point,
            context_ref=request.context_ref,
            conversation_id=request.conversation_id,
        )
        return owned is True

    async def _call_dependency(self, function: Any, *args: Any, **kwargs: Any) -> Any:
        if not inspect.iscoroutinefunction(function):
            raise TypeError("safety dependencies must be cancellation-aware async code")
        async with asyncio.timeout(self._timeout_seconds):
            return await function(*args, **kwargs)

    @staticmethod
    def _error() -> ScreeningResult:
        return ScreeningResult(
            decision=ScreeningDecision.error,
            risk_level=RiskDecision.L1,
            safe_template_id="safety_service_unavailable",
            safety_action_ids=("show_crisis_resources",),
        )
