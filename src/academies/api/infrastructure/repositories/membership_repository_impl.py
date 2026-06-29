"""Django-ORM implementation of :class:`IMembershipRepository`.

Backs the contract with the ``academies.models.Membership`` model.
Inherits the shared async CRUD surface from
:class:`common.api.BaseRepository` (``get`` / ``create`` / ``list`` /
``count`` return raw ORM rows) and adds the ``set_status`` transition used
by the approve / reject flow. Data access only.
"""

from __future__ import annotations

from typing import Any

from academies.api.domain.repositories.membership_repository import (
    IMembershipRepository,
)
from academies.models import Membership
from common.api import BaseRepository


class MembershipRepositoryImpl(BaseRepository, IMembershipRepository):
    """Concrete Membership repository over ``academies.models.Membership``.

    Attributes:
        model:            The :class:`academies.models.Membership` ORM model.
        default_ordering: Default ``order_by`` for ``list`` queries.
    """

    model = Membership
    default_ordering = ["-created_at"]

    async def set_status(self, id_: int, *, status: str) -> Any:
        """Transition the membership row's ``status`` and return the row.

        Args:
            id_:    Primary key of the membership row.
            status: New status (``approved`` or ``rejected``).

        Returns:
            The updated ``Membership`` ORM row.
        """
        return await self.partial_update(id_, status=status)
