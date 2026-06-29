"""Mapper for the UserProfile aggregate.

Converts the 1:1 ``UserProfile`` ORM row (with its owning user selected)
to the domain entity and on to the response schema, and translates the
patch schema into the update DTO. ``orm_to_entity`` returns a frozen
``UserProfileEntity`` (no ORM leak); ``model_dump()`` is confined to
``entity_to_response`` / ``dto_to_response``.
"""

from __future__ import annotations

from typing import Any

from accounts.api.application.dtos.user_profile_dtos import (
    UpdateUserProfileDTO,
    UserProfileResponseDTO,
)
from accounts.api.domain.entities.user_profile import UserProfileEntity
from accounts.api.presentation.schemas.user_profile_schemas import (
    ProfileNestedSchema,
    UserProfilePatchSchema,
    UserProfileResponseSchema,
)


class UserProfileMapper:
    """Stateless mapper for the 1:1 UserProfile aggregate."""

    @staticmethod
    def orm_to_entity(orm: Any) -> UserProfileEntity:
        """Convert a ``UserProfile`` ORM instance to a frozen domain entity.

        Reads the owning user's identity scalars off the already-selected
        ``orm.user`` relation so no second query is needed.

        Args:
            orm: ``UserProfile`` ORM row with ``user`` selected.

        Returns:
            ``UserProfileEntity`` domain object.
        """
        user = orm.user
        return UserProfileEntity(
            user_id=orm.user_id,
            phone=str(user.phone) if user.phone else "",
            email=user.email or "",
            username=str(user.username),
            is_active=user.is_active,
            sex=orm.sex,
            dob=str(orm.dob) if orm.dob else None,
            role=orm.role,
            sub_role=orm.sub_role,
            is_whatsapp_notification_enabled=orm.is_whatsapp_notification_enabled,
            is_email_notification_enabled=orm.is_email_notification_enabled,
            is_phone_notification_enabled=orm.is_phone_notification_enabled,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def entity_to_dto(entity: UserProfileEntity) -> UserProfileResponseDTO:
        """Convert a ``UserProfileEntity`` to a ``UserProfileResponseDTO``.

        Args:
            entity: Domain entity returned by a use case.

        Returns:
            ``UserProfileResponseDTO`` carrying the same scalar fields.
        """
        return UserProfileResponseDTO(
            user_id=entity.user_id,
            phone=entity.phone,
            email=entity.email,
            username=entity.username,
            is_active=entity.is_active,
            sex=entity.sex,
            dob=entity.dob,
            role=entity.role,
            sub_role=entity.sub_role,
            is_whatsapp_notification_enabled=entity.is_whatsapp_notification_enabled,
            is_email_notification_enabled=entity.is_email_notification_enabled,
            is_phone_notification_enabled=entity.is_phone_notification_enabled,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def dto_to_response(dto: UserProfileResponseDTO) -> dict:
        """Serialise a ``UserProfileResponseDTO`` to a user-centric response dict.

        User identity fields sit at the top level; demographic / onboarding
        data is nested under ``profile``. ``model_dump()`` is called here
        and only here for this aggregate's read path.

        Args:
            dto: Application-layer DTO to serialise.

        Returns:
            Plain dict matching the ``UserProfileResponseSchema`` shape.
        """
        profile_nested = ProfileNestedSchema(
            sex=dto.sex,
            dob=dto.dob,
            role=dto.role,
            sub_role=dto.sub_role,
            is_whatsapp_notification_enabled=dto.is_whatsapp_notification_enabled,
            is_email_notification_enabled=dto.is_email_notification_enabled,
            is_phone_notification_enabled=dto.is_phone_notification_enabled,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )
        return UserProfileResponseSchema(
            user_id=dto.user_id,
            phone=dto.phone,
            email=dto.email,
            username=dto.username,
            is_active=dto.is_active,
            profile=profile_nested,
        ).model_dump(mode="json")

    @staticmethod
    def entity_to_response(entity: UserProfileEntity) -> dict:
        """Shortcut: convert a domain entity directly to a response dict.

        Args:
            entity: Domain entity returned by a use case.

        Returns:
            Plain dict matching the ``UserProfileResponseSchema`` shape.
        """
        return UserProfileMapper.dto_to_response(
            UserProfileMapper.entity_to_dto(entity)
        )

    @staticmethod
    def schema_to_update_dto(schema: UserProfilePatchSchema) -> UpdateUserProfileDTO:
        """Convert a ``UserProfilePatchSchema`` to an ``UpdateUserProfileDTO``.

        ``None`` values are preserved so the use case can skip unchanged
        fields.

        Args:
            schema: Validated PATCH request schema.

        Returns:
            ``UpdateUserProfileDTO`` with unset fields left ``None``.
        """
        return UpdateUserProfileDTO(
            sex=schema.sex,
            dob=schema.dob,
            role=schema.role,
            sub_role=schema.sub_role,
            is_whatsapp_notification_enabled=schema.is_whatsapp_notification_enabled,
            is_email_notification_enabled=schema.is_email_notification_enabled,
            is_phone_notification_enabled=schema.is_phone_notification_enabled,
        )
