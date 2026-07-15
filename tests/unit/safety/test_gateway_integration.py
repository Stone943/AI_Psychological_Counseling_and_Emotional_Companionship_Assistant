from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from mental_health_api.safety.gateway import (
    FreeTextSafetyGateway,
    FreeTextSafetyRequest,
    RiskDecision,
    ScreeningDecision,
)


def request(**changes: object) -> FreeTextSafetyRequest:
    values = {
        "request_id": "request-1",
        "subject_id": "subject-1",
        "conversation_id": "conversation-1",
        "entry_point": "chat.message",
        "field_name": "payload.text",
        "context_ref": "conversation:conversation-1",
        "text": "synthetic text",
        "idempotency_key": "key-1",
        "occurred_at": datetime.now(UTC),
    }
    values.update(changes)
    return FreeTextSafetyRequest(**values)


class Owner:
    async def owns_context(self, **kwargs: object) -> bool:
        return kwargs["subject_id"] == "subject-1" and kwargs["context_ref"] == "conversation:conversation-1"


def allow_result() -> dict[str, object]:
    return {
        "decision": "allow",
        "risk_decision": "L0",
        "screening_decision_id": "decision-1",
        "pii_result": {},
        "safe_template_id": None,
        "safety_action_ids": [],
        "evidence_codes": [],
        "rule_version": "rules-v1",
        "model_version": None,
    }


@pytest.mark.asyncio
async def test_missing_member_a_fails_closed() -> None:
    result = await FreeTextSafetyGateway().screen(request())
    assert result.decision is ScreeningDecision.error
    assert result.is_blocked


@pytest.mark.asyncio
async def test_screener_called_exactly_once() -> None:
    class Screener:
        calls = 0

        async def screen_text(self, dto: FreeTextSafetyRequest) -> dict[str, object]:
            self.calls += 1
            assert "synthetic text" not in repr(dto)
            return allow_result()

    screener = Screener()
    result = await FreeTextSafetyGateway(screener, ownership_verifier=Owner()).screen(request())
    assert result.is_safe
    assert screener.calls == 1


@pytest.mark.asyncio
async def test_context_forgery_never_reaches_screener() -> None:
    class Screener:
        calls = 0

        async def screen_text(self, dto: FreeTextSafetyRequest) -> dict[str, object]:
            self.calls += 1
            return {}

    screener = Screener()
    result = await FreeTextSafetyGateway(screener).screen(request(context_ref="conversation:other"))
    assert result.is_blocked and result.risk_level is RiskDecision.L1
    assert screener.calls == 0


@pytest.mark.asyncio
async def test_incomplete_a_result_fails_closed() -> None:
    class Screener:
        async def screen_text(self, dto: FreeTextSafetyRequest) -> dict[str, object]:
            return {"decision": "allow", "risk_decision": "L0", "screening_decision_id": "unsafe"}

    result = await FreeTextSafetyGateway(Screener(), ownership_verifier=Owner()).screen(request())
    assert result.is_blocked


@pytest.mark.asyncio
async def test_subject_context_is_bound_without_calling_screener() -> None:
    class Screener:
        calls = 0

        async def screen_text(self, dto: FreeTextSafetyRequest) -> dict[str, object]:
            self.calls += 1
            return allow_result()

    screener = Screener()
    result = await FreeTextSafetyGateway(screener).screen(
        request(
            conversation_id=None,
            entry_point="knowledge.search",
            field_name="query",
            context_ref="subject:other:knowledge-search",
        )
    )
    assert result.is_blocked
    assert screener.calls == 0


@pytest.mark.asyncio
async def test_screener_timeout_fails_closed() -> None:
    class Screener:
        async def screen_text(self, dto: FreeTextSafetyRequest) -> dict[str, object]:
            await asyncio.Event().wait()
            return allow_result()

    result = await FreeTextSafetyGateway(Screener(), ownership_verifier=Owner(), timeout_seconds=0.01).screen(request())
    assert result.is_blocked


@pytest.mark.asyncio
async def test_assessment_context_requires_subject_ownership() -> None:
    class DenyOwner:
        calls = 0

        async def owns_context(self, **kwargs: object) -> bool:
            self.calls += 1
            return False

    class Screener:
        calls = 0

        async def screen_text(self, dto: FreeTextSafetyRequest) -> dict[str, object]:
            self.calls += 1
            return allow_result()

    owner = DenyOwner()
    screener = Screener()
    result = await FreeTextSafetyGateway(screener, ownership_verifier=owner).screen(
        request(
            conversation_id=None,
            entry_point="assessment.optional_note",
            field_name="optional_note",
            context_ref="assessment:PHQ9:submission-owned-by-other",
        )
    )
    assert result.is_blocked
    assert owner.calls == 1
    assert screener.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_field", ["safe_template_id", "safety_action_ids"])
async def test_incomplete_high_risk_result_fails_closed(missing_field: str) -> None:
    class Screener:
        async def screen_text(self, dto: FreeTextSafetyRequest) -> dict[str, object]:
            result: dict[str, object] = {
                "decision": "block",
                "risk_decision": "L3",
                "screening_decision_id": "decision-high-risk",
                "pii_result": {},
                "safe_template_id": "immediate_safety",
                "safety_action_ids": ["show_crisis_resources", "call_110", "call_120", "call_12356"],
                "evidence_codes": ["imminent-risk"],
                "rule_version": "rules-v1",
                "model_version": None,
            }
            if missing_field == "safety_action_ids":
                result[missing_field] = []
            else:
                result[missing_field] = None
            return result

    result = await FreeTextSafetyGateway(Screener(), ownership_verifier=Owner()).screen(request())
    assert result.decision is ScreeningDecision.error
    assert result.safety_action_ids == ("show_crisis_resources",)


@pytest.mark.asyncio
async def test_high_risk_block_does_not_require_allow_only_decision_id() -> None:
    class Screener:
        async def screen_text(self, dto: FreeTextSafetyRequest) -> dict[str, object]:
            return {
                "decision": "block",
                "risk_decision": "L3",
                "screening_decision_id": None,
                "pii_result": {},
                "safe_template_id": "immediate_safety",
                "safety_action_ids": ["show_crisis_resources", "call_110", "call_120", "call_12356"],
                "evidence_codes": ["imminent-risk"],
                "rule_version": "rules-v1",
                "model_version": None,
            }

    result = await FreeTextSafetyGateway(Screener(), ownership_verifier=Owner()).screen(request())

    assert result.decision is ScreeningDecision.block
    assert result.risk_level is RiskDecision.L3
    assert result.screening_decision_id is None


@pytest.mark.asyncio
async def test_high_risk_block_rejects_allow_only_decision_id() -> None:
    class Screener:
        async def screen_text(self, dto: FreeTextSafetyRequest) -> dict[str, object]:
            return {
                "decision": "block",
                "risk_decision": "L3",
                "screening_decision_id": "allow-proof-must-not-appear-on-block",
                "pii_result": {},
                "safe_template_id": "immediate_safety",
                "safety_action_ids": ["show_crisis_resources", "call_110", "call_120", "call_12356"],
                "evidence_codes": ["imminent-risk"],
                "rule_version": "rules-v1",
                "model_version": None,
            }

    result = await FreeTextSafetyGateway(Screener(), ownership_verifier=Owner()).screen(request())

    assert result.decision is ScreeningDecision.error
    assert result.screening_decision_id is None
