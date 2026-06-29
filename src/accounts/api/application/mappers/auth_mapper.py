"""Mapper for the auth token aggregate.

Converts ``AuthTokenEntity`` → ``AuthTokenResponseDTO`` → response dict.
``model_dump()`` is called only inside ``dto_to_response`` /
``otp_send_response`` — never in a controller body or use case.
"""

from __future__ import annotations

from accounts.api.application.dtos.auth_dtos import AuthTokenResponseDTO
from accounts.api.domain.entities.auth import AuthTokenEntity
from accounts.api.presentation.schemas.auth_schemas import (
    OTPSendResponse,
    TokenResponse,
)


class AuthMapper:
    """Stateless mapper for auth token responses.

    All methods are ``@staticmethod`` — this class is never instantiated.
    """

    @staticmethod
    def entity_to_dto(entity: AuthTokenEntity) -> AuthTokenResponseDTO:
        """Convert an ``AuthTokenEntity`` to an ``AuthTokenResponseDTO``.

        Args:
            entity: Domain entity returned by an auth use case.

        Returns:
            ``AuthTokenResponseDTO`` carrying both tokens and the token type.
        """
        return AuthTokenResponseDTO(
            access_token=entity.access_token,
            refresh_token=entity.refresh_token,
            token_type=entity.token_type,
        )

    @staticmethod
    def dto_to_response(dto: AuthTokenResponseDTO) -> dict:
        """Serialise an ``AuthTokenResponseDTO`` to a plain dict for JSON encoding.

        ``model_dump()`` is called here and only here for this aggregate.

        Args:
            dto: Application-layer DTO to serialise.

        Returns:
            Plain dict with ``access_token``, ``refresh_token``, ``token_type``.
        """
        return TokenResponse.model_validate(dto, from_attributes=True).model_dump(
            mode="json"
        )

    @staticmethod
    def otp_send_response(expires_in: int) -> dict:
        """Build the OTP send response dict.

        Args:
            expires_in: Seconds until the OTP expires.

        Returns:
            Plain dict with ``message`` and ``expires_in``.
        """
        return OTPSendResponse(
            message="OTP sent successfully",
            expires_in=expires_in,
        ).model_dump(mode="json")
