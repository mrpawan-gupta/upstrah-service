"""Data Transfer Objects for the accounts application layer.

Plain dataclasses (extending :class:`common.api.BaseModelDTO`) that carry
the minimal fields across each use-case boundary. No validation — that
lives in the presentation-layer Pydantic schemas.

Auth DTOs:    OTPSendDTO, OTPVerifyDTO, RefreshDTO, LogoutDTO, AuthTokenResponseDTO
OTP DTOs:     OTPCreateDTO, OTPResponseDTO
Profile DTOs: UpdateUserProfileDTO, UserProfileResponseDTO
"""

from accounts.api.application.dtos.auth_dtos import (
    AuthTokenResponseDTO,
    LogoutDTO,
    OTPSendDTO,
    OTPVerifyDTO,
    RefreshDTO,
)
from accounts.api.application.dtos.otp_dtos import OTPCreateDTO, OTPResponseDTO
from accounts.api.application.dtos.user_profile_dtos import (
    UpdateUserProfileDTO,
    UserProfileResponseDTO,
)

__all__ = [
    "AuthTokenResponseDTO",
    "LogoutDTO",
    "OTPCreateDTO",
    "OTPResponseDTO",
    "OTPSendDTO",
    "OTPVerifyDTO",
    "RefreshDTO",
    "UpdateUserProfileDTO",
    "UserProfileResponseDTO",
]
