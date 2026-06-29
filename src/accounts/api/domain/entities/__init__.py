"""Domain entities for the accounts app.

Frozen dataclasses representing immutable domain state passed between
layers. ORM models never leak past infrastructure; these carry only the
scalar attributes the use cases and presentation layer need.

Entities:
    AuthTokenEntity   — an issued JWT access/refresh token pair
    OTPEntity         — an OTP row (phone, code, expiry, validity)
    UserProfileEntity — a user's onboarding profile + owning-user scalars
"""

from accounts.api.domain.entities.auth import AuthTokenEntity
from accounts.api.domain.entities.otp import OTPEntity
from accounts.api.domain.entities.user_profile import UserProfileEntity

__all__ = [
    "AuthTokenEntity",
    "OTPEntity",
    "UserProfileEntity",
]
