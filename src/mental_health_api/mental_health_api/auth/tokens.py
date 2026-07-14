# ruff: noqa: E501
"""JWT access tokens and opaque refresh tokens."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import TYPE_CHECKING

import jwt

if TYPE_CHECKING:
    from mental_health_api.config import Settings


def create_access_token(subject_id: str, settings: Settings, ttl_seconds: int = 900) -> str:
    """Create a short-lived JWT access token (default 15 min)."""
    now = int(time.time())
    payload = {"sub": subject_id, "iat": now, "exp": now + ttl_seconds, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret_key.get_secret_value(), algorithm="HS256")


def verify_access_token(token: str, settings: Settings) -> dict | None:
    """Verify a JWT access token. Returns payload or None."""
    try:
        return jwt.decode(token, settings.jwt_secret_key.get_secret_value(), algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def create_refresh_token(settings: Settings) -> tuple[str, str, str]:
    """Create an opaque 256-bit refresh token. Returns (token, digest, family)."""
    token = secrets.token_hex(32)
    family = secrets.token_hex(16)
    digest = hmac.new(
        settings.refresh_token_secret.get_secret_value().encode(), token.encode(), hashlib.sha256
    ).hexdigest()
    return token, digest, family
