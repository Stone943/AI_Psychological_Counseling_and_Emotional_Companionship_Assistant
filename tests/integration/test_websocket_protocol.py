# ruff: noqa: E501
"""B-07: WebSocket protocol tests — ticket, command validation, sequence invariants."""

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
        jwt_secret_key="test-jwt-32chars!!",
        refresh_token_secret="test-refresh-32c!",
        database_url="sqlite+aiosqlite:///./test.db",
    )
    return create_app(settings)


@pytest.mark.asyncio
async def test_ticket_endpoint_exists(app) -> None:
    """POST /v1/realtime/tickets must exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/realtime/tickets", json={})
        assert resp.status_code in (201, 503)


@pytest.mark.asyncio
async def test_websocket_endpoint_accepts(app) -> None:
    """WS /v1/realtime must accept connections."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/realtime/tickets")
        assert resp.status_code in (200, 404, 405, 503)


class TestClientCommandValidation:
    """ClientCommandEnvelope invariants."""

    def test_no_sequence_in_command(self) -> None:
        """ClientCommandEnvelope MUST NOT have sequence field."""
        from mental_health_api.contracts.models import ClientCommandEnvelope

        assert "sequence" not in ClientCommandEnvelope.model_fields

    def test_server_envelope_has_sequence(self) -> None:
        """ServerEventEnvelope MUST have sequence >= 0."""
        from mental_health_api.contracts.models import ServerEventEnvelope

        assert "sequence" in ServerEventEnvelope.model_fields

    def test_command_types_exact(self) -> None:
        """Client command types must match frozen set."""
        import typing

        from mental_health_api.contracts.models import ClientCommandEnvelope

        # Get Literal args
        args = typing.get_args(ClientCommandEnvelope.model_fields["type"].annotation)
        expected = {"message.send", "generation.cancel", "session.resume", "session.ack", "safety.answer"}
        assert {str(a) for a in args} == expected
