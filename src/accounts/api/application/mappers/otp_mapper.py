"""Mapper for the OTP aggregate.

Covers the write path (``schema_to_create_dto``) and the entity-based read
path (``orm_to_entity`` → ``entity_to_dto`` → ``dto_to_response``).
``orm_to_entity`` never leaks an ORM object — it returns a frozen
``OTPEntity``. ``model_dump()`` is called only inside ``dto_to_response`` /
``entity_to_create_response``.
"""

from __future__ import annotations

from typing import Any

from accounts.api.application.dtos.otp_dtos import OTPCreateDTO, OTPResponseDTO
from accounts.api.domain.entities.otp import OTPEntity
from accounts.api.presentation.schemas.otp_schemas import (
    OTPCreateResponseSchema,
    OTPRequestSchema,
    OTPResponseSchema,
)


class OTPMapper:
    """Stateless mapper for the OTP aggregate."""

    @staticmethod
    def schema_to_create_dto(schema: OTPRequestSchema) -> OTPCreateDTO:
        """Convert a validated ``OTPRequestSchema`` to an ``OTPCreateDTO``.

        Args:
            schema: Validated create-request schema from the presentation layer.

        Returns:
            ``OTPCreateDTO`` carrying all fields needed by the create use case.
        """
        return OTPCreateDTO(
            phone=schema.phone,
            email=schema.email,
            otp=schema.otp,
            expires_at=schema.expires_at,
        )

    @staticmethod
    def orm_to_entity(row: Any) -> OTPEntity:
        """Convert an ``accounts.models.OTP`` ORM instance to an ``OTPEntity``.

        Args:
            row: ``OTP`` ORM instance.

        Returns:
            Frozen ``OTPEntity`` with all scalar fields populated.
        """
        return OTPEntity(
            id=row.id,
            phone=str(row.phone) if row.phone else None,
            email=row.email,
            otp=row.otp,
            expires_at=row.expires_at,
            is_valid=row.is_valid(),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def entity_to_dto(entity: OTPEntity) -> OTPResponseDTO:
        """Convert a domain ``OTPEntity`` to an ``OTPResponseDTO``.

        Args:
            entity: Domain entity returned by a use case.

        Returns:
            ``OTPResponseDTO`` carrying the same scalar fields.
        """
        return OTPResponseDTO(
            id=entity.id,
            phone=entity.phone,
            email=entity.email,
            otp=entity.otp,
            expires_at=entity.expires_at,
            is_valid=entity.is_valid,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def dto_to_response(dto: OTPResponseDTO) -> dict:
        """Serialise an ``OTPResponseDTO`` to a plain dict for JSON encoding.

        ``model_dump()`` is called here and only here for the read path.

        Args:
            dto: Application-layer DTO to serialise.

        Returns:
            Plain dict matching the ``OTPResponseSchema`` shape.
        """
        return OTPResponseSchema.model_validate(dto, from_attributes=True).model_dump(
            mode="json"
        )

    @staticmethod
    def entity_to_response(entity: OTPEntity) -> dict:
        """Shortcut: convert a domain entity directly to a response dict.

        Args:
            entity: Domain entity returned by a use case.

        Returns:
            Plain dict matching the ``OTPResponseSchema`` shape.
        """
        return OTPMapper.dto_to_response(OTPMapper.entity_to_dto(entity))

    @staticmethod
    def entity_to_create_response(entity: OTPEntity) -> dict:
        """Serialise a freshly-created OTP entity using the create response schema.

        ``otp`` and ``expires_at`` are required in ``OTPCreateResponseSchema``
        and are guaranteed non-null immediately after ``set_otp_and_validity()``.

        Args:
            entity: ``OTPEntity`` returned by the create use case.

        Returns:
            Plain dict matching the ``OTPCreateResponseSchema`` shape.
        """
        return OTPCreateResponseSchema(
            id=entity.id,
            phone=entity.phone,
            email=entity.email,
            otp=entity.otp,
            expires_at=entity.expires_at,
            is_valid=entity.is_valid,
        ).model_dump(mode="json")
