"""Crisis resources remain available but degraded without a signed bundle."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from mental_health_api.app import create_app
from mental_health_api.config import Settings


@pytest.mark.asyncio
async def test_missing_bundle_returns_degraded_builtin_numbers(tmp_path) -> None:
    app = create_app(Settings(environment="test", force_tls=False, content_dir=tmp_path, jwt_secret_key="test-secret"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/crisis-resources")

    assert response.status_code == 200
    payload = response.json()
    assert payload["resource_status"] == "degraded"
    assert payload["degraded_reason"] == "bundle_missing"
    assert {row["number"] for row in payload["resources"]} >= {"110", "120", "12356"}


@pytest.mark.asyncio
async def test_unknown_locale_never_relabels_china_resources(tmp_path) -> None:
    app = create_app(Settings(environment="test", force_tls=False, content_dir=tmp_path, jwt_secret_key="test-secret"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/crisis-resources?region=US&language=en")

    payload = response.json()
    assert payload["resource_status"] == "degraded"
    assert payload["degraded_reason"] == "bundle_missing"
    assert payload["region"] == "CN-mainland"
    assert payload["language"] == "zh-CN"
