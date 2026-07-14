# ruff: noqa: E501
"""Feedback REST routes — submit and retrieve feedback."""

from __future__ import annotations

from fastapi import APIRouter, Request

from mental_health_api.errors import AppError

router = APIRouter(prefix="/v1/feedback", tags=["feedback"])


@router.post("", status_code=201)
async def submit_feedback(request: Request):
    """Submit feedback on AI response, knowledge article, or crisis event."""
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Feedback not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.get("/{feedback_id}")
async def get_feedback(feedback_id: str, request: Request):
    """Retrieve feedback status. Only accessible by the submitting subject."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )
