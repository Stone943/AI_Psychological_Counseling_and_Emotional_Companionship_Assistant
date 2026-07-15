"""In-process adapter for Member A's screened turn orchestrator."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Protocol

from mental_health_api.consents.ai_adapter import ConsentSnapshotPort
from mental_health_api.contracts.models import ResponseBlockedPayload, ResponseCompletedPayload, ResponseDeltaPayload
from mental_health_api.provider_policy.adapter import ProviderProcessingPolicyPort


class TurnUnavailableError(RuntimeError):
    """The screened turn cannot run safely; callers must fail closed."""


@dataclass(frozen=True)
class ReviewedChunk:
    response_id: str
    chunk_index: int
    type: str
    payload: dict[str, Any]


class ScreenedTurnRunner(Protocol):
    async def run_screened_turn(
        self,
        *,
        screening_decision_id: str,
        conversation_id: str,
        subject_id: str,
        idempotency_key: str,
        provider_policy_port: ProviderProcessingPolicyPort,
        consent_snapshot_port: ConsentSnapshotPort,
    ) -> Any: ...


class TurnAdapter:
    """Pass an unconsumed A decision to A in the same process.

    The adapter never receives the raw message. A's in-memory DecisionStore owns
    the screened text and the provider adapter owns proof/policy/consent order.
    """

    def __init__(
        self,
        runner: ScreenedTurnRunner | None = None,
        *,
        provider_policy_port: ProviderProcessingPolicyPort | None = None,
        consent_snapshot_port: ConsentSnapshotPort | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("AI turn timeout must be positive")
        self._runner = runner
        self._provider_policy_port = provider_policy_port or ProviderProcessingPolicyPort()
        self._consent_snapshot_port = consent_snapshot_port or ConsentSnapshotPort()
        self._timeout_seconds = timeout_seconds

    async def run_screened_turn(
        self,
        screening_decision_id: str,
        conversation_id: str,
        subject_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if not all((screening_decision_id, conversation_id, subject_id, idempotency_key)):
            raise TurnUnavailableError("screened turn metadata is incomplete")
        if self._runner is None:
            raise TurnUnavailableError("Member A screened-turn runner is unavailable")

        try:
            async with asyncio.timeout(self._timeout_seconds):
                call: Any = self._runner.run_screened_turn
                if not inspect.iscoroutinefunction(call):
                    raise TurnUnavailableError("screened-turn runner must be cancellation-aware async code")
                kwargs = {
                    "screening_decision_id": screening_decision_id,
                    "conversation_id": conversation_id,
                    "subject_id": subject_id,
                    "idempotency_key": idempotency_key,
                    "provider_policy_port": self._provider_policy_port,
                    "consent_snapshot_port": self._consent_snapshot_port,
                }
                raw = await call(**kwargs)
            return self._validate_response(raw)
        except TurnUnavailableError:
            raise
        except Exception as exc:
            raise TurnUnavailableError("screened turn failed closed") from exc

    @classmethod
    def _validate_response(cls, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict) or set(raw) != {"response_id", "chunks"} or not raw.get("response_id"):
            raise TurnUnavailableError("invalid screened-turn response")
        chunks_raw = raw.get("chunks")
        if not isinstance(chunks_raw, list) or not chunks_raw:
            raise TurnUnavailableError("screened-turn response has no reviewed chunks")
        chunks = [cls._validate_chunk(chunk, raw["response_id"]) for chunk in chunks_raw]
        indexes = [chunk.chunk_index for chunk in chunks]
        if indexes != list(range(len(chunks))):
            raise TurnUnavailableError("reviewed chunks are not contiguous")
        terminal = [chunk for chunk in chunks if chunk.type in {"response.completed", "response.blocked"}]
        if len(terminal) != 1 or chunks[-1] != terminal[0]:
            raise TurnUnavailableError("reviewed chunks require one final terminal event")
        if terminal[0].type == "response.blocked" and len(chunks) != 1:
            raise TurnUnavailableError("blocked responses must not expose partial deltas")
        terminal_payload = terminal[0].payload
        return {
            "response_id": raw["response_id"],
            "chunks": [
                {
                    "response_id": chunk.response_id,
                    "chunk_index": chunk.chunk_index,
                    "type": chunk.type,
                    "payload": chunk.payload,
                }
                for chunk in chunks
            ],
            "outcome": terminal_payload["outcome"],
            "response_source": terminal_payload.get("response_source"),
        }

    @staticmethod
    def _validate_chunk(raw: Any, response_id: str) -> ReviewedChunk:
        if not isinstance(raw, dict) or set(raw) != {"response_id", "chunk_index", "type", "payload"}:
            raise TurnUnavailableError("A must not allocate server event sequence")
        if raw.get("response_id") != response_id:
            raise TurnUnavailableError("chunk response binding mismatch")
        event_type = raw.get("type")
        if event_type not in {"response.delta", "response.completed", "response.blocked"}:
            raise TurnUnavailableError("unknown reviewed chunk type")
        if not isinstance(raw.get("chunk_index"), int) or raw["chunk_index"] < 0:
            raise TurnUnavailableError("invalid chunk index")
        if not isinstance(raw.get("payload"), dict):
            raise TurnUnavailableError("reviewed chunk payload must be structured")
        payload = TurnAdapter._validate_payload(event_type, raw["payload"], response_id, raw["chunk_index"])
        return ReviewedChunk(
            response_id=response_id,
            chunk_index=raw["chunk_index"],
            type=event_type,
            payload=payload,
        )

    @staticmethod
    def _validate_payload(
        event_type: str, payload: dict[str, Any], response_id: str, chunk_index: int
    ) -> dict[str, Any]:
        if event_type == "response.delta":
            delta = ResponseDeltaPayload.model_validate(payload)
            if delta.response_id != response_id or delta.chunk_index != chunk_index or not delta.text:
                raise TurnUnavailableError("delta payload binding mismatch")
            return delta.model_dump(mode="json")
        if event_type == "response.completed":
            completed = ResponseCompletedPayload.model_validate(payload)
            if (
                completed.response_id != response_id
                or completed.total_chunks != chunk_index
                or not completed.response_source
                or not completed.outcome
            ):
                raise TurnUnavailableError("completed payload binding mismatch")
            return completed.model_dump(mode="json")
        blocked = ResponseBlockedPayload.model_validate(payload)
        if (
            blocked.response_id != response_id
            or not blocked.outcome
            or not blocked.template_id
            or not blocked.public_error_code
        ):
            raise TurnUnavailableError("blocked payload binding mismatch")
        return blocked.model_dump(mode="json")
