"""Mapper for the Membership aggregate.

Converts the ``Membership`` ORM row to the domain entity, the entity to the
response DTO, the response DTO to a response dict, and the create schema to
a write DTO. ``orm_to_entity`` returns a frozen ``MembershipEntity`` (no
ORM leak); ``model_dump()`` is confined to ``dto_to_response``.
"""

from __future__ import annotations

from typing import Any

from academies.api.application.dtos.membership_dtos import (
    MembershipCreateDTO,
    MembershipResponseDTO,
)
from academies.api.domain.entities.membership import MembershipEntity
from academies.api.presentation.schemas.membership_schemas import (
    MembershipCreateSchema,
    MembershipResponseSchema,
)


class MembershipMapper:
    """Stateless mapper for the Membership aggregate."""

    @staticmethod
    def orm_to_entity(orm: Any) -> MembershipEntity:
        """Convert a ``Membership`` ORM instance to a frozen domain entity.

        Args:
            orm: ``Membership`` ORM row.

        Returns:
            ``MembershipEntity`` domain object.
        """
        return MembershipEntity(
            id=orm.id,
            user_id=orm.user_id,
            academy_id=orm.academy_id,
            role=orm.role,
            status=orm.status,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def entity_to_dto(entity: MembershipEntity) -> MembershipResponseDTO:
        """Convert a ``MembershipEntity`` to a ``MembershipResponseDTO``."""
        return MembershipResponseDTO(
            id=entity.id,
            user_id=entity.user_id,
            academy_id=entity.academy_id,
            role=entity.role,
            status=entity.status,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def dto_to_response(dto: MembershipResponseDTO) -> dict:
        """Serialise a ``MembershipResponseDTO`` to a response dict.

        ``model_dump()`` is called here and only here for this aggregate's
        read path.

        Args:
            dto: Application-layer DTO to serialise.

        Returns:
            Plain dict matching the ``MembershipResponseSchema`` shape.
        """
        return MembershipResponseSchema.model_validate(dto).model_dump(mode="json")

    @staticmethod
    def entity_to_response(entity: MembershipEntity) -> dict:
        """Shortcut: convert a domain entity directly to a response dict."""
        return MembershipMapper.dto_to_response(MembershipMapper.entity_to_dto(entity))

    @staticmethod
    def schema_to_dto(
        schema: MembershipCreateSchema, *, user_id: int, academy_id: int
    ) -> MembershipCreateDTO:
        """Convert a ``MembershipCreateSchema`` to a ``MembershipCreateDTO``.

        Args:
            schema:     Validated POST request schema.
            user_id:    PK of the applying user (from the caller token).
            academy_id: PK of the academy applied to (from the path).

        Returns:
            ``MembershipCreateDTO`` ready for the use case.
        """
        return MembershipCreateDTO(
            user_id=user_id,
            academy_id=academy_id,
            role=schema.role,
        )
