"""Structured error handling for mental_health_api.

Provides application-level error classes and exception handlers.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error with structured fields."""

    def __init__(
        self,
        code: str,
        message: str = "",
        http_status: int = 500,
        retryable: bool = False,
        client_action: str = "none",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message or code
        self.http_status = http_status
        self.retryable = retryable
        self.client_action = client_action
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppError):
    """Input validation failure."""

    def __init__(self, message: str = "Validation failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="VALIDATION_FAILED",
            message=message,
            http_status=422,
            retryable=False,
            client_action="fix_input",
            details=details,
        )


class AuthError(AppError):
    """Authentication failure."""

    def __init__(self, code: str = "AUTH_REQUIRED", message: str = "Authentication required") -> None:
        super().__init__(
            code=code,
            message=message,
            http_status=401,
            retryable=False,
            client_action="authenticate" if code == "AUTH_REQUIRED" else "reauthenticate",
        )


class ForbiddenError(AppError):
    """Authorization failure."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(
            code="FORBIDDEN",
            message=message,
            http_status=403,
            retryable=False,
            client_action="none",
        )


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, message: str = "Not found") -> None:
        super().__init__(
            code="NOT_FOUND",
            message=message,
            http_status=404,
            retryable=False,
            client_action="none",
        )


class ConflictError(AppError):
    """Resource conflict."""

    def __init__(self, code: str = "CONFLICT", message: str = "Resource conflict") -> None:
        super().__init__(
            code=code,
            message=message,
            http_status=409,
            retryable=False,
            client_action="refresh" if code == "CONFLICT" else "use_new_idempotency_key",
        )


class RateLimitError(AppError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int = 60) -> None:
        super().__init__(
            code="RATE_LIMITED",
            message="Too many requests",
            http_status=429,
            retryable=True,
            client_action="retry_after",
            details={"retry_after_seconds": retry_after},
        )


class ServiceUnavailableError(AppError):
    """Service unavailable — may retry."""

    def __init__(self, code: str = "SERVICE_UNAVAILABLE", message: str = "Service unavailable") -> None:
        super().__init__(
            code=code,
            message=message,
            http_status=503,
            retryable=True,
            client_action="retry",
        )


class InternalError(AppError):
    """Unexpected internal error."""

    def __init__(self, message: str = "Internal server error") -> None:
        super().__init__(
            code="INTERNAL_ERROR",
            message=message,
            http_status=500,
            retryable=True,
            client_action="retry",
        )
