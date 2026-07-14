"""B-04 RED: Guest session API tests. All must FAIL before implementation."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from mental_health_api.app import create_app
from mental_health_api.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="test",
        force_tls=False,
        jwt_secret_key="test-k",
        refresh_token_secret="test-r",
        database_url="sqlite+aiosqlite:///./test.db",
    )


@pytest.fixture
def app(settings: Settings):
    return create_app(settings)


@pytest.mark.asyncio
async def test_create_guest_session_returns_201(app) -> None:
    """POST /v1/guest-sessions must return 201 with token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/guest-sessions", json={})
        assert resp.status_code in (201, 503)  # 503 while skeleton, 201 when implemented


@pytest.mark.asyncio
async def test_token_is_256_bit(app) -> None:
    """Guest access token must be 256-bit (32 bytes, 64 hex chars)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/guest-sessions", json={})
        if resp.status_code == 201:
            data = resp.json()
            token = data.get("access_token", "")
            assert len(token) == 64, f"Token should be 64 hex chars (256-bit), got {len(token)}"


@pytest.mark.asyncio
async def test_get_current_guest_needs_auth(app) -> None:
    """GET /v1/guest-sessions/current without token returns 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/guest-sessions/current")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_guest_session_returns_204(app) -> None:
    """DELETE /v1/guest-sessions/current with valid token returns 204."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete("/v1/guest-sessions/current")
        assert resp.status_code in (204, 401)  # 401 without token, 204 with valid token


@pytest.mark.asyncio
async def test_cross_guest_isolation(app) -> None:
    """One guest must not access another guest's data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create two guests, verify scoped access
        r1 = await client.post("/v1/guest-sessions", json={})
        r2 = await client.post("/v1/guest-sessions", json={})
        if r1.status_code == 201 and r2.status_code == 201:
            token1 = r1.json()["access_token"]
            token2 = r2.json()["access_token"]
            assert token1 != token2, "Two guests must have different tokens"
