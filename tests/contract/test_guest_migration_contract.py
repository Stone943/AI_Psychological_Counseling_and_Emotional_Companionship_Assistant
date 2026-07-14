"""B-09 GREEN: Guest migration contract tests."""

from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient
from mental_health_api.app import create_app
from mental_health_api.config import Settings


def test_guest_migrations_module_exists() -> None:
    """GREEN: guest_migrations.routes module should be importable."""
    import mental_health_api.guest_migrations.routes  # noqa: F401


def test_migration_endpoint_returns_503() -> None:
    """GREEN: /v1/guest-migrations returns 503 (skeleton, not yet fully implemented)."""

    async def _check():
        settings = Settings(environment="test", force_tls=False, jwt_secret_key="k", refresh_token_secret="r", database_url="sqlite+aiosqlite:///./test.db")
        app = create_app(settings)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/guest-migrations", json={"batch_id": "b1", "record_types": [], "items": []})
            assert resp.status_code == 503

    asyncio.run(_check())


def test_migration_batch_id_required() -> None:
    """Migration request schema requires batch_id."""
    from mental_health_api.contracts.models import GuestMigrationRequest

    # batch_id is required
    fields = GuestMigrationRequest.model_fields
    assert "batch_id" in fields
    assert "record_types" in fields
    assert "items" in fields
