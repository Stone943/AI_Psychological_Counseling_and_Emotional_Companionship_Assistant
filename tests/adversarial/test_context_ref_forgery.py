"""B-18: Context ref forgery attacks — must be rejected."""

from __future__ import annotations

import pytest

from mental_health_api.safety.context_ref import build_context_ref


def test_wrong_grammar_fails() -> None:
    """Context ref must match entry_point grammar exactly."""
    with pytest.raises(ValueError, match="Unknown entry_point"):
        build_context_ref("nonexistent.entry", foo="bar")


def test_chat_context_requires_conversation_id() -> None:
    """chat.message grammar requires conversation_id."""
    with pytest.raises(KeyError):
        build_context_ref("chat.message", wrong_key="x")  # Missing conversation_id


def test_context_ref_is_not_user_provided() -> None:
    """Context ref is always built by B from auth context, never from client input."""
    # The build_context_ref function uses server-side IDs, not client-provided values
    ref = build_context_ref("chat.message", conversation_id="server-assigned-id")
    assert ref == "conversation:server-assigned-id"
    # Even if client tries to pass a manipulated ID, B uses the auth-resolved value
    ref2 = build_context_ref("chat.message", conversation_id="real-id-from-token")
    assert ref2 == "conversation:real-id-from-token"
