"""Data Transfer Objects for the OTP aggregate.

Both DTOs extend :class:`common.api.BaseModelDTO`, inheriting the shared
``to_dict`` / ``from_dict`` helpers; each subclass owns its ``@dataclass``
decoration. ``OTPCreateDTO`` is the write boundary; ``OTPResponseDTO`` is
the read boundary the mapper serialises to the response schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from common.api import BaseModelDTO


@dataclass
class OTPCreateDTO(BaseModelDTO):
    """Input DTO for creating or resetting an OTP.

    Attributes:
        phone:      E.164 phone number, or ``None``.
        email:      Email address, or ``None``. At least one must be set.
        otp:        Explicit OTP code to store; ``None`` triggers auto-generation.
        expires_at: Explicit expiry timestamp; ``None`` uses the default TTL.
    """

    phone: str | None = None
    email: str | None = None
    otp: str | None = None
    expires_at: datetime | None = None


@dataclass
class OTPResponseDTO(BaseModelDTO):
    """Read representation of an OTP row returned by use cases.

    Attributes:
        id:         PK of the OTP row.
        phone:      E.164 phone number, or ``None``.
        email:      Email address, or ``None``.
        otp:        The OTP code, or ``None``.
        expires_at: Expiry timestamp, or ``None``.
        is_valid:   Whether the code is still within its validity window.
        created_at: Row creation timestamp.
        updated_at: Row last-modified timestamp.
    """

    id: int
    phone: str | None
    email: str | None
    otp: str | None
    expires_at: datetime | None
    is_valid: bool
    created_at: datetime
    updated_at: datetime
