"""# ruff: noqa: E501
Exercise REST routes — catalog, sessions, history, feedback.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from mental_health_api.errors import AppError

router = APIRouter(prefix="/v1/exercises", tags=["exercises"])


@router.get("")
async def list_exercises(request: Request):
    """List available exercise definitions (published only)."""
    return {"exercises": []}


@router.get("/{exercise_id}")
async def get_exercise(exercise_id: str, request: Request):
    raise AppError(
        code="NOT_FOUND", message="Exercise not found", http_status=404, retryable=False, client_action="none"
    )


@router.post("/sessions", status_code=201)
async def start_session(request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.post("/sessions/{session_id}/pause", status_code=200)
async def pause_session(session_id: str, request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.post("/sessions/{session_id}/resume", status_code=200)
async def resume_session(session_id: str, request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.post("/sessions/{session_id}/complete", status_code=200)
async def complete_session(session_id: str, request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )
