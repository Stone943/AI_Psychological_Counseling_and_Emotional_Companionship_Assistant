"""Password recovery service — 256-bit token, 15 min TTL, single-use."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone


class RecoveryService:
    """Manages password recovery tokens. Token is 256-bit, only HMAC digest stored."""

    TOKEN_BYTES = 32
    TTL_MINUTES = 15

    def __init__(self, secret: str) -> None:
        self._secret = secret.encode()

    def create_recovery_token(self, email: str) -> tuple[str, str]:
        """Create a recovery token. Returns (plaintext_token, digest)."""
        token = secrets.token_hex(self.TOKEN_BYTES)
        digest = self._hash(token)
        return token, digest

    def verify_token(self, token: str, stored_digest: str) -> bool:
        """Verify a recovery token against stored digest."""
        return hmac.compare_digest(self._hash(token), stored_digest)

    def is_expired(self, created_at: datetime) -> bool:
        """Check if a token has expired (15 min TTL)."""
        deadline = created_at + timedelta(minutes=self.TTL_MINUTES)
        return datetime.now(timezone.utc) > deadline

    def _hash(self, token: str) -> str:
        return hmac.new(self._secret, token.encode(), hashlib.sha256).hexdigest()
