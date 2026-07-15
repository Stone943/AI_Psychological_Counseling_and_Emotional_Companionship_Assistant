# ruff: noqa: B008, TC001, TC002
"""Guest session REST routes."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from mental_health_api.config import Settings
from mental_health_api.database.engine import get_session
from mental_health_api.errors import AppError
from mental_health_api.guests.contracts import GuestSessionResponse, GuestSessionStatus
from mental_health_api.guests.service import GuestService

router = APIRouter(prefix="/v1/guest-sessions", tags=["guests"])


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise _invalid_guest()
    return authorization.removeprefix("Bearer ").strip()


def _device_key(value: str | None) -> str:
    if value is None:
        raise _invalid_guest()
    try:
        GuestService.validate_device_key(value)
    except ValueError as exc:
        raise _invalid_guest() from exc
    return value


def _invalid_guest() -> AppError:
    return AppError(
        code="GUEST_SESSION_INVALID",
        message="No active guest session",
        http_status=401,
        retryable=False,
        client_action="create_guest_session",
    )


def _guest_persistence_unavailable() -> AppError:
    return AppError(
        code="SERVICE_UNAVAILABLE",
        message="Guest persistence unavailable",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.post("", status_code=201, response_model=GuestSessionResponse)
async def create_guest_session(
    x_device_key: str | None = Header(default=None, alias="X-Device-Key"),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> GuestSessionResponse:
    try:
        subject, db_session, token = await GuestService(settings, session).create_guest(_device_key(x_device_key))
    except SQLAlchemyError as exc:
        await session.rollback()
        raise _guest_persistence_unavailable() from exc
    return GuestSessionResponse(
        guest_subject_id=subject.guest_subject_id,
        access_token=token,
        expires_at=db_session.expires_at,
        scopes=db_session.scopes.split(),
    )


@router.get("/current", response_model=GuestSessionStatus)
async def get_current_guest(
    authorization: str | None = Header(default=None),
    x_device_key: str | None = Header(default=None, alias="X-Device-Key"),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> GuestSessionStatus:
    try:
        current = await GuestService(settings, session).verify_token(_bearer(authorization), _device_key(x_device_key))
    except SQLAlchemyError as exc:
        await session.rollback()
        raise _guest_persistence_unavailable() from exc
    if current is None:
        raise _invalid_guest()
    return GuestSessionStatus(
        guest_subject_id=current.guest_subject_id,
        created_at=current.created_at,
        expires_at=current.expires_at,
        scopes=current.scopes.split(),
    )


@router.delete("/current", status_code=204)
async def delete_current_guest(
    authorization: str | None = Header(default=None),
    x_device_key: str | None = Header(default=None, alias="X-Device-Key"),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        revoked = await GuestService(settings, session).revoke(_bearer(authorization), _device_key(x_device_key))
    except SQLAlchemyError as exc:
        await session.rollback()
        raise _guest_persistence_unavailable() from exc
    if revoked is None:
        raise _invalid_guest()
    return Response(status_code=204)
