"""Presentation-layer controller for the 1:1 UserProfile endpoints.

Thin facade over :class:`UserProfileUseCases`: maps the PATCH schema to a
DTO via :class:`UserProfileMapper`, calls one use-case method, and maps
the returned entity to a response dict. No business logic, no ORM, no
``APIResponse`` here.
"""

from __future__ import annotations

from accounts.api.application.mappers.user_profile_mapper import UserProfileMapper
from accounts.api.application.use_cases.user_profile_use_cases import (
    UserProfileUseCases,
)
from accounts.api.presentation.schemas.user_profile_schemas import (
    UserProfilePatchSchema,
)
from common.api.base_controller import BaseController


class UserProfileController(BaseController):
    """Facade over ``UserProfileUseCases`` for the profile endpoints."""

    def __init__(self, use_cases: UserProfileUseCases) -> None:
        """Inject the use-case dependency."""
        super().__init__(use_cases)
        self._use_cases = use_cases

    async def get(self, user_id: int) -> dict:
        """Return the profile for ``user_id`` (GET).

        Args:
            user_id: PK of the owning user.

        Returns:
            Serialised ``UserProfileResponseSchema`` dict.
        """
        entity = await self._use_cases.get(user_id)
        return UserProfileMapper.entity_to_response(entity)

    async def partial_update(
        self, user_id: int, payload: UserProfilePatchSchema
    ) -> dict:
        """Patch the profile for ``user_id`` (PATCH) — unset fields unchanged.

        Args:
            user_id: PK of the owning user.
            payload: Validated PATCH schema (at least one field set).

        Returns:
            Serialised ``UserProfileResponseSchema`` dict.
        """
        dto = UserProfileMapper.schema_to_update_dto(payload)
        entity = await self._use_cases.update(user_id, dto)
        return UserProfileMapper.entity_to_response(entity)
