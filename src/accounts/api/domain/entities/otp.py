"""Domain entity for the OTP aggregate.

``OTPEntity`` extends :class:`common.api.BaseEntity` (itself a frozen
dataclass), inheriting the shared ``to_dict`` helper. The subclass keeps
its own ``@dataclass(frozen=True)`` decoration to register its fields.
No ORM object is ever exposed here — the mapper builds this entity from
the ``accounts.models.OTP`` row.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from common.api import BaseEntity


@dataclass(frozen=True)
class OTPEntity(BaseEntity):
    """Immutable domain representation of an OTP row.

    Attributes:
        id:         Primary key of the OTP row.
        phone:      E.164 phone the code was issued to, or ``None``.
        email:      Email the code was issued to, or ``None``.
        otp:        The generated numeric OTP code, or ``None``.
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
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
