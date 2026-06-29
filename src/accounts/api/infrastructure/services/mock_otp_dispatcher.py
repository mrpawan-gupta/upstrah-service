"""Mocked OTP delivery dispatcher (no real SMS provider).

Implements the application-layer :class:`IOTPDispatcher` port. Delivery is
intentionally MOCKED in this service: the dispatcher hands the code to the
``common.auth.notifications.sms.ConsoleSMSService`` stub, which logs the
delivery intent and prints to stdout in development — no Twilio / 8x8
calls. Swap this slot in the DI container for a real provider when one is
added.
"""

from __future__ import annotations

import structlog

from accounts.api.application.interfaces.otp_dispatcher import IOTPDispatcher
from common.auth.notifications.sms import ConsoleSMSService

logger = structlog.get_logger(__name__)


class MockOTPDispatcher(IOTPDispatcher):
    """OTP dispatcher that mock-delivers via the console SMS stub."""

    def __init__(self) -> None:
        """Construct with the console SMS stub as the delivery channel."""
        self._sms = ConsoleSMSService()

    async def send_otp(self, *, phone: str, otp_code: str, channel: str) -> None:
        """Mock-deliver ``otp_code`` to ``phone`` over ``channel``.

        Args:
            phone:    E.164 destination phone number.
            otp_code: Numeric OTP code to deliver.
            channel:  Delivery channel label (logged only).
        """
        logger.info("otp_dispatch_mock", phone=phone, channel=channel)
        self._sms.send(phone, f"Your verification code is {otp_code}")
