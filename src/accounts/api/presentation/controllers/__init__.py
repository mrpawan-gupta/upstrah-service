"""Presentation-layer controllers for the accounts app.

Thin facades over the use cases (extending
:class:`common.api.BaseController`): translate request schema → DTO, call
one use-case method, map the returned entity → response dict. No business
logic, no ORM, no ``APIResponse`` (the endpoint adds the envelope).

Controllers:
    AuthController        — OTP send/verify, refresh, logout, me
    OTPController         — OTP admin CRUD
    UserProfileController — onboarding profile read/update
"""

from accounts.api.presentation.controllers.auth_controller import AuthController
from accounts.api.presentation.controllers.otp_controller import OTPController
from accounts.api.presentation.controllers.user_profile_controller import (
    UserProfileController,
)

__all__ = [
    "AuthController",
    "OTPController",
    "UserProfileController",
]
