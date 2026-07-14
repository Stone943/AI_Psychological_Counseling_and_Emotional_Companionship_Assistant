"""Tests for FastAPI application factory and health endpoint."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from mental_health_api.app import create_app
from mental_health_api.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Test settings with SQLite."""
    return Settings(
        environment="test",
        debug=True,
        database_url="sqlite+aiosqlite:///./test_mental_health.db",
        redis_url="redis://localhost:6379/0",
        encryption_key_ref="test-key",
        jwt_secret_key="test-secret",
        refresh_token_secret="test-refresh",
        force_tls=False,
        cors_origins=["*"],
    )


@pytest.fixture
def app(settings: Settings):
    """Create test app."""
    return create_app(settings)


@pytest.mark.asyncio
async def test_health_endpoint(app) -> None:
    """Health endpoint returns 200 and status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
async def test_app_has_settings(app) -> None:
    """App stores settings in state."""
    assert app.state.settings is not None
    assert app.state.settings.environment == "test"


@pytest.mark.asyncio
async def test_unknown_route_returns_404(app) -> None:
    """Unknown routes return 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/nonexistent")
        assert resp.status_code == 404
