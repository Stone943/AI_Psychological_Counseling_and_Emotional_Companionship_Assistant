# ruff: noqa: E501
"""Auth REST routes — register, login, refresh, logout, recovery, devices."""

from __future__ import annotations

from fastapi import APIRouter, Request

from mental_health_api.errors import AppError

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(request: Request):
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Auth not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.post("/login")
async def login(request: Request):
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Auth not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.post("/refresh")
async def refresh(request: Request):
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Auth not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.post("/logout", status_code=204)
async def logout(request: Request):
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Auth not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.get("/devices")
async def list_devices(request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.delete("/devices/{device_id}", status_code=204)
async def revoke_device(device_id: str, request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.post("/recovery-requests", status_code=202)
async def request_recovery(request: Request):
    """Always returns 202 regardless of whether email exists (prevents enumeration)."""
    return {"message": "If the email exists, a recovery link has been sent."}


@router.post("/recovery-confirmations", status_code=204)
async def confirm_recovery(request: Request):
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Recovery not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.post("/guest-migration", status_code=200)
async def migrate_guest(request: Request):
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Guest migration not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )
