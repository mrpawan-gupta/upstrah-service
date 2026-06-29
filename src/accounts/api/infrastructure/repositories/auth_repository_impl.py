"""Django-ORM implementation of :class:`IAuthRepository`.

Phone-OTP only — no allauth / SocialAccount, no email-password. Resolves
or creates a user purely from the verified phone number, and assembles the
JWT claim payload from the user's groups and permissions. Data access
only: no business rules, no HTTP, no Celery.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

from accounts.api.domain.repositories.auth_repository import IAuthRepository
from accounts.models import PhoneNumber

if TYPE_CHECKING:
    from accounts.models import User


class AuthRepositoryImpl(IAuthRepository):
    """Auth repository backed by the Django ORM (phone-OTP flow)."""

    def __init__(self) -> None:
        """Resolve the active user model once at construction."""
        self._User = get_user_model()

    async def get_user_by_id(self, user_id: int | str) -> User | None:
        """Return the ``User`` with the given PK, or ``None`` if not found."""
        try:
            return await self._User.objects.aget(pk=user_id)
        except self._User.DoesNotExist:
            return None

    async def get_or_create_user_by_phone(self, phone: str) -> tuple[User, bool]:
        """Return ``(user, created)`` for the given phone number.

        Resolution order: an existing verified ``PhoneNumber`` row, then the
        ``User.phone`` convenience column, then create a new phone-only user
        with a verified ``PhoneNumber`` row.

        Args:
            phone: E.164 phone number that completed an OTP challenge.

        Returns:
            Tuple of (``User`` instance, created flag).
        """
        existing = (
            await PhoneNumber.objects.select_related("user")
            .filter(phone=phone)
            .afirst()
        )
        if existing is not None:
            return existing.user, False

        user = await self._User.objects.filter(phone=phone).afirst()
        if user is not None:
            await PhoneNumber.objects.aget_or_create(
                phone=phone, defaults={"user": user, "verified": True}
            )
            return user, False

        # create_user is a custom manager method (no native async equivalent).
        user = await sync_to_async(self._User.objects.create_user)(
            phone=phone, password=None
        )
        await PhoneNumber.objects.aget_or_create(
            phone=phone, defaults={"user": user, "verified": True}
        )
        return user, True

    async def get_user_token_claims(self, user_id: int | str) -> dict[str, Any]:
        """Build the JWT ``user_data`` payload for ``user_id``.

        Returns a dict with ``is_superuser``, ``is_staff``, ``roles``
        (group names), and ``scopes`` (``app_label.codename`` permission
        strings from groups + direct assignments).
        """
        try:
            user = await self._User.objects.prefetch_related(
                "groups",
                "groups__permissions__content_type",
                "user_permissions__content_type",
            ).aget(pk=user_id)
        except self._User.DoesNotExist:
            return {
                "is_superuser": False,
                "is_staff": False,
                "roles": [],
                "scopes": [],
            }

        roles = sorted({g.name for g in user.groups.all()})
        scopes: set[str] = set()
        for group in user.groups.all():
            for perm in group.permissions.all():
                scopes.add(f"{perm.content_type.app_label}.{perm.codename}")
        for perm in user.user_permissions.all():
            scopes.add(f"{perm.content_type.app_label}.{perm.codename}")

        return {
            "is_superuser": bool(user.is_superuser),
            "is_staff": bool(user.is_staff),
            "roles": roles,
            "scopes": sorted(scopes),
        }
