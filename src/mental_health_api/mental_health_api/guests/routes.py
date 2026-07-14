# ruff: noqa: E501, B008
"""Guest session REST routes — POST/GET/DELETE /v1/guest-sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Request, Response

from mental_health_api.errors import AppError

if TYPE_CHECKING:
    from mental_health_api.config import Settings
    from mental_health_api.guests.contracts import GuestSessionResponse

router = APIRouter(prefix="/v1/guest-sessions", tags=["guests"])


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


@router.post("", status_code=201)
async def create_guest_session(settings: Settings = Depends(get_settings)) -> GuestSessionResponse:
    """Create a temporary guest identity and return a 256-bit opaque access token."""
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Guest sessions not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.get("/current")
async def get_current_guest(request: Request):
    """Return the current guest session status."""
    raise AppError(
        code="GUEST_SESSION_INVALID",
        message="No active guest session",
        http_status=401,
        retryable=False,
        client_action="create_guest_session",
    )


@router.delete("/current")
async def delete_current_guest(request: Request):
    """Revoke the current guest session and schedule cleanup."""
    return Response(status_code=204)
