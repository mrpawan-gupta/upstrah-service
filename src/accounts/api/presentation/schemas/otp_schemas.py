"""Pydantic request/response schemas for the OTP resource.

Request bodies extend :class:`common.api.BaseRequestSchema`
(``extra="forbid"``); response bodies extend
:class:`common.api.BaseResponseSchema` (``from_attributes=True``). List
endpoints use :class:`common.api.BaseFilter` directly for pagination, so
no list-filter subclass is declared here.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import model_validator

from common.api import BaseRequestSchema, BaseResponseSchema


class OTPRequestSchema(BaseRequestSchema):
    """Request body for ``POST /otps``.

    At least one of ``phone`` or ``email`` must be provided. ``otp`` and
    ``expires_at`` are optional — omitted means the server generates both.

    Attributes:
        phone:      E.164 phone number, or ``None``.
        email:      Email address, or ``None``.
        otp:        Explicit OTP code to store, or ``None`` to auto-generate.
        expires_at: Explicit expiry timestamp, or ``None`` for the default TTL.
    """

    phone: str | None = None
    email: str | None = None
    otp: str | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def phone_or_email_required(self) -> OTPRequestSchema:
        """Validate that at least one identifier is provided."""
        if not self.phone and not self.email:
            raise ValueError("Provide at least one of: phone, email.")
        return self


class OTPCreateResponseSchema(BaseResponseSchema):
    """Response body for ``POST /otps``.

    ``otp`` and ``expires_at`` are always set after a create/reset, so they
    are required (non-nullable) here.

    Attributes:
        id:         PK of the OTP row.
        phone:      E.164 phone number, or ``null``.
        email:      Email address, or ``null``.
        otp:        The generated OTP code.
        expires_at: Timestamp when the code expires.
        is_valid:   Whether the code is still within its validity window.
    """

    id: int
    phone: str | None
    email: str | None
    otp: str
    expires_at: datetime
    is_valid: bool


class OTPResponseSchema(BaseResponseSchema):
    """Wire representation of an OTP row (list / get endpoints).

    Attributes:
        id:         PK of the OTP row.
        phone:      E.164 phone number, or ``null``.
        email:      Email address, or ``null``.
        otp:        The OTP code, or ``null``.
        expires_at: Expiry timestamp, or ``null``.
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
