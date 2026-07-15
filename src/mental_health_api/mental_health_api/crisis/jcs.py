"""RFC 8785 JSON canonicalization boundary."""

from __future__ import annotations

from typing import Any

import rfc8785


def canonicalize(value: Any) -> bytes:
    """Return RFC 8785 canonical UTF-8 bytes or reject unsupported JSON."""
    try:
        encoded = rfc8785.dumps(value)
    except (rfc8785.CanonicalizationError, TypeError, ValueError) as exc:
        raise ValueError("value is not RFC 8785 canonicalizable") from exc
    return encoded if isinstance(encoded, bytes) else encoded.encode("utf-8")
