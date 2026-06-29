"""Pydantic request/response schemas for the auth (phone-OTP) endpoints.

Request schemas extend :class:`common.api.BaseRequestSchema`
(``extra="forbid"`` — unknown fields are rejected with a 422); response
schemas extend :class:`common.api.BaseResponseSchema`
(``from_attributes=True`` — a mapper can validate straight from a DTO).
Validation lives here, never in the controller.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from pydantic import Field

from common.api import BaseRequestSchema, BaseResponseSchema


class OTPSendRequest(BaseRequestSchema):
    """Validated body for ``POST /auth/otp/send``.

    Attributes:
        phone: Phone number in E.164 format (e.g. ``+15551234567``).
            Rate-limited per phone by the cache-backed OTP handler.
    """

    phone: str = Field(
        ...,
        min_length=1,
        description=str(_("Phone number in E.164 format (e.g. +15551234567).")),
    )


class OTPVerifyRequest(BaseRequestSchema):
    """Validated body for ``POST /auth/otp/verify``.

    Attributes:
        phone: Phone number in E.164 format that received the OTP.
        code:  Numeric OTP code sent to ``phone``.
    """

    phone: str = Field(
        ...,
        min_length=1,
        description=str(_("Phone number in E.164 format that received the OTP.")),
    )
    code: str = Field(
        ...,
        min_length=4,
        max_length=8,
        description=str(_("Numeric OTP code sent to the phone number.")),
    )


class RefreshRequest(BaseRequestSchema):
    """Validated body for ``POST /auth/refresh``.

    Attributes:
        refresh_token: A valid JWT refresh token previously issued by
            ``/auth/otp/verify`` or ``/auth/refresh``.
    """

    refresh_token: str = Field(
        ...,
        min_length=1,
        description=str(_("Valid JWT refresh token to exchange for a new access token.")),
    )


class LogoutRequest(BaseRequestSchema):
    """Validated body for ``POST /auth/logout``.

    Both tokens are blacklisted so neither can be reused after logout.

    Attributes:
        access_token:  The JWT access token to revoke.
        refresh_token: The JWT refresh token to revoke.
    """

    access_token: str = Field(
        ..., min_length=1, description=str(_("JWT access token to revoke."))
    )
    refresh_token: str = Field(
        ..., min_length=1, description=str(_("JWT refresh token to revoke."))
    )


class TokenResponse(BaseResponseSchema):
    """JWT token pair returned on a successful OTP verify or refresh.

    Attributes:
        access_token:  Short-lived JWT for authenticating API requests.
        refresh_token: Long-lived JWT for obtaining new access tokens.
        token_type:    Always ``"bearer"`` — for the ``Authorization`` header.
    """

    access_token: str = Field(
        ..., description=str(_("Short-lived JWT for authenticating API requests."))
    )
    refresh_token: str = Field(
        ..., description=str(_("Long-lived JWT for obtaining new access tokens."))
    )
    token_type: str = Field(
        "bearer",
        description=str(_("Token type for the Authorization header. Always 'bearer'.")),
    )


class OTPSendResponse(BaseResponseSchema):
    """Response payload for ``POST /auth/otp/send``.

    Attributes:
        message:    Human-readable confirmation that the OTP was dispatched.
        expires_in: Number of seconds before the OTP expires.
    """

    message: str = Field(
        ..., description=str(_("Confirmation that the OTP was dispatched."))
    )
    expires_in: int = Field(
        ..., description=str(_("Number of seconds before the OTP expires."))
    )
