# ruff: noqa: E501
"""Safety REST routes — answer submission and recheck."""

from __future__ import annotations

from fastapi import APIRouter, Request

from mental_health_api.errors import AppError

router = APIRouter(prefix="/v1/safety-contexts", tags=["safety"])


@router.post("/{safety_context_id}/answers", status_code=200)
async def submit_answer(safety_context_id: str, request: Request):
    """Submit a safety confirmation answer (safe_now/not_safe/unsure)."""
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Safety answers not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.post("/{safety_context_id}/rechecks", status_code=200)
async def request_recheck(safety_context_id: str, request: Request):
    """Request a new safety confirmation question for an existing context."""
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Safety recheck not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )
