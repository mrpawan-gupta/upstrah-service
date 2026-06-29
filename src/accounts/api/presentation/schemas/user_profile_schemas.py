"""Pydantic request/response schemas for the UserProfile (onboarding) endpoints.

Covers ``GET /users/{user_id}/profile`` and ``PATCH
/users/{user_id}/profile``. The PATCH schema makes every field
``| None = None`` (unset = leave unchanged) and validates ``sex`` / ``dob``
/ ``role`` / ``sub_role`` here, never in the controller.
"""

from __future__ import annotations

import re
from datetime import datetime

from django.utils.translation import gettext_lazy as _
from pydantic import Field, field_validator, model_validator

from accounts.constants import Role, Sex, SubRole
from common.api import BaseRequestSchema, BaseResponseSchema

_SEX_VALUES = {c.value for c in Sex}
_ROLE_VALUES = {c.value for c in Role}
_SUB_ROLE_VALUES = {c.value for c in SubRole}


class ProfileNestedSchema(BaseResponseSchema):
    """Onboarding data block nested inside the user-profile response.

    Attributes:
        sex:                              ``"m"``, ``"f"``, ``"o"``, or ``null``.
        dob:                              ISO-8601 date string, or ``null``.
        role:                             Onboarding role, or ``null``.
        sub_role:                         Onboarding sub-role, or ``null``.
        is_whatsapp_notification_enabled: WhatsApp delivery opt-in.
        is_email_notification_enabled:    Email delivery opt-in.
        is_phone_notification_enabled:    SMS / voice delivery opt-in.
        created_at:                       Profile creation timestamp.
        updated_at:                       Profile last-modified timestamp.
    """

    sex: str | None = Field(None, description=str(_("Sex: 'm', 'f', 'o', or null.")))
    dob: str | None = Field(
        None, description=str(_("Date of birth (YYYY-MM-DD) or null."))
    )
    role: str | None = Field(None, description=str(_("Onboarding role, or null.")))
    sub_role: str | None = Field(
        None, description=str(_("Onboarding sub-role, or null."))
    )
    is_whatsapp_notification_enabled: bool = Field(
        ..., description=str(_("WhatsApp delivery opt-in."))
    )
    is_email_notification_enabled: bool = Field(
        ..., description=str(_("Email delivery opt-in."))
    )
    is_phone_notification_enabled: bool = Field(
        ..., description=str(_("SMS / voice delivery opt-in."))
    )
    created_at: datetime = Field(
        ..., description=str(_("Timestamp when the profile was created."))
    )
    updated_at: datetime = Field(
        ..., description=str(_("Timestamp of the last profile update."))
    )


class UserProfileResponseSchema(BaseResponseSchema):
    """User-centric response for the profile endpoints.

    User identity fields sit at the top level; the onboarding profile is
    nested under ``profile``.

    Attributes:
        user_id:   PK of the ``User`` record.
        phone:     E.164 phone string.
        email:     Login email address.
        username:  Username (Snowflake-derived).
        is_active: Whether the account can log in.
        profile:   Nested onboarding profile.
    """

    user_id: int = Field(..., description=str(_("PK of the owning user.")))
    phone: str = Field(..., description=str(_("E.164 phone number.")))
    email: str = Field(..., description=str(_("Login email address.")))
    username: str = Field(..., description=str(_("Username.")))
    is_active: bool = Field(..., description=str(_("Whether the account can log in.")))
    profile: ProfileNestedSchema = Field(
        ..., description=str(_("Nested onboarding profile."))
    )


class UserProfilePatchSchema(BaseRequestSchema):
    """Request body for ``PATCH /users/{user_id}/profile``.

    All fields optional; at least one must be provided. Unset fields are
    left unchanged. Lazily creates the ``UserProfile`` row on first write.
    """

    sex: str | None = Field(
        None, description=str(_("Sex: 'm' (male), 'f' (female), or 'o' (other)."))
    )
    dob: str | None = Field(
        None, description=str(_("Date of birth in YYYY-MM-DD format."))
    )
    role: str | None = Field(
        None, description=str(_("Onboarding role (customer/agent/partner)."))
    )
    sub_role: str | None = Field(
        None, description=str(_("Onboarding sub-role (individual/business/broker)."))
    )
    is_whatsapp_notification_enabled: bool | None = Field(
        None, description=str(_("Toggle WhatsApp delivery opt-in."))
    )
    is_email_notification_enabled: bool | None = Field(
        None, description=str(_("Toggle email delivery opt-in."))
    )
    is_phone_notification_enabled: bool | None = Field(
        None, description=str(_("Toggle SMS / voice delivery opt-in."))
    )

    @field_validator("sex", mode="after")
    @classmethod
    def validate_sex(cls, v: str | None) -> str | None:
        """Validate that sex is one of the accepted single-character codes."""
        if v is not None and v not in _SEX_VALUES:
            raise ValueError(
                str(_("sex must be one of: m (male), f (female), o (other)."))
            )
        return v

    @field_validator("dob", mode="after")
    @classmethod
    def validate_dob(cls, v: str | None) -> str | None:
        """Validate that dob is in YYYY-MM-DD format."""
        if v is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError(
                str(_("dob must be in YYYY-MM-DD format (e.g. 1990-05-15)."))
            )
        return v

    @field_validator("role", mode="after")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        """Validate that role is one of the accepted onboarding roles."""
        if v is not None and v not in _ROLE_VALUES:
            raise ValueError(
                str(_("role must be one of: {choices}.")).format(
                    choices=", ".join(sorted(_ROLE_VALUES))
                )
            )
        return v

    @field_validator("sub_role", mode="after")
    @classmethod
    def validate_sub_role(cls, v: str | None) -> str | None:
        """Validate that sub_role is one of the accepted onboarding sub-roles."""
        if v is not None and v not in _SUB_ROLE_VALUES:
            raise ValueError(
                str(_("sub_role must be one of: {choices}.")).format(
                    choices=", ".join(sorted(_SUB_ROLE_VALUES))
                )
            )
        return v

    @model_validator(mode="after")
    def at_least_one_field(self) -> UserProfilePatchSchema:
        """Validate that at least one field is provided."""
        if all(
            f is None
            for f in (
                self.sex,
                self.dob,
                self.role,
                self.sub_role,
                self.is_whatsapp_notification_enabled,
                self.is_email_notification_enabled,
                self.is_phone_notification_enabled,
            )
        ):
            raise ValueError(
                str(
                    _(
                        "Provide at least one of: sex, dob, role, sub_role, "
                        "is_whatsapp_notification_enabled, "
                        "is_email_notification_enabled, "
                        "is_phone_notification_enabled."
                    )
                )
            )
        return self
