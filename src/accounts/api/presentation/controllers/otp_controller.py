"""Presentation-layer controller for OTP admin operations.

Thin facade over :class:`OTPUseCases`. Maps domain entities to response
dicts via :class:`OTPMapper`; contains no business logic, no ORM, and
never builds an ``APIResponse`` (the endpoint does that).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from accounts.api.application.mappers.otp_mapper import OTPMapper
from accounts.api.presentation.schemas.otp_schemas import OTPRequestSchema
from common.api import BaseFilter
from common.api.base_controller import BaseController
from common.api.response import OffsetPaginatedResponse

if TYPE_CHECKING:
    from accounts.api.application.use_cases.otp_use_cases import OTPUseCases


class OTPController(BaseController):
    """Facade over ``OTPUseCases`` for the OTP admin endpoints."""

    def __init__(self, use_cases: OTPUseCases) -> None:
        """Inject the use-case dependency."""
        super().__init__(use_cases)

    async def create(self, payload: OTPRequestSchema) -> dict:
        """Create or reset an OTP for the given phone (POST /otps).

        Args:
            payload: Validated ``OTPRequestSchema``.

        Returns:
            Serialised ``OTPCreateResponseSchema`` dict including the code.
        """
        entity = await self._use_cases.create(OTPMapper.schema_to_create_dto(payload))
        return OTPMapper.entity_to_create_response(entity)

    async def list(
        self, *, filter: BaseFilter
    ) -> tuple[list[dict], OffsetPaginatedResponse]:
        """Return a paginated list of OTP rows (GET /otps).

        Args:
            filter: Pagination / sort parameters.

        Returns:
            Tuple of (serialised items, pagination metadata).
        """
        entities, total = await self._use_cases.list(filter)
        items = [OTPMapper.entity_to_response(e) for e in entities]
        meta = OffsetPaginatedResponse(
            limit=filter.limit,
            offset=filter.offset,
            total=total,
            returned=len(items),
            has_more=filter.offset + len(items) < total,
        )
        return items, meta

    async def get(self, otp_id: int) -> dict:
        """Retrieve a single OTP row by primary key (GET /otps/{id}).

        Args:
            otp_id: Primary key of the OTP row.

        Returns:
            Serialised OTP dict.
        """
        entity = await self._use_cases.get(otp_id)
        return OTPMapper.entity_to_response(entity)

    async def delete(self, otp_id: int) -> None:
        """Invalidate (delete) the OTP row by primary key (DELETE /otps/{id}).

        Args:
            otp_id: Primary key of the OTP row to invalidate.
        """
        await self._use_cases.delete(otp_id)
