"""Turn adapter — bridges B's safety gateway, consent, and provider policy into A's run_screened_turn."""

from __future__ import annotations


class TurnAdapter:
    """Coordinates a single conversation turn: screen → consent/policy gates → AI generation → output review → outbox.

    All gates and orchestration run within the same single-worker FastAPI process.
    No independent AI orchestration service or RPC.
    """

    def __init__(self) -> None:
        self._turn_counter = 0

    async def run_screened_turn(
        self, screening_decision_id: str, conversation_id: str, subject_id: str, message_text: str
    ) -> dict:
        """Execute a turn after B-08 screening passed (L0).

        Order: proof consume=1 → policy read=1 → consent read=1 (if approved) → dispatch=1 (if granted).
        Returns structured response chunks for ReviewedStreamChunk → ServerEventEnvelope mapping.
        """
        self._turn_counter += 1
        # Stub: returns deterministic local response
        return {
            "response_id": f"resp_{self._turn_counter}",
            "chunks": [{"chunk_index": 0, "text": "I hear you. Can you tell me more about what you're experiencing?"}],
            "outcome": "completed",
            "response_source": "local_template",
        }
