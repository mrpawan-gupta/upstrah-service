"""Abstract repository interface for the 1:1 UserProfile (onboarding).

Defines the ABC consumed by the use-case layer: get / upsert the single
demographic + role row per :class:`accounts.models.User`. Pure
``abc.ABC`` — no Django import; the implementation pairs it with
:class:`common.api.BaseRepository`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from accounts.models import UserProfile


class IUserProfileRepository(ABC):
    """Abstract interface for ``UserProfile`` persistence operations."""

    @abstractmethod
    async def get_by_user(self, user_id: int) -> UserProfile | None:
        """Return the profile row (with owning user) for ``user_id``, or ``None``."""

    @abstractmethod
    async def upsert_by_user(
        self,
        user_id: int,
        *,
        sex: str | None = None,
        dob: str | None = None,
        role: str | None = None,
        sub_role: str | None = None,
        is_whatsapp_notification_enabled: bool | None = None,
        is_email_notification_enabled: bool | None = None,
        is_phone_notification_enabled: bool | None = None,
    ) -> UserProfile:
        """Create or update the profile row for ``user_id``.

        Only non-``None`` fields are written; others retain their current
        (or default) values. Returns the row (with its owning user
        selected) post-write.

        Args:
            user_id:                          PK of the owning ``User``.
            sex:                              ``"m"``, ``"f"``, ``"o"``, or ``None``.
            dob:                              ``YYYY-MM-DD`` string, or ``None``.
            role:                             Onboarding role, or ``None``.
            sub_role:                         Onboarding sub-role, or ``None``.
            is_whatsapp_notification_enabled: Toggle or ``None``.
            is_email_notification_enabled:    Toggle or ``None``.
            is_phone_notification_enabled:    Toggle or ``None``.
        """
