"""RecoveryMailer port — abstract interface for sending password recovery emails."""

from __future__ import annotations

from abc import ABC, abstractmethod


class RecoveryMailerPort(ABC):
    """Port for sending password recovery emails. Mailpit adapter in dev/test."""

    @abstractmethod
    async def send_recovery_email(self, email: str, recovery_link: str) -> None:
        """Send a password recovery email with a one-time link."""
        ...


class NoOpMailer(RecoveryMailerPort):
    """Default no-op mailer for when Mailpit is not available."""

    async def send_recovery_email(self, email: str, recovery_link: str) -> None:
        pass
