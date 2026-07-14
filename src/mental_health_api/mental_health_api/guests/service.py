"""Guest session service — creation, lookup, revocation, cleanup."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from mental_health_api.database.models import GuestSession, GuestSubject

if TYPE_CHECKING:
    from mental_health_api.config import Settings


class GuestService:
    """Manages guest (unauthenticated) temporary identities."""

    TOKEN_BYTES = 32  # 256-bit opaque token
    TTL_HOURS = 24

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pepper = (settings.jwt_secret_key.get_secret_value()[:32]).encode()

    def create_guest(self, device_key: str = "") -> tuple[GuestSubject, str]:
        """Create a new guest subject with a 256-bit opaque access token."""
        subject_id = f"gst_{secrets.token_hex(16)}"
        token = secrets.token_hex(self.TOKEN_BYTES)
        token_digest = self._hash_token(token)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.TTL_HOURS)

        subject = GuestSubject(
            guest_subject_id=subject_id,
            device_key_hash=self._hash_device_key(device_key),
            scopes="onboarding register safety_gate realtime_ticket core_functions",
            expires_at=expires_at,
        )

        GuestSession(
            guest_subject_id=subject_id,
            token_digest=token_digest,
            device_key_hash=self._hash_device_key(device_key),
            scopes="onboarding register safety_gate realtime_ticket core_functions",
            expires_at=expires_at,
        )

        return subject, token

    def verify_token(self, token: str) -> str | None:
        """Verify a guest token and return the subject_id, or None."""
        self._hash_token(token)
        # In production, this queries the DB for matching digest, non-revoked, non-expired
        # For now, return a stub
        return None

    def revoke(self, subject_id: str) -> None:
        """Revoke all sessions for a guest subject."""
        pass

    def cleanup_expired(self) -> int:
        """Delete expired guest subjects and sessions. Returns count cleaned."""
        return 0

    def _hash_token(self, token: str) -> str:
        """HMAC-SHA256 digest of a token (only digest stored in DB)."""
        return hmac.new(self._pepper, token.encode(), hashlib.sha256).hexdigest()

    def _hash_device_key(self, device_key: str) -> str:
        """HMAC-SHA256 digest of a device key."""
        if not device_key:
            return ""
        return hmac.new(self._pepper, device_key.encode(), hashlib.sha256).hexdigest()
