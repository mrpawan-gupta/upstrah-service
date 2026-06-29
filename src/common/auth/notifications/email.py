"""Email service interface and development stub.

Provides an ``IEmailService`` protocol and a ``ConsoleEmailService`` stub
for local development.  Replace ``ConsoleEmailService`` with a real provider
(SendGrid, Mailgun, SES, etc.) in production by implementing ``IEmailService``
and injecting it via the DI container.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class EmailMessage:
    """Structured email message.

    Attributes:
        to: Recipient email address.
        subject: Email subject line.
        body_text: Plain-text body.
        body_html: Optional HTML body.
        from_email: Sender address (falls back to settings default).
        reply_to: Optional reply-to address.
        tags: Provider-specific tags for tracking/categorisation.
    """

    to: str
    subject: str
    body_text: str
    body_html: str = ""
    from_email: str = ""
    reply_to: str = ""
    tags: list[str] = field(default_factory=list)


class IEmailService(ABC):
    """Abstract interface for email delivery.

    All implementations must be safe to call from async context (they may
    delegate to a thread pool internally if the underlying SDK is sync).
    """

    @abstractmethod
    def send(self, message: EmailMessage) -> None:
        """Send an email message.

        Args:
            message: The structured ``EmailMessage`` to deliver.

        Raises:
            Exception: On delivery failure (provider-specific).
        """


class ConsoleEmailService(IEmailService):
    """Development stub — prints email to stdout.

    Intentionally prints the full message body to stdout for local
    debugging.  Sensitive tokens (password reset, etc.) are visible
    only in the developer's terminal, not in log aggregators.

    Attributes:
        name: Provider identifier used by the router.
    """

    name = "console"

    def send(self, message: EmailMessage) -> None:
        """Print the email to stdout and log delivery intent.

        Args:
            message: The email message to "deliver".
        """
        logger.info("email_stub_send", to=message.to, subject=message.subject)
        print(
            f"\n{'=' * 60}\n"
            f"[EMAIL] To: {message.to}\n"
            f"[EMAIL] Subject: {message.subject}\n"
            f"[EMAIL] From: {message.from_email or '(default)'}\n"
            f"{'─' * 60}\n"
            f"{message.body_text}\n"
            f"{'=' * 60}\n"
        )


console_email_service = ConsoleEmailService()
