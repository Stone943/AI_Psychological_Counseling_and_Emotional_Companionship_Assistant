"""B-18: Verify all 10 free-text entry points are registered and no route bypass exists."""

from __future__ import annotations

import pytest
from mental_health_api.safety.free_text_registry import ENTRIES, is_registered


class TestTenEntryPoints:
    """All 10 entry points from PRD 14.1 must be present and no extras."""

    def test_exact_count(self) -> None:
        assert len(ENTRIES) == 10

    @pytest.mark.parametrize(
        "entry_point",
        [
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
        ],
    )
    def test_each_entry_registered(self, entry_point: str) -> None:
        assert is_registered(entry_point), f"Entry point {entry_point} must be registered"

    def test_no_eleventh_entry(self) -> None:
        """Any unregistered free-text field must fail."""
        assert not is_registered("unknown.entry")
        assert not is_registered("admin.free_text")  # No 11th entry

    def test_each_entry_has_max_length(self) -> None:
        for ep, entry in ENTRIES.items():
            assert entry.max_length > 0, f"{ep} must have max_length > 0"
            assert entry.field_name, f"{ep} must have field_name"


class TestContextRefGrammar:
    """Context ref builders must produce correct grammar for all entries."""

    def test_chat_message_grammar(self) -> None:
        from mental_health_api.safety.context_ref import build_context_ref
        assert build_context_ref("chat.message", conversation_id="c1") == "conversation:c1"

    def test_knowledge_search_grammar(self) -> None:
        from mental_health_api.safety.context_ref import build_context_ref
        assert build_context_ref("knowledge.search", subject_id="s1") == "subject:s1:knowledge-search"

    def test_assessment_grammar(self) -> None:
        from mental_health_api.safety.context_ref import build_context_ref
        assert build_context_ref("assessment.optional_note", scale="PHQ9", version="v1") == "assessment:PHQ9:v1"

    def test_guest_migration_grammar(self) -> None:
        from mental_health_api.safety.context_ref import build_context_ref
        assert build_context_ref("guest_migration.label", batch_id="b1", item_id="i1") == "guest-migration:b1:item:i1"


class TestFailClosed:
    """Safety gateway must fail closed on any dependency failure."""

    def test_screening_result_blocked(self) -> None:
        from mental_health_api.safety.gateway import RiskDecision, ScreeningDecision, ScreeningResult

        error_result = ScreeningResult(ScreeningDecision.error, RiskDecision.L0)
        assert error_result.is_blocked is True
        assert error_result.is_safe is False

        blocked_result = ScreeningResult(ScreeningDecision.block, RiskDecision.L3)
        assert blocked_result.is_blocked is True

    def test_unknown_entry_not_registered(self) -> None:
        """Unknown entry points must not pass is_registered."""
        assert not is_registered("admin.console")
        assert not is_registered("")
        assert not is_registered("chat.private_message")  # Only chat.message is valid
