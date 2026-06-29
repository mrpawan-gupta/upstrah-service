"""Presentation-layer controller for the Academy endpoints.

Thin facade over :class:`AcademyUseCases`: maps request schemas to DTOs via
:class:`AcademyMapper`, calls one use-case method, and maps the returned
entity to a response dict. No business logic, no ORM, no ``APIResponse``.
"""

from __future__ import annotations

from academies.api.application.mappers.academy_mapper import AcademyMapper
from academies.api.application.use_cases.academy_use_cases import AcademyUseCases
from academies.api.presentation.schemas.academy_schemas import (
    AcademyCreateSchema,
    AcademyPatchSchema,
    AcademyUpdateSchema,
)
from common.api.base_controller import BaseController
from common.api.response import OffsetPaginatedResponse


class AcademyController(BaseController):
    """Facade over ``AcademyUseCases`` for the academy endpoints."""

    def __init__(self, use_cases: AcademyUseCases) -> None:
        """Inject the use-case dependency."""
        super().__init__(use_cases)
        self._use_cases = use_cases

    async def create(self, payload: AcademyCreateSchema, *, created_by: int) -> dict:
        """Create an academy owned by ``created_by`` (POST).

        Args:
            payload:    Validated create schema.
            created_by: PK of the owning user.

        Returns:
            Serialised ``AcademyResponseSchema`` dict.
        """
        dto = AcademyMapper.schema_to_dto(payload, created_by=created_by)
        entity = await self._use_cases.create(dto)
        return AcademyMapper.entity_to_response(entity)

    async def get(self, academy_id: int) -> dict:
        """Retrieve a single academy by primary key (GET).

        Args:
            academy_id: Primary key of the academy.

        Returns:
            Serialised ``AcademyResponseSchema`` dict.
        """
        entity = await self._use_cases.get(academy_id)
        return AcademyMapper.entity_to_response(entity)

    async def update(self, academy_id: int, payload: AcademyUpdateSchema) -> dict:
        """Full replace of an academy (PUT).

        Args:
            academy_id: Primary key of the academy.
            payload:    Validated PUT schema (all fields required).

        Returns:
            Serialised ``AcademyResponseSchema`` dict.
        """
        dto = AcademyMapper.update_schema_to_dto(payload)
        entity = await self._use_cases.update(academy_id, dto)
        return AcademyMapper.entity_to_response(entity)

    async def partial_update(
        self, academy_id: int, payload: AcademyPatchSchema
    ) -> dict:
        """Patch an academy (PATCH) — unset fields unchanged.

        Args:
            academy_id: Primary key of the academy.
            payload:    Validated PATCH schema.

        Returns:
            Serialised ``AcademyResponseSchema`` dict.
        """
        dto = AcademyMapper.patch_schema_to_dto(payload)
        entity = await self._use_cases.partial_update(academy_id, dto)
        return AcademyMapper.entity_to_response(entity)

    async def delete(self, academy_id: int) -> None:
        """Delete an academy by primary key (DELETE).

        Args:
            academy_id: Primary key of the academy to delete.
        """
        await self._use_cases.delete(academy_id)

    async def list(
        self, *, offset: int, limit: int
    ) -> tuple[list[dict], OffsetPaginatedResponse]:
        """Return a paginated list of academies (GET).

        Args:
            offset: Pagination offset.
            limit:  Items per page.

        Returns:
            Tuple of (serialised items, pagination metadata).
        """
        entities, total = await self._use_cases.list(limit=limit, offset=offset)
        items = [AcademyMapper.entity_to_response(e) for e in entities]
        meta = OffsetPaginatedResponse(
            limit=limit,
            offset=offset,
            total=total,
            returned=len(items),
            has_more=offset + len(items) < total,
        )
        return items, meta
