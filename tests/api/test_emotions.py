# ruff: noqa: E501
"""B-11 GREEN: Emotion and Memory API tests."""

from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient

from mental_health_api.app import create_app
from mental_health_api.config import Settings


def test_emotions_module_exists() -> None:
    import mental_health_api.emotions.routes  # noqa: F401


def test_memory_module_exists() -> None:
    import mental_health_api.memory.routes  # noqa: F401


def test_emotion_trends_requires_auth() -> None:
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
            resp = await client.get("/v1/emotions/trends")
            assert resp.status_code == 401

    asyncio.run(_check())


def test_memory_capability_returns_data() -> None:
    """GET /v1/memory-capability returns mode info without auth."""

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
            resp = await client.get("/v1/memory-capability")
            assert resp.status_code == 200
            data = resp.json()
            assert data["mode"] == "history_only"

    asyncio.run(_check())


def test_memory_context_proof_requires_auth() -> None:
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
            resp = await client.get("/v1/conversations/c1/context-proof")
            assert resp.status_code == 401

    asyncio.run(_check())
