"""Presentation-layer controller for the Membership endpoints.

Thin facade over :class:`MembershipUseCases`: maps the create schema to a
DTO via :class:`MembershipMapper`, calls one use-case method, and maps the
returned entity to a response dict. The approve / reject transitions are
domain methods the base CRUD surface cannot carry, so they are added as
siblings. No business logic, no ORM, no ``APIResponse``.
"""

from __future__ import annotations

from academies.api.application.mappers.membership_mapper import MembershipMapper
from academies.api.application.use_cases.membership_use_cases import (
    MembershipUseCases,
)
from academies.api.presentation.schemas.membership_schemas import (
    MembershipCreateSchema,
)
from common.api.base_controller import BaseController
from common.api.response import OffsetPaginatedResponse


class MembershipController(BaseController):
    """Facade over ``MembershipUseCases`` for the membership endpoints."""

    def __init__(self, use_cases: MembershipUseCases) -> None:
        """Inject the use-case dependency."""
        super().__init__(use_cases)
        self._use_cases = use_cases

    async def apply(
        self, payload: MembershipCreateSchema, *, user_id: int, academy_id: int
    ) -> dict:
        """Apply for membership (POST) — persists a ``pending`` row.

        Args:
            payload:    Validated create schema (requested role).
            user_id:    PK of the applying user (from the caller token).
            academy_id: PK of the academy applied to (from the path).

        Returns:
            Serialised ``MembershipResponseSchema`` dict (status ``pending``).
        """
        dto = MembershipMapper.schema_to_dto(
            payload, user_id=user_id, academy_id=academy_id
        )
        entity = await self._use_cases.apply(dto)
        return MembershipMapper.entity_to_response(entity)

    async def list_for_academy(
        self, academy_id: int, *, offset: int, limit: int
    ) -> tuple[list[dict], OffsetPaginatedResponse]:
        """Return a paginated list of an academy's memberships (GET).

        Args:
            academy_id: Primary key of the academy.
            offset:     Pagination offset.
            limit:      Items per page.

        Returns:
            Tuple of (serialised items, pagination metadata).
        """
        entities, total = await self._use_cases.list_for_academy(
            academy_id, limit=limit, offset=offset
        )
        items = [MembershipMapper.entity_to_response(e) for e in entities]
        meta = OffsetPaginatedResponse(
            limit=limit,
            offset=offset,
            total=total,
            returned=len(items),
            has_more=offset + len(items) < total,
        )
        return items, meta

    async def approve(self, membership_id: int) -> dict:
        """Approve a membership application (status → ``approved``).

        Args:
            membership_id: Primary key of the membership row.

        Returns:
            Serialised ``MembershipResponseSchema`` dict.
        """
        entity = await self._use_cases.approve(membership_id)
        return MembershipMapper.entity_to_response(entity)

    async def reject(self, membership_id: int) -> dict:
        """Reject a membership application (status → ``rejected``).

        Args:
            membership_id: Primary key of the membership row.

        Returns:
            Serialised ``MembershipResponseSchema`` dict.
        """
        entity = await self._use_cases.reject(membership_id)
        return MembershipMapper.entity_to_response(entity)
