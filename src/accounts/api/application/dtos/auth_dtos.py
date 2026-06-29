"""Data Transfer Objects for authentication use cases.

These DTOs carry the minimal set of fields each auth use-case boundary
needs. They contain no validation logic — that responsibility belongs to
the Pydantic schemas in the presentation layer. Each extends
:class:`common.api.BaseModelDTO` for the shared ``to_dict`` / ``from_dict``
helpers and owns its own ``@dataclass`` decoration.
"""

from __future__ import annotations

from dataclasses import dataclass

from common.api import BaseModelDTO


@dataclass
class OTPSendDTO(BaseModelDTO):
    """Input DTO for sending a one-time password to a phone number.

    Attributes:
        phone: Target phone number in E.164 format (e.g. ``"+15551234567"``).
    """

    phone: str


@dataclass
class OTPVerifyDTO(BaseModelDTO):
    """Input DTO for verifying an OTP code.

    Attributes:
        phone: Phone number in E.164 format that received the OTP.
        code:  Numeric OTP code entered by the user.
    """

    phone: str
    code: str


@dataclass
class RefreshDTO(BaseModelDTO):
    """Input DTO for refreshing an access token.

    Attributes:
        refresh_token: A valid refresh JWT previously issued by the OTP verify
            or refresh endpoint.
    """

    refresh_token: str


@dataclass
class LogoutDTO(BaseModelDTO):
    """Input DTO for revoking a token pair on logout.

    Both tokens are blacklisted in the cache for the remainder of their
    TTL so neither can be replayed after logout.

    Attributes:
        access_token:  The JWT access token to revoke.
        refresh_token: The JWT refresh token to revoke.
    """

    access_token: str
    refresh_token: str


@dataclass
class AuthTokenResponseDTO(BaseModelDTO):
    """Output DTO for a successfully issued JWT token pair.

    Attributes:
        access_token:  RS256-signed access JWT.
        refresh_token: RS256-signed refresh JWT for rotation.
        token_type:    Fixed value ``"bearer"``.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
