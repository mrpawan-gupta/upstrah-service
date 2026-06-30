"""Mapper for the Academy aggregate.

Converts the ``Academy`` ORM row to the domain entity (reading the
prefetched ``sports`` relation), the entity to the response DTO, the
response DTO to a response dict, and the request schemas to write DTOs
carrying ``sport_ids``. ``orm_to_entity`` returns a frozen ``AcademyEntity``
(no ORM leak); ``model_dump()`` is confined to ``dto_to_response``.
"""

from __future__ import annotations

from typing import Any

from academies.api.application.dtos.academy_dtos import (
    AcademyCreateDTO,
    AcademyPatchDTO,
    AcademyResponseDTO,
    AcademyUpdateDTO,
)
from academies.api.domain.entities.academy import AcademyEntity, SportRef
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

        Reads the already-prefetched ``sports`` relation (the repository
        prefetches it) into a tuple of frozen :class:`SportRef` value
        objects so no ORM object escapes this boundary.

        Args:
            orm: ``Academy`` ORM row with ``sports`` prefetched.

        Returns:
            ``AcademyEntity`` domain object.
        """
        sports = tuple(
            SportRef(id=s.id, name=s.name) for s in orm.sports.all()
        )
        return AcademyEntity(
            id=orm.id,
            name=orm.name,
            sports=sports,
            description=orm.description,
            city=orm.city,
            status=orm.status,
            legal_name=orm.legal_name,
            address=orm.address,
            email=orm.email,
            phone=str(orm.phone) if orm.phone else "",
            registration_type=orm.registration_type,
            gst_number=orm.gst_number,
            website=orm.website,
            social_links=orm.social_links or {},
            athlete_count=orm.athlete_count,
            coach_count=orm.coach_count,
            primary_contact_name=orm.primary_contact_name,
            primary_contact_phone=(
                str(orm.primary_contact_phone) if orm.primary_contact_phone else ""
            ),
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
            ``AcademyResponseDTO`` carrying the same fields.
        """
        return AcademyResponseDTO(
            id=entity.id,
            name=entity.name,
            sports=list(entity.sports),
            description=entity.description,
            city=entity.city,
            status=entity.status,
            legal_name=entity.legal_name,
            address=entity.address,
            email=entity.email,
            phone=entity.phone,
            registration_type=entity.registration_type,
            gst_number=entity.gst_number,
            website=entity.website,
            social_links=entity.social_links,
            athlete_count=entity.athlete_count,
            coach_count=entity.coach_count,
            primary_contact_name=entity.primary_contact_name,
            primary_contact_phone=entity.primary_contact_phone,
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
            created_by=created_by,
            sport_ids=list(schema.sport_ids),
            description=schema.description,
            city=schema.city,
            status=schema.status,
            legal_name=schema.legal_name,
            address=schema.address,
            email=schema.email,
            phone=schema.phone,
            registration_type=schema.registration_type,
            gst_number=schema.gst_number,
            website=schema.website,
            social_links=dict(schema.social_links),
            athlete_count=schema.athlete_count,
            coach_count=schema.coach_count,
            primary_contact_name=schema.primary_contact_name,
            primary_contact_phone=schema.primary_contact_phone,
        )

    @staticmethod
    def update_schema_to_dto(schema: AcademyUpdateSchema) -> AcademyUpdateDTO:
        """Convert an ``AcademyUpdateSchema`` (PUT) to an ``AcademyUpdateDTO``."""
        return AcademyUpdateDTO(
            name=schema.name,
            sport_ids=list(schema.sport_ids),
            description=schema.description,
            city=schema.city,
            status=schema.status,
            legal_name=schema.legal_name,
            address=schema.address,
            email=schema.email,
            phone=schema.phone,
            registration_type=schema.registration_type,
            gst_number=schema.gst_number,
            website=schema.website,
            social_links=dict(schema.social_links),
            athlete_count=schema.athlete_count,
            coach_count=schema.coach_count,
            primary_contact_name=schema.primary_contact_name,
            primary_contact_phone=schema.primary_contact_phone,
        )

    @staticmethod
    def patch_schema_to_dto(schema: AcademyPatchSchema) -> AcademyPatchDTO:
        """Convert an ``AcademyPatchSchema`` (PATCH) to an ``AcademyPatchDTO``.

        ``None`` values are preserved so the use case skips unchanged fields.
        """
        return AcademyPatchDTO(
            name=schema.name,
            sport_ids=schema.sport_ids,
            description=schema.description,
            city=schema.city,
            status=schema.status,
            legal_name=schema.legal_name,
            address=schema.address,
            email=schema.email,
            phone=schema.phone,
            registration_type=schema.registration_type,
            gst_number=schema.gst_number,
            website=schema.website,
            social_links=schema.social_links,
            athlete_count=schema.athlete_count,
            coach_count=schema.coach_count,
            primary_contact_name=schema.primary_contact_name,
            primary_contact_phone=schema.primary_contact_phone,
        )
