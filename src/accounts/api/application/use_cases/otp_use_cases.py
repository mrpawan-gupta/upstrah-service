"""Use cases for OTP admin operations.

Inherits the shared CRUD facade from :class:`common.api.BaseUseCase` and
overrides ``get`` / ``list`` / ``create`` / ``delete`` to call the
repository and map raw ORM rows into ``OTPEntity`` via
:class:`OTPMapper`, so the presentation layer works in domain terms only.
``create`` carries the OTP-specific get-or-create + regenerate logic. The
phone-OTP login flow (send/verify) lives in ``AuthUseCases``.
"""

from __future__ import annotations

from accounts.api.application.dtos.otp_dtos import OTPCreateDTO
from accounts.api.application.mappers.otp_mapper import OTPMapper
from accounts.api.domain.entities.otp import OTPEntity
from accounts.api.domain.repositories.otp_repository import IOTPRepository
from common.api import BaseFilter, BaseUseCase
from common.exceptions.exceptions import ResourceNotFoundError


class OTPUseCases(BaseUseCase):
    """Admin use cases for the OTP aggregate.

    Provides read and create/invalidate operations. Send/verify remain in
    ``AuthUseCases`` to preserve the auth flow contract.

    Args:
        repository: Concrete ``IOTPRepository`` provided by the DI container.
    """

    def __init__(self, repository: IOTPRepository) -> None:
        """Inject the repository dependency."""
        super().__init__(repository)

    async def _get_or_raise(self, otp_id: int) -> object:
        """Return the OTP ORM row for ``otp_id`` or raise ``ResourceNotFoundError``."""
        row = await self._repository.get(otp_id)
        if row is None:
            raise ResourceNotFoundError("OTP not found")
        return row

    async def create(self, dto: OTPCreateDTO) -> OTPEntity:
        """Create or reset an OTP for the given phone.

        When a row already exists for the phone it is reset (new code, new
        expiry); otherwise a new row is created.

        Args:
            dto: ``OTPCreateDTO`` with ``phone`` set.

        Returns:
            ``OTPEntity`` representing the created or reset OTP row.
        """
        otp_obj, _ = await self._repository.get_or_create(dto.phone)
        otp_obj.set_otp_and_validity()
        if dto.otp is not None:
            otp_obj.otp = dto.otp
        if dto.expires_at is not None:
            otp_obj.expires_at = dto.expires_at
        await self._repository.save(otp_obj)
        return OTPMapper.orm_to_entity(otp_obj)

    async def list(self, filter: BaseFilter) -> tuple[list[OTPEntity], int]:
        """Return a paginated list of OTP rows and the total count.

        Args:
            filter: Pagination / sort parameters.

        Returns:
            Tuple of (list of ``OTPEntity``, total count).
        """
        rows = await self._repository.list(
            limit=filter.limit,
            offset=filter.offset,
            order_by=filter.to_order_by(),
            **filter.to_orm_filters(),
        )
        total = await self._repository.count(**filter.to_orm_filters())
        return [OTPMapper.orm_to_entity(r) for r in rows], total

    async def get(self, otp_id: int) -> OTPEntity:
        """Retrieve a single OTP row by primary key.

        Args:
            otp_id: Primary key of the OTP row.

        Returns:
            ``OTPEntity`` for the matching row.

        Raises:
            ResourceNotFoundError: No OTP row exists for ``otp_id``.
        """
        row = await self._get_or_raise(otp_id)
        return OTPMapper.orm_to_entity(row)

    async def delete(self, otp_id: int) -> None:
        """Invalidate (hard-delete) the OTP row by primary key.

        Args:
            otp_id: Primary key of the OTP row to invalidate.

        Raises:
            ResourceNotFoundError: No OTP row exists for ``otp_id``.
        """
        await self._get_or_raise(otp_id)
        await self._repository.delete(otp_id)
