"""Django-ORM implementation of the OTP repository.

Backs :class:`IOTPRepository` with the ``accounts.models.OTP`` model. It
inherits the shared async CRUD surface from
:class:`common.api.BaseRepository` — ``get`` / ``list`` / ``count`` /
``delete`` are the unchanged base methods (each returns a raw ORM row;
mapping to entities is the use case's job). The class sets ``model`` and
``default_ordering`` and adds the OTP-specific query methods the auth /
admin flows rely on. Data access only.
"""

from __future__ import annotations

from typing import Any

from accounts.api.domain.repositories.otp_repository import IOTPRepository
from accounts.models import OTP
from common.api import BaseRepository


class OTPRepositoryImpl(BaseRepository, IOTPRepository):
    """Concrete OTP repository over ``accounts.models.OTP``.

    Attributes:
        model:            The :class:`accounts.models.OTP` ORM model.
        default_ordering: Default ``order_by`` for ``list`` queries.
    """

    model = OTP
    default_ordering = ["-created_at"]

    async def get_or_create(self, phone: str) -> tuple[Any, bool]:
        """Return ``(otp_obj, created)`` for the given phone number."""
        return await OTP.objects.aget_or_create(phone=phone, defaults={})

    async def save(self, otp_obj: Any) -> None:
        """Persist changes to an existing OTP row."""
        await otp_obj.asave()

    async def get_by_phone(self, phone: str) -> Any | None:
        """Return the OTP row for the given phone, or ``None``."""
        try:
            return await OTP.objects.aget(phone=phone)
        except OTP.DoesNotExist:
            return None

    async def delete_row(self, otp_obj: Any) -> None:
        """Hard-delete a resolved OTP row instance (single-use consume)."""
        await otp_obj.adelete()
