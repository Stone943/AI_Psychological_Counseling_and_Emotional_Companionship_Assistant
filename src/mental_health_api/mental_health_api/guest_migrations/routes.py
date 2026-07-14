# ruff: noqa: E501
"""Guest migration REST routes — preview, create, status."""

from __future__ import annotations

from fastapi import APIRouter, Request

from mental_health_api.errors import AppError

router = APIRouter(prefix="/v1/guest-migrations", tags=["guest-migrations"])


@router.post("", status_code=202)
async def create_migration(request: Request):
    """Initiate a guest-to-account migration with per-item safety screening."""
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Guest migration not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.get("/{batch_id}")
async def get_migration_status(batch_id: str, request: Request):
    """Check the status of a guest migration batch."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )
