"""Data Transfer Objects for the UserProfile (onboarding) application layer.

Defines the dataclass boundaries between the presentation layer and the
``UserProfile`` use-case facade. Each extends
:class:`common.api.BaseModelDTO`; ``UpdateUserProfileDTO`` uses ``| None``
defaults so a PATCH leaves unset fields unchanged, and
``UserProfileResponseDTO`` is the read boundary serialised to the response.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from common.api import BaseModelDTO


@dataclass
class UpdateUserProfileDTO(BaseModelDTO):
    """Carry optional fields for a partial update of a user's profile row.

    ``None`` means "leave unchanged". The presentation layer ensures at
    least one field is non-``None`` before constructing this DTO.

    Attributes:
        sex:                              New sex code, or ``None``.
        dob:                              New ``YYYY-MM-DD`` date string, or ``None``.
        role:                             New onboarding role, or ``None``.
        sub_role:                         New onboarding sub-role, or ``None``.
        is_whatsapp_notification_enabled: WhatsApp opt-in, or ``None``.
        is_email_notification_enabled:    Email opt-in, or ``None``.
        is_phone_notification_enabled:    SMS / voice opt-in, or ``None``.
    """

    sex: str | None = None
    dob: str | None = None
    role: str | None = None
    sub_role: str | None = None
    is_whatsapp_notification_enabled: bool | None = None
    is_email_notification_enabled: bool | None = None
    is_phone_notification_enabled: bool | None = None


@dataclass
class UserProfileResponseDTO(BaseModelDTO):
    """Read representation of a user's profile returned by use cases.

    Attributes:
        user_id:                          PK of the owning user.
        phone:                            Owning user's E.164 phone.
        email:                            Owning user's login email.
        username:                         Owning user's username.
        is_active:                        Whether the account can log in.
        sex:                              Sex code, or ``None``.
        dob:                              ``YYYY-MM-DD`` date string, or ``None``.
        role:                             Onboarding role, or ``None``.
        sub_role:                         Onboarding sub-role, or ``None``.
        is_whatsapp_notification_enabled: WhatsApp opt-in.
        is_email_notification_enabled:    Email opt-in.
        is_phone_notification_enabled:    SMS / voice opt-in.
        created_at:                       Profile creation timestamp.
        updated_at:                       Profile last-modified timestamp.
    """

    user_id: int
    phone: str
    email: str
    username: str
    is_active: bool
    sex: str | None
    dob: str | None
    role: str | None
    sub_role: str | None
    is_whatsapp_notification_enabled: bool
    is_email_notification_enabled: bool
    is_phone_notification_enabled: bool
    created_at: datetime
    updated_at: datetime
