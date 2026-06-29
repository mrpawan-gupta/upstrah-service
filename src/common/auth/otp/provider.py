"""OTP code generation utility."""

from __future__ import annotations

import secrets

from django.conf import settings


class OTPProvider:
    """Generates OTP codes, honouring dev/QA overrides from Django settings."""

    _DIGITS = "0123456789"

    def __init__(self, length: int = 4) -> None:
        self.length = length

    def generate(self, length: int | None = None, phone: str | None = None) -> str:
        """Return an OTP code for *phone*.

        Resolution order:
        1. ``OTP_FIXED_CODE`` — non-empty → every phone gets this code (dev/local).
        2. ``OTP_BYPASS_PHONE`` / ``OTP_BYPASS_CODE`` — single-phone QA override (prod).
        3. Cryptographically random code of *length* digits.
        """
        fixed = getattr(settings, "OTP_FIXED_CODE", "")
        if fixed:
            return fixed

        if phone:
            bypass_phone = getattr(settings, "OTP_BYPASS_PHONE", "")
            bypass_code = getattr(settings, "OTP_BYPASS_CODE", "")
            if bypass_phone and bypass_code and phone == bypass_phone:
                return bypass_code

        size = length if length is not None else self.length
        return "".join(secrets.choice(self._DIGITS) for _ in range(size))
