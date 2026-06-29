"""OTP generation, rate-limiting, and lifecycle management."""

from common.auth.otp.handler import OTPHandler, otp_handler
from common.auth.otp.provider import OTPProvider

__all__ = ["OTPHandler", "OTPProvider", "otp_handler"]
