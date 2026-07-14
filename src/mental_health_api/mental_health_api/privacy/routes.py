"""# ruff: noqa: E501
Privacy routes — export, deletion, account closure per PRD data rights.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from mental_health_api.errors import AppError

router = APIRouter(prefix="/v1/privacy", tags=["privacy"])


@router.post("/exports", status_code=202)
async def request_export(request: Request):
    """Request a full data export. Returns job ID for status polling."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, request: Request):
    """Check the status of a privacy job (export/deletion/closure)."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.post("/deletions", status_code=202)
async def request_deletion(request: Request):
    """Request data deletion. Triggers tombstone and 24h online cleanup."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.post("/account-closures", status_code=202)
async def close_account(request: Request):
    """Close account: revoke all tokens, schedule deletion, write tombstone."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )
