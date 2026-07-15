"""B-08: Verify 10 free-text entry points match PRD 14.1."""

from __future__ import annotations

from mental_health_api.safety.free_text_registry import ENTRIES, is_registered


def test_exact_ten_entries() -> None:
    """v1 must have exactly 10 entry points."""
    assert len(ENTRIES) == 10, f"Expected 10, got {len(ENTRIES)}"


def test_all_required_entries() -> None:
    """All 10 entries from PRD 14.1 must be present."""
    required = {
        "chat.message",
        "conversation.title",
        "feedback.comment",
        "exercise.reflection",
        "emotion.correction_note",
        "memory.value",
        "knowledge.search",
        "assessment.optional_note",
        "profile.nickname",
        "guest_migration.label",
    }
    assert set(ENTRIES.keys()) == required


def test_is_registered() -> None:
    assert is_registered("chat.message") is True
    assert is_registered("nonexistent") is False


def test_context_ref_grammar() -> None:
    """Context ref builder produces correct grammar for each entry point."""
    from mental_health_api.safety.context_ref import build_context_ref

    assert build_context_ref("chat.message", conversation_id="conv-1") == "conversation:conv-1"
    assert build_context_ref("knowledge.search", subject_id="subj-1") == "subject:subj-1:knowledge-search"
    assert build_context_ref("emotion.correction_note", emotion_result_id="em-1") == "emotion-result:em-1"
    assert build_context_ref("memory.value", subject_id="s", memory_id="m-1") == "memory:m-1"
    assert build_context_ref("memory.value", subject_id="s") == "subject:s:new-memory"
    assert build_context_ref("profile.nickname", subject_id="u-1") == "profile:u-1"


def test_screening_result() -> None:
    """ScreeningResult correctly identifies safe vs blocked states."""
    from mental_health_api.safety.gateway import RiskDecision, ScreeningDecision, ScreeningResult

    safe = ScreeningResult(
        ScreeningDecision.allow,
        RiskDecision.L0,
        screening_decision_id="decision-1",
        pii_result={},
        rule_version="rules-v1",
    )
    assert safe.is_safe is True
    assert safe.is_blocked is False

    blocked = ScreeningResult(ScreeningDecision.block, RiskDecision.L2)
    assert blocked.is_safe is False
    assert blocked.is_blocked is True

    error = ScreeningResult(ScreeningDecision.error, RiskDecision.L0)
    assert error.is_blocked is True
