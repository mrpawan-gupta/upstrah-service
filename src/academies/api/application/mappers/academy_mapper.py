"""Mapper for the Academy aggregate.

Converts the ``Academy`` ORM row to the domain entity, the entity to the
response DTO, the response DTO to a response dict, and the request schemas
to write DTOs. ``orm_to_entity`` returns a frozen ``AcademyEntity`` (no ORM
leak); ``model_dump()`` is confined to ``dto_to_response``.
"""

from __future__ import annotations

from typing import Any

from academies.api.application.dtos.academy_dtos import (
    AcademyCreateDTO,
    AcademyPatchDTO,
    AcademyResponseDTO,
    AcademyUpdateDTO,
)
from academies.api.domain.entities.academy import AcademyEntity
from academies.api.presentation.schemas.academy_schemas import (
    AcademyCreateSchema,
    AcademyPatchSchema,
    AcademyResponseSchema,
    AcademyUpdateSchema,
)


class AcademyMapper:
    """Stateless mapper for the Academy aggregate."""

    @staticmethod
    def orm_to_entity(orm: Any) -> AcademyEntity:
        """Convert an ``Academy`` ORM instance to a frozen domain entity.

        Args:
            orm: ``Academy`` ORM row.

        Returns:
            ``AcademyEntity`` domain object.
        """
        return AcademyEntity(
            id=orm.id,
            name=orm.name,
            sport=orm.sport,
            description=orm.description,
            city=orm.city,
            status=orm.status,
            created_by=orm.created_by_id,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def entity_to_dto(entity: AcademyEntity) -> AcademyResponseDTO:
        """Convert an ``AcademyEntity`` to an ``AcademyResponseDTO``.

        Args:
            entity: Domain entity returned by a use case.

        Returns:
            ``AcademyResponseDTO`` carrying the same scalar fields.
        """
        return AcademyResponseDTO(
            id=entity.id,
            name=entity.name,
            sport=entity.sport,
            description=entity.description,
            city=entity.city,
            status=entity.status,
            created_by=entity.created_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def dto_to_response(dto: AcademyResponseDTO) -> dict:
        """Serialise an ``AcademyResponseDTO`` to a response dict.

        ``model_dump()`` is called here and only here for this aggregate's
        read path.

        Args:
            dto: Application-layer DTO to serialise.

        Returns:
            Plain dict matching the ``AcademyResponseSchema`` shape.
        """
        return AcademyResponseSchema.model_validate(dto).model_dump(mode="json")

    @staticmethod
    def entity_to_response(entity: AcademyEntity) -> dict:
        """Shortcut: convert a domain entity directly to a response dict."""
        return AcademyMapper.dto_to_response(AcademyMapper.entity_to_dto(entity))

    @staticmethod
    def schema_to_dto(
        schema: AcademyCreateSchema, *, created_by: int
    ) -> AcademyCreateDTO:
        """Convert an ``AcademyCreateSchema`` to an ``AcademyCreateDTO``.

        Args:
            schema:     Validated POST request schema.
            created_by: PK of the owning user (resolved from the caller).

        Returns:
            ``AcademyCreateDTO`` ready for the use case.
        """
        return AcademyCreateDTO(
            name=schema.name,
            sport=schema.sport,
            created_by=created_by,
            description=schema.description,
            city=schema.city,
            status=schema.status,
        )

    @staticmethod
    def update_schema_to_dto(schema: AcademyUpdateSchema) -> AcademyUpdateDTO:
        """Convert an ``AcademyUpdateSchema`` (PUT) to an ``AcademyUpdateDTO``."""
        return AcademyUpdateDTO(
            name=schema.name,
            sport=schema.sport,
            description=schema.description,
            city=schema.city,
            status=schema.status,
        )

    @staticmethod
    def patch_schema_to_dto(schema: AcademyPatchSchema) -> AcademyPatchDTO:
        """Convert an ``AcademyPatchSchema`` (PATCH) to an ``AcademyPatchDTO``.

        ``None`` values are preserved so the use case skips unchanged fields.
        """
        return AcademyPatchDTO(
            name=schema.name,
            sport=schema.sport,
            description=schema.description,
            city=schema.city,
            status=schema.status,
        )
