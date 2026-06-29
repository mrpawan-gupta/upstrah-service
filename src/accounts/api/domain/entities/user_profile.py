"""Domain entity for the UserProfile aggregate (onboarding sidecar).

Represents the 1:1 demographic + notification-preference record attached
to a :class:`accounts.models.User`. ORM models are never exposed beyond
the infrastructure layer; this entity carries only the scalar attributes
the use cases and presentation layer need, including the few owning-user
identity fields the profile/``/auth/me`` responses surface (so callers
never need to join back to ``User`` across aggregates).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UserProfileEntity:
    """Immutable domain representation of the 1:1 ``UserProfile`` row.

    Carries the profile's own columns plus the owning user's identity
    scalars (resolved in the same query) so the presentation layer can
    render a user-centric response without a second round-trip.

    Attributes:
        user_id:                          PK of the owning ``User``.
        phone:                            Owning user's E.164 phone string.
        email:                            Owning user's login email.
        username:                         Owning user's username.
        is_active:                        Whether the account can log in.
        sex:                              ``"m"``, ``"f"``, ``"o"``, or ``None``.
        dob:                              ISO-8601 date (``"YYYY-MM-DD"``), or ``None``.
        role:                             Onboarding role, or ``None``.
        sub_role:                         Onboarding sub-role, or ``None``.
        is_whatsapp_notification_enabled: WhatsApp delivery opt-in.
        is_email_notification_enabled:    Email delivery opt-in.
        is_phone_notification_enabled:    SMS / voice delivery opt-in.
        created_at:                       Profile row creation timestamp.
        updated_at:                       Profile row last-modified timestamp.
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
