from __future__ import annotations

import asyncio

import pytest

from mental_health_api.ai_bridge.turn_adapter import TurnAdapter, TurnUnavailableError


@pytest.mark.asyncio
async def test_missing_runner_fails_closed() -> None:
    with pytest.raises(TurnUnavailableError):
        await TurnAdapter().run_screened_turn("decision", "conversation", "subject", "key")


@pytest.mark.asyncio
async def test_rejects_a_owned_sequence() -> None:
    class Runner:
        async def run_screened_turn(self, **kwargs: object) -> dict[str, object]:
            return {
                "response_id": "response-1",
                "chunks": [
                    {
                        "response_id": "response-1",
                        "chunk_index": 0,
                        "sequence": 0,
                        "type": "response.delta",
                        "payload": {"text": "reviewed"},
                    }
                ],
            }

    with pytest.raises(TurnUnavailableError):
        await TurnAdapter(Runner()).run_screened_turn("decision", "conversation", "subject", "key")


@pytest.mark.asyncio
async def test_accepts_contiguous_reviewed_chunks() -> None:
    class Runner:
        async def run_screened_turn(self, **kwargs: object) -> dict[str, object]:
            return {
                "response_id": "response-1",
                "chunks": [
                    {
                        "response_id": "response-1",
                        "chunk_index": 0,
                        "type": "response.delta",
                        "payload": {"response_id": "response-1", "chunk_index": 0, "text": "reviewed"},
                    },
                    {
                        "response_id": "response-1",
                        "chunk_index": 1,
                        "type": "response.completed",
                        "payload": {
                            "response_id": "response-1",
                            "total_chunks": 1,
                            "response_source": "local_template",
                            "outcome": "completed",
                            "feedback_target_id": None,
                        },
                    },
                ],
            }

    result = await TurnAdapter(Runner()).run_screened_turn("decision", "conversation", "subject", "key")
    assert result["chunks"][0]["chunk_index"] == 0
    assert "sequence" not in result["chunks"][0]


@pytest.mark.asyncio
async def test_rejects_response_without_terminal_chunk() -> None:
    class Runner:
        async def run_screened_turn(self, **kwargs: object) -> dict[str, object]:
            return {
                "response_id": "response-1",
                "chunks": [
                    {
                        "response_id": "response-1",
                        "chunk_index": 0,
                        "type": "response.delta",
                        "payload": {"response_id": "response-1", "chunk_index": 0, "text": "reviewed"},
                    }
                ],
            }

    with pytest.raises(TurnUnavailableError):
        await TurnAdapter(Runner()).run_screened_turn("decision", "conversation", "subject", "key")


@pytest.mark.asyncio
async def test_runner_timeout_fails_closed() -> None:
    class Runner:
        side_effect = False

        async def run_screened_turn(self, **kwargs: object) -> dict[str, object]:
            await asyncio.sleep(0.05)
            self.side_effect = True
            return {}

    runner = Runner()
    with pytest.raises(TurnUnavailableError):
        await TurnAdapter(runner, timeout_seconds=0.01).run_screened_turn("decision", "conversation", "subject", "key")
    await asyncio.sleep(0.06)
    assert runner.side_effect is False
