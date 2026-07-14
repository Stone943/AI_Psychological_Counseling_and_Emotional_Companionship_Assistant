"""# ruff: noqa: E501
Admin routes — TOTP MFA, content management, risk review, audit. No Web UI.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from mental_health_api.errors import AppError

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.post("/mfa/enroll", status_code=200)
async def enroll_mfa(request: Request):
    """Begin TOTP enrollment. Returns seed (shown once) and provisioning URI."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Admin authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.post("/mfa/confirm", status_code=200)
async def confirm_mfa(request: Request):
    """Confirm TOTP enrollment with a valid code."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Admin authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.post("/reauth", status_code=200)
async def reauth(request: Request):
    """Password + TOTP → 5-minute reauth token for sensitive operations."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Admin authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.get("/audit")
async def query_audit(request: Request):
    """Query audit log entries (no psychological content)."""
    raise AppError(
        code="FORBIDDEN", message="Insufficient permissions", http_status=403, retryable=False, client_action="none"
    )
