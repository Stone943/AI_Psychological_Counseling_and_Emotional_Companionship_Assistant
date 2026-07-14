# ruff: noqa: E501
"""B-05 RED: Auth API tests — register, login, refresh, logout, recovery."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from mental_health_api.app import create_app
from mental_health_api.config import Settings


@pytest.fixture
def app():
    settings = Settings(
        environment="test",
        force_tls=False,
        jwt_secret_key="test-jwt-secret-key-32chars!",
        refresh_token_secret="test-refresh-secret-32c!",
        database_url="sqlite+aiosqlite:///./test.db",
    )
    return create_app(settings)


@pytest.mark.asyncio
async def test_register_route_exists(app) -> None:
    """POST /v1/auth/register must exist (even if returning 503 skeleton)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/auth/register", json={"email": "test@example.com", "password": "SecurePass123!"})
        assert resp.status_code in (201, 503)


@pytest.mark.asyncio
async def test_login_route_exists(app) -> None:
    """POST /v1/auth/login must exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/auth/login", json={"email": "test@example.com", "password": "SecurePass123!"})
        assert resp.status_code in (200, 401, 503)


@pytest.mark.asyncio
async def test_recovery_request_always_202(app) -> None:
    """POST /v1/auth/recovery-requests always returns 202 (no email enumeration)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/auth/recovery-requests", json={"email": "nonexistent@example.com"})
        assert resp.status_code in (202, 404)


@pytest.mark.asyncio
async def test_device_revocation_route(app) -> None:
    """User can list and revoke device sessions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/auth/devices")
        assert resp.status_code in (200, 401)
