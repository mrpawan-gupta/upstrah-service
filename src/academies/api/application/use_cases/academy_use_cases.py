"""Use cases for the Academy aggregate.

Inherits the shared CRUD facade from :class:`common.api.BaseUseCase` and
overrides ``get`` / ``create`` / ``update`` / ``partial_update`` /
``delete`` / ``list`` to call the repository and map raw ORM rows into
``AcademyEntity`` via :class:`AcademyMapper`, so the presentation layer
works in domain terms only. ``partial_update`` drops unset (``None``)
fields so a PATCH never overwrites with nulls.
"""

from __future__ import annotations

from academies.api.application.dtos.academy_dtos import (
    AcademyCreateDTO,
    AcademyPatchDTO,
    AcademyUpdateDTO,
)
from academies.api.application.mappers.academy_mapper import AcademyMapper
from academies.api.domain.entities.academy import AcademyEntity
from academies.api.domain.repositories.academy_repository import IAcademyRepository
from common.api import BaseUseCase
from common.exceptions.exceptions import ResourceNotFoundError


class AcademyUseCases(BaseUseCase):
    """Business-logic facade for the Academy aggregate.

    Args:
        repository: Concrete :class:`IAcademyRepository` from the DI container.
    """

    def __init__(self, repository: IAcademyRepository) -> None:
        """Inject the repository dependency."""
        super().__init__(repository)

    async def _get_or_raise(self, academy_id: int) -> object:
        """Return the academy ORM row or raise ``ResourceNotFoundError``."""
        row = await self._repository.get(academy_id)
        if row is None:
            raise ResourceNotFoundError(f"Academy {academy_id} not found")
        return row

    async def create(self, dto: AcademyCreateDTO) -> AcademyEntity:
        """Create an academy owned by ``dto.created_by``.

        Args:
            dto: ``AcademyCreateDTO`` with the academy fields and owner.

        Returns:
            The created ``AcademyEntity``.
        """
        row = await self._repository.create(
            name=dto.name,
            sport=dto.sport,
            description=dto.description,
            city=dto.city,
            status=dto.status,
            created_by_id=dto.created_by,
        )
        return AcademyMapper.orm_to_entity(row)

    async def get(self, academy_id: int) -> AcademyEntity:
        """Retrieve a single academy by primary key.

        Args:
            academy_id: Primary key of the academy.

        Returns:
            ``AcademyEntity`` for the matching row.

        Raises:
            ResourceNotFoundError: No academy exists for ``academy_id``.
        """
        row = await self._get_or_raise(academy_id)
        return AcademyMapper.orm_to_entity(row)

    async def update(self, academy_id: int, dto: AcademyUpdateDTO) -> AcademyEntity:
        """Full replace (PUT) of an academy.

        Args:
            academy_id: Primary key of the academy.
            dto:        ``AcademyUpdateDTO`` with every mutable field set.

        Returns:
            The updated ``AcademyEntity``.

        Raises:
            ResourceNotFoundError: No academy exists for ``academy_id``.
        """
        await self._get_or_raise(academy_id)
        row = await self._repository.update(
            academy_id,
            name=dto.name,
            sport=dto.sport,
            description=dto.description,
            city=dto.city,
            status=dto.status,
        )
        return AcademyMapper.orm_to_entity(row)

    async def partial_update(
        self, academy_id: int, dto: AcademyPatchDTO
    ) -> AcademyEntity:
        """PATCH an academy — unset (``None``) fields are left unchanged.

        Args:
            academy_id: Primary key of the academy.
            dto:        ``AcademyPatchDTO`` with unset fields left ``None``.

        Returns:
            The updated ``AcademyEntity``.

        Raises:
            ResourceNotFoundError: No academy exists for ``academy_id``.
        """
        await self._get_or_raise(academy_id)
        fields = {k: v for k, v in dto.to_dict().items() if v is not None}
        row = await self._repository.partial_update(academy_id, **fields)
        return AcademyMapper.orm_to_entity(row)

    async def delete(self, academy_id: int) -> None:
        """Delete an academy by primary key.

        Args:
            academy_id: Primary key of the academy to delete.

        Raises:
            ResourceNotFoundError: No academy exists for ``academy_id``.
        """
        await self._get_or_raise(academy_id)
        await self._repository.delete(academy_id)

    async def list(
        self, *, limit: int, offset: int
    ) -> tuple[list[AcademyEntity], int]:
        """Return a paginated list of academies and the total count.

        Args:
            limit:  Max rows to return.
            offset: Rows to skip.

        Returns:
            Tuple of (list of ``AcademyEntity``, total count).
        """
        rows = await self._repository.list(
            limit=limit, offset=offset, order_by=["-created_at"]
        )
        total = await self._repository.count()
        return [AcademyMapper.orm_to_entity(r) for r in rows], total
