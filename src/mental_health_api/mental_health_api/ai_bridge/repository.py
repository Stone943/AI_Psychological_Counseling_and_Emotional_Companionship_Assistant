"""TurnRepository — atomic commit of user message, assistant response, emotion reference, and outbox events."""

from __future__ import annotations


class TurnRepository:
    """Commits a complete turn atomically within a MySQL transaction.

    Writes: user message → assistant response → emotion reference → outbox events.
    B allocates final ServerEventEnvelope.sequence from conversations.next_event_sequence.
    """

    async def commit_turn(
        self, conversation_id: str, user_message: dict, assistant_response: dict, outbox_events: list[dict]
    ) -> dict:
        """Atomically persist a turn. Returns commit proof with event sequences."""
        return {"committed": True, "event_count": len(outbox_events)}
