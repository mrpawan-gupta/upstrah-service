"""Pydantic request/response schemas for the accounts presentation layer.

Request schemas extend :class:`common.api.BaseRequestSchema`
(``extra="forbid"``); response schemas extend
:class:`common.api.BaseResponseSchema` (``from_attributes=True``). These
define the wire shapes — domain entities are never serialised directly.

Auth schemas:    OTPSendRequest, OTPVerifyRequest, RefreshRequest,
                 LogoutRequest, TokenResponse, OTPSendResponse
OTP schemas:     OTPRequestSchema, OTPCreateResponseSchema, OTPResponseSchema
Profile schemas: UserProfilePatchSchema, UserProfileResponseSchema,
                 ProfileNestedSchema
"""

from accounts.api.presentation.schemas.auth_schemas import (
    LogoutRequest,
    OTPSendRequest,
    OTPSendResponse,
    OTPVerifyRequest,
    RefreshRequest,
    TokenResponse,
)
from accounts.api.presentation.schemas.otp_schemas import (
    OTPCreateResponseSchema,
    OTPRequestSchema,
    OTPResponseSchema,
)
from accounts.api.presentation.schemas.user_profile_schemas import (
    ProfileNestedSchema,
    UserProfilePatchSchema,
    UserProfileResponseSchema,
)

__all__ = [
    "LogoutRequest",
    "OTPCreateResponseSchema",
    "OTPRequestSchema",
    "OTPResponseSchema",
    "OTPSendRequest",
    "OTPSendResponse",
    "OTPVerifyRequest",
    "ProfileNestedSchema",
    "RefreshRequest",
    "TokenResponse",
    "UserProfilePatchSchema",
    "UserProfileResponseSchema",
]
