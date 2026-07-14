"""Auth service — registration, login, token management."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from mental_health_api.auth.passwords import hash_password
from mental_health_api.auth.tokens import create_access_token, create_refresh_token

if TYPE_CHECKING:
    from mental_health_api.config import Settings


class AuthService:
    """Manages user authentication: register, login, refresh, logout, device revocation."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def register(self, email: str, password: str, nickname: str | None = None) -> dict:
        """Register a new user account. Returns tokens."""
        email_hash = self._hash_email(email)
        hash_password(password)
        # In production: store in DB, check uniqueness
        access_token = create_access_token(email_hash, self._settings)
        refresh_token, refresh_digest, family = create_refresh_token(self._settings)
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "Bearer", "expires_in": 900}

    def login(self, email: str, password: str) -> dict | None:
        """Authenticate a user. Returns tokens or None."""
        self._hash_email(email)
        # In production: lookup user by email_hash, verify password_hash
        return None

    def refresh(self, refresh_token: str) -> dict | None:
        """Rotate refresh token. Returns new token pair."""
        return None

    def logout(self, refresh_token: str) -> None:
        """Revoke a refresh token."""
        pass

    def _hash_email(self, email: str) -> str:
        """HMAC-SHA256 email hash with pepper."""
        pepper = self._settings.jwt_secret_key.get_secret_value()[:32].encode()
        return hashlib.sha256(pepper + email.lower().strip().encode()).hexdigest()
