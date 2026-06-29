"""Abstract port for OTP delivery dispatch.

The application layer depends only on this interface; the infrastructure
layer supplies the concrete implementation (a mocked/logging dispatcher in
this service — no real SMS provider is called). Keeping the port here lets
a fake be substituted in tests by swapping one DI slot.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class IOTPDispatcher(ABC):
    """Port: deliver an OTP code to a phone over a channel.

    Infrastructure provides the concrete implementation. In this service
    delivery is mocked, so the implementation only logs the intent.
    """

    @abstractmethod
    async def send_otp(self, *, phone: str, otp_code: str, channel: str) -> None:
        """Deliver ``otp_code`` to ``phone`` via ``channel``.

        Args:
            phone:    E.164 destination phone number.
            otp_code: Numeric OTP code to deliver.
            channel:  Delivery channel (``"sms"``, ``"whatsapp"``, ``"auto"``).
        """
