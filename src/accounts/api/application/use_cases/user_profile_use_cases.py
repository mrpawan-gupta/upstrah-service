"""Use cases for the UserProfile (onboarding) aggregate.

Provides get and update (upsert) operations on the 1:1 onboarding
sidecar. Rows are created lazily on first read/write so callers never
need to seed defaults — the API response shape stays stable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from accounts.api.application.mappers.user_profile_mapper import UserProfileMapper
from accounts.api.domain.entities.user_profile import UserProfileEntity
from common.api import BaseUseCase
from common.exceptions.exceptions import ResourceNotFoundError

if TYPE_CHECKING:
    from accounts.api.application.dtos.user_profile_dtos import UpdateUserProfileDTO
    from accounts.api.domain.repositories.user_profile_repository import (
        IUserProfileRepository,
    )

logger = structlog.get_logger(__name__)


class UserProfileUseCases(BaseUseCase):
    """Business-logic facade for the 1:1 UserProfile aggregate.

    Args:
        repository: Concrete :class:`IUserProfileRepository` provided by
            the DI container.
    """

    def __init__(self, repository: IUserProfileRepository) -> None:
        """Inject the repository dependency."""
        super().__init__(repository)

    async def get(self, user_id: int) -> UserProfileEntity:
        """Return the profile for ``user_id``, creating defaults if absent.

        Args:
            user_id: PK of the owning user.

        Returns:
            ``UserProfileEntity`` for the user.

        Raises:
            ResourceNotFoundError: The user does not exist (upsert would
                violate the FK), surfaced as a 404.
        """
        orm = await self._repository.get_by_user(user_id)
        if orm is None:
            try:
                orm = await self._repository.upsert_by_user(user_id)
            except Exception as exc:  # FK violation → user missing
                raise ResourceNotFoundError(f"User {user_id} not found") from exc
        return UserProfileMapper.orm_to_entity(orm)

    async def update(
        self, user_id: int, dto: UpdateUserProfileDTO
    ) -> UserProfileEntity:
        """Patch the profile for ``user_id``; creates the row if absent.

        At least one field must be non-``None`` — the presentation layer
        validates this before constructing the DTO.

        Args:
            user_id: PK of the owning user.
            dto:     ``UpdateUserProfileDTO`` with unset fields left ``None``.

        Returns:
            The updated ``UserProfileEntity``.

        Raises:
            ResourceNotFoundError: The user does not exist.
        """
        try:
            orm = await self._repository.upsert_by_user(
                user_id,
                sex=dto.sex,
                dob=dto.dob,
                role=dto.role,
                sub_role=dto.sub_role,
                is_whatsapp_notification_enabled=dto.is_whatsapp_notification_enabled,
                is_email_notification_enabled=dto.is_email_notification_enabled,
                is_phone_notification_enabled=dto.is_phone_notification_enabled,
            )
        except Exception as exc:
            raise ResourceNotFoundError(f"User {user_id} not found") from exc
        logger.info("user_profile_updated", user_id=user_id)
        return UserProfileMapper.orm_to_entity(orm)
