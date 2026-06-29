"""OTP generation, verification, and rate-limiting backed by Django cache."""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache

from common.auth.otp.provider import OTPProvider


class OTPHandler:
    """Manages the full OTP lifecycle for phone-based authentication."""

    OTP_KEY_PREFIX = "otp"
    RATE_KEY_PREFIX = "otp_rate"
    RATE_TTL = 3600

    def _otp_key(self, phone: str) -> str:
        """Return the cache key used to store the OTP code for *phone*."""
        return f"{self.OTP_KEY_PREFIX}:{phone}"

    def _rate_key(self, phone: str) -> str:
        """Return the cache key used to track the OTP send-rate for *phone*."""
        return f"{self.RATE_KEY_PREFIX}:{phone}"

    def generate_and_store(self, phone: str) -> str:
        """Generate an OTP, persist it in cache, and return the code."""
        code = OTPProvider().generate(
            length=getattr(settings, "OTP_LENGTH", 4), phone=phone
        )
        ttl = getattr(settings, "OTP_EXPIRE_SECONDS", 600)
        cache.set(self._otp_key(phone), code, timeout=ttl)
        return code

    def verify(self, phone: str, code: str) -> bool:
        """Check *code* against the stored OTP.

        Deletes the key on a successful match (single-use).
        Returns ``True`` on success, ``False`` otherwise.
        """
        stored = cache.get(self._otp_key(phone))
        if stored and stored == code:
            cache.delete(self._otp_key(phone))
            return True
        return False

    def is_rate_limited(self, phone: str) -> bool:
        """Return ``True`` if the phone has exceeded the hourly send limit."""
        count = cache.get(self._rate_key(phone))
        if count is None:
            return False
        max_attempts = getattr(settings, "OTP_RATE_LIMIT_MAX", 5)
        return int(count) >= max_attempts

    def increment_rate(self, phone: str) -> None:
        """Increment the hourly OTP-send counter for *phone*."""
        key = self._rate_key(phone)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=self.RATE_TTL)

    VERIFY_RATE_KEY_PREFIX = "otp_verify"
    MAX_VERIFY_ATTEMPTS = 5
    VERIFY_LOCKOUT_TTL = 600  # 10 minutes — matches OTP validity window

    def _verify_key(self, phone: str) -> str:
        """Return the cache key used to track failed OTP verify attempts."""
        return f"{self.VERIFY_RATE_KEY_PREFIX}:{phone}"

    def is_verify_rate_limited(self, phone: str) -> bool:
        """Return ``True`` if the phone has exceeded the OTP verify attempt limit.

        Args:
            phone: E.164 phone number being verified.

        Returns:
            ``True`` when the attempt counter has reached ``MAX_VERIFY_ATTEMPTS``.
        """
        count = cache.get(self._verify_key(phone))
        if count is None:
            return False
        return int(count) >= self.MAX_VERIFY_ATTEMPTS

    def increment_verify_attempts(self, phone: str) -> None:
        """Increment the failed OTP verify counter for *phone*.

        Args:
            phone: E.164 phone number that submitted a wrong code.
        """
        key = self._verify_key(phone)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=self.VERIFY_LOCKOUT_TTL)

    def clear_verify_attempts(self, phone: str) -> None:
        """Clear the failed OTP verify counter after a successful verification.

        Args:
            phone: E.164 phone number whose counter should be reset.
        """
        cache.delete(self._verify_key(phone))


otp_handler = OTPHandler()
