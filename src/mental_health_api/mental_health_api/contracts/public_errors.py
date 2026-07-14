# ruff: noqa: E501  # error spec lines are fine as-is
"""PublicError — the single source of truth for all API error codes.

Frozen per PRD section 2.5. Any addition/deletion/change requires
error-contract version bump.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ClientAction = Literal[
    "none",
    "fix_input",
    "authenticate",
    "reauthenticate",
    "refresh",
    "retry",
    "retry_after",
    "use_new_idempotency_key",
    "reconnect",
    "resume",
    "obtain_new_ticket",
    "show_safe_template",
    "refetch_definition",
    "open_safety_confirmation",
    "remove_local_copy",
    "restart_recovery",
    "create_guest_session",
    "show_pending",
    "contact_support",
]


@dataclass(frozen=True)
class PublicErrorSpec:
    """A single canonical error row."""

    code: str
    http_status: int
    retryable: bool
    client_action: ClientAction
    description: str = ""


# v1 frozen canonical rows per PRD 2.5
CANONICAL_ERRORS: dict[str, PublicErrorSpec] = {
    "VALIDATION_FAILED": PublicErrorSpec("VALIDATION_FAILED", 422, False, "fix_input"),
    "AUTH_REQUIRED": PublicErrorSpec("AUTH_REQUIRED", 401, False, "authenticate"),
    "AUTH_INVALID": PublicErrorSpec("AUTH_INVALID", 401, False, "reauthenticate"),
    "FORBIDDEN": PublicErrorSpec("FORBIDDEN", 403, False, "none"),
    "NOT_FOUND": PublicErrorSpec("NOT_FOUND", 404, False, "none"),
    "CONFLICT": PublicErrorSpec("CONFLICT", 409, False, "refresh"),
    "IDEMPOTENCY_CONFLICT": PublicErrorSpec("IDEMPOTENCY_CONFLICT", 409, False, "use_new_idempotency_key"),
    "RATE_LIMITED": PublicErrorSpec("RATE_LIMITED", 429, True, "retry_after"),
    "SERVICE_UNAVAILABLE": PublicErrorSpec("SERVICE_UNAVAILABLE", 503, True, "retry"),
    "SAFETY_GATE_UNAVAILABLE": PublicErrorSpec("SAFETY_GATE_UNAVAILABLE", 503, True, "retry"),
    "TEXT_ENTRY_NOT_REGISTERED": PublicErrorSpec("TEXT_ENTRY_NOT_REGISTERED", 500, False, "contact_support"),
    "TEXT_ENTRY_CONTEXT_MISMATCH": PublicErrorSpec("TEXT_ENTRY_CONTEXT_MISMATCH", 400, False, "fix_input"),
    "WS_COMMAND_INVALID": PublicErrorSpec("WS_COMMAND_INVALID", 400, False, "reconnect"),
    "WS_ACK_INVALID": PublicErrorSpec("WS_ACK_INVALID", 409, False, "resume"),
    "WS_RESUME_INVALID": PublicErrorSpec("WS_RESUME_INVALID", 409, False, "reconnect"),
    "WS_TICKET_INVALID": PublicErrorSpec("WS_TICKET_INVALID", 401, False, "obtain_new_ticket"),
    "OUTPUT_BLOCKED": PublicErrorSpec("OUTPUT_BLOCKED", 422, False, "show_safe_template"),
    "ASSESSMENT_VERSION_CONFLICT": PublicErrorSpec("ASSESSMENT_VERSION_CONFLICT", 409, False, "refetch_definition"),
    "SAFETY_CONFIRMATION_REQUIRED": PublicErrorSpec(
        "SAFETY_CONFIRMATION_REQUIRED", 423, False, "open_safety_confirmation"
    ),
    "ASSESSMENT_RESULT_DELETED": PublicErrorSpec("ASSESSMENT_RESULT_DELETED", 410, False, "remove_local_copy"),
    "RECOVERY_TOKEN_INVALID": PublicErrorSpec("RECOVERY_TOKEN_INVALID", 400, False, "restart_recovery"),
    "GUEST_SESSION_INVALID": PublicErrorSpec("GUEST_SESSION_INVALID", 401, False, "create_guest_session"),
    "GUEST_SESSION_EXPIRED": PublicErrorSpec("GUEST_SESSION_EXPIRED", 401, False, "create_guest_session"),
    "CONTENT_WITHDRAWN": PublicErrorSpec("CONTENT_WITHDRAWN", 410, False, "remove_local_copy"),
    "DELETION_IN_PROGRESS": PublicErrorSpec("DELETION_IN_PROGRESS", 202, False, "show_pending"),
    "INTERNAL_ERROR": PublicErrorSpec("INTERNAL_ERROR", 500, True, "retry"),
}


def get_error(code: str) -> PublicErrorSpec:
    """Look up a canonical error. Returns INTERNAL_ERROR for unknown codes."""
    return CANONICAL_ERRORS.get(code, CANONICAL_ERRORS["INTERNAL_ERROR"])
