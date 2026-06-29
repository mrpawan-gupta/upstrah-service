"""Use cases for the Membership aggregate.

Inherits the shared CRUD facade from :class:`common.api.BaseUseCase` and
adds the apply / list / approve / reject operations. ``apply`` persists a
``pending`` row; ``approve`` / ``reject`` transition the status. Raw ORM
rows are mapped to ``MembershipEntity`` via :class:`MembershipMapper` so the
presentation layer works in domain terms only.
"""

from __future__ import annotations

from academies.api.application.dtos.membership_dtos import MembershipCreateDTO
from academies.api.application.mappers.membership_mapper import MembershipMapper
from academies.api.domain.entities.membership import MembershipEntity
from academies.api.domain.repositories.membership_repository import (
    IMembershipRepository,
)
from academies.constants import MembershipStatus
from common.api import BaseUseCase
from common.exceptions.exceptions import (
    DuplicateResourceError,
    ResourceNotFoundError,
)


class MembershipUseCases(BaseUseCase):
    """Business-logic facade for the Membership aggregate.

    Args:
        repository: Concrete :class:`IMembershipRepository` from the DI
            container.
    """

    def __init__(self, repository: IMembershipRepository) -> None:
        """Inject the repository dependency."""
        super().__init__(repository)

    async def _get_or_raise(self, membership_id: int) -> object:
        """Return the membership ORM row or raise ``ResourceNotFoundError``."""
        row = await self._repository.get(membership_id)
        if row is None:
            raise ResourceNotFoundError(f"Membership {membership_id} not found")
        return row

    async def apply(self, dto: MembershipCreateDTO) -> MembershipEntity:
        """Apply for membership — persists a ``pending`` row.

        Args:
            dto: ``MembershipCreateDTO`` with user, academy, and role.

        Returns:
            The created ``MembershipEntity`` (status ``pending``).

        Raises:
            DuplicateResourceError: The user already applied to this academy.
        """
        try:
            row = await self._repository.create(
                user_id=dto.user_id,
                academy_id=dto.academy_id,
                role=dto.role,
                status=MembershipStatus.PENDING.value,
            )
        except Exception as exc:  # unique_together (user, academy) violation
            raise DuplicateResourceError(
                "A membership for this user and academy already exists"
            ) from exc
        return MembershipMapper.orm_to_entity(row)

    async def list_for_academy(
        self, academy_id: int, *, limit: int, offset: int
    ) -> tuple[list[MembershipEntity], int]:
        """Return a paginated list of memberships for an academy.

        Args:
            academy_id: Primary key of the academy.
            limit:      Max rows to return.
            offset:     Rows to skip.

        Returns:
            Tuple of (list of ``MembershipEntity``, total count).
        """
        rows = await self._repository.list(
            limit=limit,
            offset=offset,
            order_by=["-created_at"],
            academy_id=academy_id,
        )
        total = await self._repository.count(academy_id=academy_id)
        return [MembershipMapper.orm_to_entity(r) for r in rows], total

    async def approve(self, membership_id: int) -> MembershipEntity:
        """Approve a membership application (status → ``approved``).

        Args:
            membership_id: Primary key of the membership row.

        Returns:
            The updated ``MembershipEntity``.

        Raises:
            ResourceNotFoundError: No membership exists for ``membership_id``.
        """
        await self._get_or_raise(membership_id)
        row = await self._repository.set_status(
            membership_id, status=MembershipStatus.APPROVED.value
        )
        return MembershipMapper.orm_to_entity(row)

    async def reject(self, membership_id: int) -> MembershipEntity:
        """Reject a membership application (status → ``rejected``).

        Args:
            membership_id: Primary key of the membership row.

        Returns:
            The updated ``MembershipEntity``.

        Raises:
            ResourceNotFoundError: No membership exists for ``membership_id``.
        """
        await self._get_or_raise(membership_id)
        row = await self._repository.set_status(
            membership_id, status=MembershipStatus.REJECTED.value
        )
        return MembershipMapper.orm_to_entity(row)
