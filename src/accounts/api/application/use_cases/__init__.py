"""Use cases for the accounts application layer.

Business-rule orchestration extending :class:`common.api.BaseUseCase`.
Use cases call repositories (typed as domain interfaces) and the shared
``jwt``/``otp`` helpers; they hold no FastAPI dependencies and no
``model_dump()``.

Use cases:
    AuthUseCases        — OTP send/verify → JWT, refresh, logout
    OTPUseCases         — OTP admin (create/list/get/delete)
    UserProfileUseCases — onboarding profile get / upsert
"""

from accounts.api.application.use_cases.auth_use_cases import AuthUseCases
from accounts.api.application.use_cases.otp_use_cases import OTPUseCases
from accounts.api.application.use_cases.user_profile_use_cases import (
    UserProfileUseCases,
)

__all__ = [
    "AuthUseCases",
    "OTPUseCases",
    "UserProfileUseCases",
]
