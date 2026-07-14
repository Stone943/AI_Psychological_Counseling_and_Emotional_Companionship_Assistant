"""B-06 RED: Conversation idempotency, outbox atomicity, sequence invariants."""

from __future__ import annotations

from mental_health_api.database.models import Conversation


class TestConversationInvariants:
    """Conversation and Message model invariants (no DB needed)."""

    def test_message_uses_message_ordinal_not_sequence(self) -> None:
        """Message model MUST use message_ordinal, never sequence."""
        from mental_health_api.database.models import Message

        fields = {c.name for c in Message.__table__.columns}
        assert "message_ordinal" in fields
        assert "sequence" not in fields

    def test_outbox_has_sequence_with_conversation(self) -> None:
        """OutboxEvent has (conversation_id, sequence) unique constraint."""
        from mental_health_api.database.models import OutboxEvent

        fields = {c.name for c in OutboxEvent.__table__.columns}
        assert "sequence" in fields
        assert "conversation_id" in fields

    def test_conversation_has_next_event_sequence(self) -> None:
        """Conversation tracks next_event_sequence for B's sole allocation."""
        fields = {c.name for c in Conversation.__table__.columns}
        assert "next_event_sequence" in fields
        assert "persistence_mode" in fields


class TestIdempotency:
    """Idempotency key-based deduplication."""

    def test_idempotency_record_model(self) -> None:
        """Idempotency records are tracked for deduplication."""
        from mental_health_api.database.models import IdempotencyRecord

        fields = {c.name for c in IdempotencyRecord.__table__.columns}
        assert "idempotency_key" in fields
        assert "response_json" in fields
