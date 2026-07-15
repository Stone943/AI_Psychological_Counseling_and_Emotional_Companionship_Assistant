"""B-04 guest session API lifecycle tests over an isolated SQLite schema."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from mental_health_api.app import create_app
from mental_health_api.config import Settings
from mental_health_api.database.base import Base


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        environment="test",
        force_tls=False,
        jwt_secret_key="test-k",
        refresh_token_secret="test-r",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'guest-api.db'}",
    )


@pytest_asyncio.fixture
async def app(settings: Settings):
    application = create_app(settings)
    async with application.state.database_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield application
    await application.state.database_engine.dispose()


@pytest.mark.asyncio
async def test_create_guest_session_returns_201(app) -> None:
    """POST /v1/guest-sessions must return 201 with token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/guest-sessions", json={}, headers={"X-Device-Key": "d" * 64})
        assert resp.status_code == 201


@pytest.mark.asyncio
async def test_token_is_256_bit(app) -> None:
    """Guest access token must be 256-bit (32 bytes, 64 hex chars)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/guest-sessions", json={}, headers={"X-Device-Key": "d" * 64})
        assert resp.status_code == 201
        token = resp.json().get("access_token", "")
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
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_guest_lifecycle(app) -> None:
    device_key = "a" * 64
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/v1/guest-sessions", headers={"X-Device-Key": device_key})
        assert created.status_code == 201
        headers = {
            "Authorization": f"Bearer {created.json()['access_token']}",
            "X-Device-Key": device_key,
        }
        assert (await client.get("/v1/guest-sessions/current", headers=headers)).status_code == 200
        assert (await client.delete("/v1/guest-sessions/current", headers=headers)).status_code == 204
        assert (await client.get("/v1/guest-sessions/current", headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_cross_guest_isolation(app) -> None:
    """One guest must not access another guest's data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create two guests, verify scoped access
        r1 = await client.post("/v1/guest-sessions", json={}, headers={"X-Device-Key": "1" * 64})
        r2 = await client.post("/v1/guest-sessions", json={}, headers={"X-Device-Key": "2" * 64})
        assert r1.status_code == r2.status_code == 201
        token1 = r1.json()["access_token"]
        token2 = r2.json()["access_token"]
        assert token1 != token2, "Two guests must have different tokens"
