# ruff: noqa: E501
"""Conversation REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from mental_health_api.errors import AppError

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


@router.post("", status_code=201)
async def create_conversation(request: Request):
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Conversations not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.get("")
async def list_conversations(request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str, request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )
