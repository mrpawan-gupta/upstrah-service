"""Abstract repository interfaces (ports) for the accounts app.

Pure ``abc.ABC`` contracts the application layer depends on; concrete
Django-ORM implementations live in ``infrastructure/repositories`` and are
substituted at wiring time. Importing from this package keeps call sites
decoupled from the individual interface modules.

Interfaces:
    IAuthRepository        — phone-user resolution + JWT claim assembly
    IOTPRepository         — OTP persistence (get/create/save/delete)
    IUserProfileRepository — 1:1 onboarding profile get / upsert
"""

from accounts.api.domain.repositories.auth_repository import IAuthRepository
from accounts.api.domain.repositories.otp_repository import IOTPRepository
from accounts.api.domain.repositories.user_profile_repository import (
    IUserProfileRepository,
)

__all__ = [
    "IAuthRepository",
    "IOTPRepository",
    "IUserProfileRepository",
]
