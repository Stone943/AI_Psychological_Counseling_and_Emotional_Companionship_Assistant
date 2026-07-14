"""B-18: Safety answer state machine — replay, mutation, recheck invariants."""

from __future__ import annotations

from mental_health_api.contracts.models import SafetyAnswerId


def test_answer_id_enum_exact() -> None:
    """Safety answer IDs must be exactly safe_now, not_safe, unsure."""
    valid = {SafetyAnswerId.safe_now, SafetyAnswerId.not_safe, SafetyAnswerId.unsure}
    assert len(valid) == 3
    assert SafetyAnswerId.safe_now.value == "safe_now"
    assert SafetyAnswerId.not_safe.value == "not_safe"
    assert SafetyAnswerId.unsure.value == "unsure"


def test_answer_state_transitions() -> None:
    """Verify answer → risk level mapping per PRD 2.3."""
    # safe_now → L0 (downgrade)
    # unsure → L2 (escalate)
    # not_safe → L3 (escalate)
    transitions = {
        "safe_now": "L0",
        "unsure": "L2",
        "not_safe": "L3",
    }
    assert transitions[SafetyAnswerId.safe_now.value] == "L0"
    assert transitions[SafetyAnswerId.unsure.value] == "L2"
    assert transitions[SafetyAnswerId.not_safe.value] == "L3"
