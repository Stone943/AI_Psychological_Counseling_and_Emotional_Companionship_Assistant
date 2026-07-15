# ruff: noqa: E501
"""B-10 GREEN: Feedback API tests."""

from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient

from mental_health_api.app import create_app
from mental_health_api.config import Settings


def test_feedback_module_exists() -> None:
    """GREEN: feedback routes module should be importable."""
    import mental_health_api.feedback.routes  # noqa: F401


def test_feedback_endpoint_returns_503() -> None:
    """GREEN: /v1/feedback returns 503 (skeleton)."""

    async def _check():
        settings = Settings(
            environment="test",
            force_tls=False,
            jwt_secret_key="k",
            refresh_token_secret="r",
            database_url="sqlite+aiosqlite:///./test.db",
        )
        app = create_app(settings)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/feedback", json={"target_id": "t1", "target_type": "ai_response", "category": "helpful"}
            )
            assert resp.status_code == 503

    asyncio.run(_check())


def test_turn_adapter_exists() -> None:
    """GREEN: TurnAdapter should be importable."""
    from mental_health_api.ai_bridge.turn_adapter import TurnAdapter

    adapter = TurnAdapter()
    assert adapter is not None


def test_feedback_discriminated_union() -> None:
    """Feedback categories must match PRD spec."""
    from mental_health_api.contracts.models import FeedbackCategory, FeedbackTarget

    assert FeedbackTarget.ai_response.value == "ai_response"
    assert FeedbackCategory.helpful.value == "helpful"
    assert FeedbackCategory.false_positive.value == "false_positive"
