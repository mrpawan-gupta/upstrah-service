"""Presentation-layer controller for the auth (phone-OTP) endpoints.

Thin facade: maps Pydantic schemas → DTOs (via :class:`AuthMapper`),
calls exactly one use-case method, and maps the resulting domain entity
→ DTO → response dict. No business logic, no ORM, no ``model_dump()`` in
the body — the endpoint adds the ``APIResponse`` envelope.

This controller composes two use cases (``AuthUseCases`` and
``UserProfileUseCases``) because the ``me`` endpoint reads the caller's
onboarding profile; no single CRUD shape fits, so per the common-base
rule it documents the exception rather than inheriting one base's CRUD.
"""

from __future__ import annotations

from accounts.api.application.dtos.auth_dtos import (
    LogoutDTO,
    OTPSendDTO,
    OTPVerifyDTO,
    RefreshDTO,
)
from accounts.api.application.mappers.auth_mapper import AuthMapper
from accounts.api.application.mappers.user_profile_mapper import UserProfileMapper
from accounts.api.application.use_cases.auth_use_cases import AuthUseCases
from accounts.api.application.use_cases.user_profile_use_cases import (
    UserProfileUseCases,
)
from accounts.api.presentation.schemas.auth_schemas import (
    LogoutRequest,
    OTPSendRequest,
    OTPVerifyRequest,
    RefreshRequest,
)
from common.api.base_controller import BaseController


class AuthController(BaseController):
    """Facade over the auth workflows.

    Args:
        use_cases:         The ``AuthUseCases`` providing the OTP/JWT flows.
        profile_use_cases: The ``UserProfileUseCases`` used by ``me``.
    """

    def __init__(
        self,
        use_cases: AuthUseCases,
        profile_use_cases: UserProfileUseCases,
    ) -> None:
        """Inject the auth and profile use-case dependencies."""
        super().__init__(use_cases)
        self._uc = use_cases
        self._profile_uc = profile_use_cases

    async def send_otp(self, payload: OTPSendRequest) -> dict:
        """Send an OTP to the given phone number (POST /auth/otp/send).

        Args:
            payload: Validated request with the ``phone`` in E.164 format.

        Returns:
            Dict with ``message`` and ``expires_in`` (seconds).

        Raises:
            RateLimitError: Too many OTP requests for this phone.
        """
        expires_in = await self._uc.send_otp(OTPSendDTO(phone=payload.phone))
        return AuthMapper.otp_send_response(expires_in)

    async def verify_otp(self, payload: OTPVerifyRequest) -> dict:
        """Verify an OTP code and return a JWT token pair (POST /auth/otp/verify).

        Args:
            payload: Validated request with ``phone`` and ``code``.

        Returns:
            Serialised ``TokenResponse`` dict.

        Raises:
            AuthenticationError: OTP is invalid or has expired.
        """
        entity = await self._uc.verify_otp(
            OTPVerifyDTO(phone=payload.phone, code=payload.code)
        )
        return AuthMapper.dto_to_response(AuthMapper.entity_to_dto(entity))

    async def refresh(self, payload: RefreshRequest) -> dict:
        """Issue a new access token from a valid refresh token (POST /auth/refresh).

        Args:
            payload: Validated request with the ``refresh_token``.

        Returns:
            Serialised ``TokenResponse`` dict.

        Raises:
            AuthenticationError: Token invalid, expired, or wrong type.
        """
        entity = await self._uc.refresh(RefreshDTO(refresh_token=payload.refresh_token))
        return AuthMapper.dto_to_response(AuthMapper.entity_to_dto(entity))

    async def logout(self, payload: LogoutRequest) -> dict:
        """Revoke both tokens (POST /auth/logout).

        Args:
            payload: Validated request with ``access_token`` and ``refresh_token``.

        Returns:
            Empty dict; the endpoint supplies the confirmation message.
        """
        await self._uc.logout(
            LogoutDTO(
                access_token=payload.access_token,
                refresh_token=payload.refresh_token,
            )
        )
        return {}

    async def me(self, user_id: int) -> dict:
        """Return the authenticated caller's profile (GET /auth/me).

        Args:
            user_id: PK of the authenticated caller (from the JWT).

        Returns:
            Serialised ``UserProfileResponseSchema`` dict.
        """
        entity = await self._profile_uc.get(user_id)
        return UserProfileMapper.entity_to_response(entity)
