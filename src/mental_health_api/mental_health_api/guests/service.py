# ruff: noqa: TC001, TC002
"""Persistent guest session lifecycle."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from mental_health_api.config import Settings
from mental_health_api.database.models import GuestSession, GuestSubject


class GuestService:
    TOKEN_BYTES = 32
    TTL = timedelta(hours=24)
    SCOPES = ("onboarding", "register", "safety_gate", "realtime_ticket", "core_functions")

    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self._session = session
        # Derive a fixed-width HMAC key so test fixtures may use short synthetic
        # secrets while production Settings can enforce stronger secret policy.
        self._pepper = hashlib.sha256(settings.jwt_secret_key.get_secret_value().encode("utf-8")).digest()

    async def create_guest(self, device_key: str = "") -> tuple[GuestSubject, GuestSession, str]:
        self.validate_device_key(device_key)
        now = datetime.now(UTC)
        subject_id = f"gst_{secrets.token_hex(16)}"
        token = secrets.token_hex(self.TOKEN_BYTES)
        device_hash = self._hash_device_key(device_key)
        expires_at = now + self.TTL
        subject = GuestSubject(
            guest_subject_id=subject_id,
            device_key_hash=device_hash,
            scopes=" ".join(self.SCOPES),
            expires_at=expires_at,
        )
        session = GuestSession(
            id=secrets.randbits(63),
            guest_subject_id=subject_id,
            token_digest=self._hash_token(token),
            device_key_hash=device_hash,
            scopes=" ".join(self.SCOPES),
            expires_at=expires_at,
            created_at=now,
        )
        self._session.add_all((subject, session))
        await self._session.commit()
        return subject, session, token

    async def verify_token(self, token: str, device_key: str) -> GuestSession | None:
        if len(token) != self.TOKEN_BYTES * 2:
            return None
        try:
            self.validate_device_key(device_key)
        except ValueError:
            return None
        now = datetime.now(UTC)
        row = await self._session.scalar(
            select(GuestSession).where(
                GuestSession.token_digest == self._hash_token(token),
                GuestSession.device_key_hash == self._hash_device_key(device_key),
                GuestSession.revoked_at.is_(None),
                GuestSession.expires_at > now,
            )
        )
        return row

    async def revoke(self, token: str, device_key: str) -> str | None:
        current = await self.verify_token(token, device_key)
        if current is None:
            return None
        now = datetime.now(UTC)
        await self._session.execute(
            update(GuestSession).where(GuestSession.guest_subject_id == current.guest_subject_id).values(revoked_at=now)
        )
        await self._session.execute(
            update(GuestSubject).where(GuestSubject.guest_subject_id == current.guest_subject_id).values(revoked_at=now)
        )
        await self._session.commit()
        return current.guest_subject_id

    async def cleanup_expired(self, now: datetime | None = None) -> int:
        cutoff = now or datetime.now(UTC)
        result = await self._session.execute(
            delete(GuestSession).where((GuestSession.expires_at <= cutoff) | GuestSession.revoked_at.is_not(None))
        )
        await self._session.commit()
        return int(getattr(result, "rowcount", 0) or 0)

    def _hash_token(self, token: str) -> str:
        return hmac.new(self._pepper, token.encode("utf-8"), hashlib.sha256).hexdigest()

    def _hash_device_key(self, device_key: str) -> str:
        return hmac.new(self._pepper, device_key.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def validate_device_key(device_key: str) -> None:
        if len(device_key) > 4096:
            raise ValueError("device proof is too long")
        if re.fullmatch(r"[0-9a-fA-F]{64}", device_key):
            return
        if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", device_key):
            raise ValueError("device proof must encode at least 256 bits")
        try:
            raw = base64.b64decode(device_key + "=" * (-len(device_key) % 4), altchars=b"-_", validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("device proof is not valid base64url") from exc
        if len(raw) < 32:
            raise ValueError("device proof must encode at least 256 bits")
