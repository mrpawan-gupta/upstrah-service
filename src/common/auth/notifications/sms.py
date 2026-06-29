"""SMS service interface and implementations.

Provides an ``ISMSService`` protocol and a ``ConsoleSMSService`` stub for
local development.  In production, Twilio is used as the SMS provider,
configured via Django settings and the DI container.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger(__name__)


class ISMSService(ABC):
    """Abstract interface for SMS delivery.

    All implementations must be safe to call from async context (they may
    delegate to a thread pool internally if the underlying SDK is sync).
    """

    @abstractmethod
    def send(self, phone: str, message: str) -> None:
        """Send *message* to *phone*.

        Args:
            phone:   E.164 phone number (e.g. ``"+6281234567890"``).
            message: Plain-text message body.
        """


class ConsoleSMSService(ISMSService):
    """Development stub — logs delivery intent and prints to stdout.

    Intentionally does NOT log or print the message body to avoid leaking
    OTP codes into log aggregators.  The actual code is printed to stdout
    only, which is acceptable in development but should be replaced in
    production.
    """

    def send(self, phone: str, message: str) -> None:
        """Print the SMS to stdout and log delivery (without the message body).

        Args:
            phone:   Destination phone number in E.164 format.
            message: Message body (printed to stdout only; not logged).
        """
        logger.info("sms_stub_send", phone=phone)
        print(f"\n[SMS] {phone}: {message}\n")


console_sms_service = ConsoleSMSService()
