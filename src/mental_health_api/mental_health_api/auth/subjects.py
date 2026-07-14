"""Subject resolution — identify the authenticated principal (user or guest)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AuthenticatedSubject:
    """Resolved authenticated principal from bearer token."""

    subject_id: str
    subject_type: str  # "user" | "guest"
    scopes: list[str]


def resolve_guest(token: str) -> AuthenticatedSubject | None:
    """Verify a guest bearer token and return the authenticated subject, or None."""
    # Full implementation in B-04 domain — currently stub
    return None


def resolve_user(token: str) -> AuthenticatedSubject | None:
    """Verify a user JWT/opaque token and return the authenticated subject, or None."""
    # Full implementation in B-05
    return None
