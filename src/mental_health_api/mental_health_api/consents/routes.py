# ruff: noqa: E501
"""Consent REST routes — GET/POST /v1/consents."""

from __future__ import annotations

from fastapi import APIRouter, Request

from mental_health_api.consents.service import ConsentService
from mental_health_api.errors import AppError

router = APIRouter(prefix="/v1/consents", tags=["consents"])

_service = ConsentService()


@router.get("")
async def list_consents(request: Request) -> list[dict]:
    """List all consent types and their current status for the authenticated subject."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.post("/{consent_type}/grant", status_code=200)
async def grant_consent(consent_type: str, request: Request) -> dict:
    """Grant a specific consent type."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.post("/{consent_type}/withdraw", status_code=200)
async def withdraw_consent(consent_type: str, request: Request) -> dict:
    """Withdraw a specific consent type."""
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )
