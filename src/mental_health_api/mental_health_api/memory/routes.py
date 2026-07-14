# ruff: noqa: E501
"""Memory REST routes — CRUD, capability, context proof."""

from __future__ import annotations

from fastapi import APIRouter, Request

from mental_health_api.errors import AppError

router = APIRouter(prefix="/v1", tags=["memory"])


@router.get("/memory-capability")
async def get_memory_capability(request: Request):
    """Return current memory mode (controlled/history_only) and policy version."""
    return {
        "mode": "history_only",
        "reason": "not_yet_implemented",
        "policy_version": "v1",
        "effective_at": "2026-07-14T00:00:00Z",
        "memory_version": "v1",
    }


@router.get("/conversations/{conversation_id}/context-proof")
async def get_context_proof(conversation_id: str, request: Request):
    """Return memory context proof without exposing memory values."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.get("/memories")
async def list_memories(request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.post("/memories", status_code=201)
async def create_memory(request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.delete("/memories/{memory_id}", status_code=204)
async def delete_memory(memory_id: str, request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )
