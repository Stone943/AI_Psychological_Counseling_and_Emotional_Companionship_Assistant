# ruff: noqa: E501
"""Emotion REST routes — results, corrections, trends."""

from __future__ import annotations

from fastapi import APIRouter, Request

from mental_health_api.errors import AppError

router = APIRouter(prefix="/v1/emotions", tags=["emotions"])


@router.get("/trends")
async def get_trends(request: Request):
    """Get emotion trends (day/week aggregation)."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.post("/{emotion_result_id}/corrections", status_code=201)
async def correct_emotion(emotion_result_id: str, request: Request):
    """Submit a user correction for an emotion result."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )
