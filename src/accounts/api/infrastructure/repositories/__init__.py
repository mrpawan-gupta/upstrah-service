"""Concrete Django-ORM repository implementations for the accounts app.

Each ``*RepositoryImpl`` satisfies a domain port and (where it needs CRUD)
inherits :class:`common.api.BaseRepository`. Data access only — no
business rules, no HTTP, no Celery.

Implementations:
    AuthRepositoryImpl        — phone-user resolution + JWT claim assembly
    OTPRepositoryImpl         — OTP persistence over ``accounts.models.OTP``
    UserProfileRepositoryImpl — 1:1 onboarding profile get / upsert
"""

from accounts.api.infrastructure.repositories.auth_repository_impl import (
    AuthRepositoryImpl,
)
from accounts.api.infrastructure.repositories.otp_repository_impl import (
    OTPRepositoryImpl,
)
from accounts.api.infrastructure.repositories.user_profile_repository_impl import (
    UserProfileRepositoryImpl,
)

__all__ = [
    "AuthRepositoryImpl",
    "OTPRepositoryImpl",
    "UserProfileRepositoryImpl",
]
