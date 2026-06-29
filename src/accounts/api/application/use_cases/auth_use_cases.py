"""Auth business logic — OTP send, OTP verify → JWT, refresh, logout, me.

This service authenticates users by phone OTP only (no email/password,
no SSO). Security characteristics mirrored from the reference:

- OTP send is rate-limited per phone (cache-backed ``otp_handler``).
- OTP verify is attempt-limited per phone (lockout after repeated misses).
- Refresh tokens are rotated on every ``/auth/refresh`` and the consumed
  token is blacklisted so replay is detected.
- OTP delivery is MOCKED: the use case calls the injected ``IOTPDispatcher``
  whose concrete implementation only logs the intent (no real SMS).
"""

from __future__ import annotations

import structlog
from django.conf import settings

from accounts.api.application.dtos.auth_dtos import (
    LogoutDTO,
    OTPSendDTO,
    OTPVerifyDTO,
    RefreshDTO,
)
from accounts.api.application.interfaces.otp_dispatcher import IOTPDispatcher
from accounts.api.domain.entities.auth import AuthTokenEntity
from accounts.api.domain.repositories.auth_repository import IAuthRepository
from accounts.api.domain.repositories.otp_repository import IOTPRepository
from accounts.constants import OtpChannel, TokenType
from common.api import BaseUseCase
from common.auth.jwt.handler import jwt_handler
from common.auth.otp.handler import otp_handler
from common.exceptions.exceptions import AuthenticationError, RateLimitError

logger = structlog.get_logger(__name__)


class AuthUseCases(BaseUseCase):
    """Application-layer use cases for the phone-OTP authentication domain.

    Each method accepts a plain DTO (no FastAPI/HTTP dependencies),
    delegates persistence to the injected repositories, uses the shared
    ``jwt_handler`` / ``otp_handler`` helpers, and returns a domain entity
    or a primitive value.

    Args:
        repo:           Concrete ``IAuthRepository`` provided by the DI container.
        otp_repo:       Concrete ``IOTPRepository`` provided by the DI container.
        otp_dispatcher: Concrete ``IOTPDispatcher`` (mocked delivery).
    """

    def __init__(
        self,
        repo: IAuthRepository,
        otp_repo: IOTPRepository,
        otp_dispatcher: IOTPDispatcher,
    ) -> None:
        """Inject the repository and dispatcher dependencies."""
        super().__init__(repo)
        self._repo = repo
        self._otp_repo = otp_repo
        self._otp_dispatcher = otp_dispatcher

    async def _build_token_pair(
        self,
        user: object,
        refresh_token_to_rotate: str | None = None,
    ) -> AuthTokenEntity:
        """Issue an access + refresh token pair for ``user``.

        Args:
            user: Authenticated ORM ``User`` instance.
            refresh_token_to_rotate: Existing refresh token to rotate, or
                ``None`` to mint a brand-new refresh token.

        Returns:
            ``AuthTokenEntity`` with both tokens populated.
        """
        user_data = await self._repo.get_user_token_claims(user.pk)
        if refresh_token_to_rotate:
            new_refresh = jwt_handler.rotate_refresh_token(
                refresh_token_to_rotate, str(user.pk)
            )
        else:
            new_refresh = jwt_handler.generate_refresh_token(str(user.pk))
        return AuthTokenEntity(
            access_token=jwt_handler.generate_access_token(
                str(user.pk), user_data=user_data
            ),
            refresh_token=new_refresh,
        )

    async def send_otp(self, dto: OTPSendDTO) -> int:
        """Generate and (mock-)send an OTP to ``dto.phone``. Returns the TTL.

        Creates or resets an ``OTP`` row keyed by phone, then dispatches it
        through the mocked ``IOTPDispatcher``.

        Args:
            dto: ``OTPSendDTO`` with the target ``phone`` number.

        Returns:
            OTP validity duration in seconds.

        Raises:
            RateLimitError: Too many OTP send requests for this phone.
        """
        if otp_handler.is_rate_limited(dto.phone):
            raise RateLimitError("Too many OTP requests. Please try again later.")

        otp_obj, created = await self._otp_repo.get_or_create(dto.phone)
        if not created:
            otp_obj.set_otp_and_validity()
            await self._otp_repo.save(otp_obj)
        code = str(otp_obj.otp)
        otp_handler.increment_rate(dto.phone)

        channel = getattr(settings, "OTP_DELIVERY_CHANNEL", OtpChannel.SMS)
        await self._otp_dispatcher.send_otp(
            phone=dto.phone, otp_code=code, channel=str(channel)
        )
        logger.info("otp_sent", phone=dto.phone, channel=str(channel))

        return getattr(settings, "OTP_VALID_DURATION", 600)

    async def verify_otp(self, dto: OTPVerifyDTO) -> AuthTokenEntity:
        """Verify an OTP and return a JWT token pair for the associated user.

        Enforces a per-phone verify attempt limit, consumes the OTP row on
        success (single-use), and resolves-or-creates the phone user.

        Args:
            dto: ``OTPVerifyDTO`` with ``phone`` and ``code``.

        Returns:
            ``AuthTokenEntity`` with access and refresh tokens.

        Raises:
            RateLimitError: Too many failed OTP verify attempts.
            AuthenticationError: OTP is invalid or has expired.
        """
        if otp_handler.is_verify_rate_limited(dto.phone):
            raise RateLimitError(
                "Too many failed OTP attempts. Please request a new OTP."
            )

        otp_obj = await self._otp_repo.get_by_phone(dto.phone)
        if otp_obj is None or otp_obj.otp != dto.code or not otp_obj.is_valid():
            otp_handler.increment_verify_attempts(dto.phone)
            raise AuthenticationError("Invalid or expired OTP")

        otp_handler.clear_verify_attempts(dto.phone)
        await self._otp_repo.delete_row(otp_obj)

        user, _created = await self._repo.get_or_create_user_by_phone(dto.phone)
        logger.info("otp_verified", phone=dto.phone, user_id=str(user.pk))
        return await self._build_token_pair(user)

    async def refresh(self, dto: RefreshDTO) -> AuthTokenEntity:
        """Issue a new access token and a rotated refresh token.

        The presented refresh token is blacklisted after a successful call
        so it cannot be replayed.

        Args:
            dto: ``RefreshDTO`` with the current ``refresh_token``.

        Returns:
            ``AuthTokenEntity`` with a new access token and a new refresh token.

        Raises:
            AuthenticationError: Token is invalid, expired, or not a refresh token.
        """
        try:
            payload = jwt_handler.verify_token(dto.refresh_token)
        except Exception as exc:
            raise AuthenticationError("Invalid or expired refresh token") from exc

        if payload.get("token_type") != TokenType.REFRESH:
            raise AuthenticationError("Provided token is not a refresh token")

        user_id = payload.get("user_id")
        if not user_id:
            raise AuthenticationError("Malformed refresh token")

        user = await self._repo.get_user_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found")

        return await self._build_token_pair(
            user, refresh_token_to_rotate=dto.refresh_token
        )

    async def logout(self, dto: LogoutDTO) -> None:
        """Blacklist both the access and refresh tokens in the cache.

        Malformed or already-expired tokens are ignored — logout is
        best-effort idempotent.

        Args:
            dto: ``LogoutDTO`` with ``access_token`` and ``refresh_token``.
        """
        from datetime import UTC, datetime

        now = int(datetime.now(UTC).timestamp())
        for token in (dto.access_token, dto.refresh_token):
            try:
                token_payload = jwt_handler.verify_token(token)
                jti = token_payload.get("jti")
                exp = token_payload.get("exp", now)
                remaining = max(0, exp - now)
                if jti and remaining > 0:
                    jwt_handler.blacklist_token(jti, remaining)
            except Exception:
                pass
