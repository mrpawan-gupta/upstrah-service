"""Django-ORM implementation of :class:`IUserProfileRepository`.

Operates on the 1:1 :class:`accounts.models.UserProfile` sidecar attached
to each :class:`accounts.models.User`. Inherits the shared async CRUD
surface from :class:`common.api.BaseRepository` (returning raw ORM rows)
and adds two ``UserProfile``-specific methods keyed by the owning
``user_id``: ``get_by_user`` and ``upsert_by_user``. The latter creates
rows lazily via ``aupdate_or_create`` so callers never pre-seed a profile.
Both selektor the owning ``user`` so the mapper can read identity fields
without a second query. Data access only.
"""

from __future__ import annotations

import datetime as dt

from accounts.api.domain.repositories.user_profile_repository import (
    IUserProfileRepository,
)
from accounts.models import UserProfile
from common.api import BaseRepository


class UserProfileRepositoryImpl(BaseRepository, IUserProfileRepository):
    """Concrete Django-backed repository for ``UserProfile`` persistence.

    Attributes:
        model:            The :class:`accounts.models.UserProfile` ORM model.
        default_ordering: Default ``order_by`` for ``list`` queries.
    """

    model = UserProfile
    default_ordering = ["id"]

    async def get_by_user(self, user_id: int) -> UserProfile | None:
        """Return the profile (with owning user) for ``user_id``, or ``None``."""
        try:
            return await UserProfile.objects.select_related("user").aget(
                user_id=user_id
            )
        except UserProfile.DoesNotExist:
            return None

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
        (or default) values. Re-fetches with ``user`` selected so the
        mapper can read identity fields.
        """
        defaults: dict = {}
        if sex is not None:
            defaults["sex"] = sex
        if dob is not None:
            defaults["dob"] = dt.date.fromisoformat(dob)
        if role is not None:
            defaults["role"] = role
        if sub_role is not None:
            defaults["sub_role"] = sub_role
        if is_whatsapp_notification_enabled is not None:
            defaults["is_whatsapp_notification_enabled"] = (
                is_whatsapp_notification_enabled
            )
        if is_email_notification_enabled is not None:
            defaults["is_email_notification_enabled"] = is_email_notification_enabled
        if is_phone_notification_enabled is not None:
            defaults["is_phone_notification_enabled"] = is_phone_notification_enabled

        await UserProfile.objects.aupdate_or_create(
            user_id=user_id, defaults=defaults
        )
        return await UserProfile.objects.select_related("user").aget(user_id=user_id)
