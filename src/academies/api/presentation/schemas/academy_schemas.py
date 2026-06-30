"""Pydantic request/response schemas for the Academy endpoints.

Covers ``POST/GET /academies`` and ``GET/PUT/PATCH/DELETE
/academies/{id}``. Write schemas carry ``sport_ids: list[int]`` for the
M2M plus the registration scalar fields (legal name, address, contact
details, registration type, counts, etc.); the response returns
``sports: list[{id, name}]`` and all scalars. The PUT schema makes every
mutable field required (empty values allowed); the PATCH schema makes every
field ``| None = None`` (unset = leave unchanged). ``status`` and
``registration_type`` are validated against the model choices here, never
in the controller.
"""

from __future__ import annotations

from datetime import datetime

from django.utils.translation import gettext_lazy as _
from pydantic import Field, field_validator

from academies.constants import AcademyStatus, RegistrationType
from common.api import BaseRequestSchema, BaseResponseSchema

_STATUS_VALUES = {c.value for c in AcademyStatus}
_REGISTRATION_TYPE_VALUES = {c.value for c in RegistrationType}


def _validate_status(value: str | None) -> str | None:
    """Return ``value`` when it is a valid status, else raise ``ValueError``."""
    if value is not None and value not in _STATUS_VALUES:
        raise ValueError(
            str(_("status must be one of: {choices}.")).format(
                choices=", ".join(sorted(_STATUS_VALUES))
            )
        )
    return value


def _validate_registration_type(value: str | None) -> str | None:
    """Return ``value`` when valid (empty allowed), else raise ``ValueError``."""
    if value not in (None, "") and value not in _REGISTRATION_TYPE_VALUES:
        raise ValueError(
            str(_("registration_type must be one of: {choices}.")).format(
                choices=", ".join(sorted(_REGISTRATION_TYPE_VALUES))
            )
        )
    return value


class SportSchema(BaseResponseSchema):
    """Nested sport reference inside an academy response.

    Attributes:
        id:   Primary key of the sport.
        name: Display name of the sport.
    """

    id: int = Field(..., description=str(_("Primary key of the sport.")))
    name: str = Field(..., description=str(_("Display name of the sport.")))


class AcademyCreateSchema(BaseRequestSchema):
    """Request body for ``POST /academies``.

    Attributes:
        name:                  Display name.
        sport_ids:             PKs of the sports the academy trains.
        description:           Optional free-text description.
        city:                  Optional city of operation.
        status:                Lifecycle status (defaults to ``active``).
        legal_name:            Registered legal entity name (optional).
        address:               Full postal address (optional).
        email:                 Contact email (optional).
        phone:                 Contact phone in E.164 (optional).
        registration_type:     Legal registration type (optional).
        gst_number:            GST registration number (optional).
        website:               Public website URL (optional).
        social_links:          Map of ``{platform: url}`` (optional).
        athlete_count:         Self-reported athlete count (defaults to 0).
        coach_count:           Self-reported coach count (defaults to 0).
        primary_contact_name:  Primary contact name (optional).
        primary_contact_phone: Primary contact phone in E.164 (optional).
    """

    name: str = Field(..., min_length=1, max_length=255, description=str(_("Name.")))
    sport_ids: list[int] = Field(
        default_factory=list, description=str(_("PKs of the sports trained."))
    )
    description: str = Field("", description=str(_("Free-text description.")))
    city: str = Field("", max_length=120, description=str(_("City of operation.")))
    status: str = Field(
        AcademyStatus.ACTIVE.value, description=str(_("'active' or 'inactive'."))
    )
    legal_name: str = Field(
        "", max_length=255, description=str(_("Registered legal entity name."))
    )
    address: str = Field("", description=str(_("Full postal address.")))
    email: str = Field("", description=str(_("Contact email.")))
    phone: str = Field("", description=str(_("Contact phone in E.164 format.")))
    registration_type: str = Field(
        "", description=str(_("Legal registration type."))
    )
    gst_number: str = Field(
        "", max_length=20, description=str(_("GST registration number."))
    )
    website: str = Field("", description=str(_("Public website URL.")))
    social_links: dict[str, str] = Field(
        default_factory=dict, description=str(_("Map of {platform: url}."))
    )
    athlete_count: int = Field(
        0, ge=0, description=str(_("Self-reported athlete count."))
    )
    coach_count: int = Field(
        0, ge=0, description=str(_("Self-reported coach count."))
    )
    primary_contact_name: str = Field(
        "", max_length=255, description=str(_("Primary contact name."))
    )
    primary_contact_phone: str = Field(
        "", description=str(_("Primary contact phone in E.164 format."))
    )

    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate that status is an accepted lifecycle value."""
        return _validate_status(v)

    @field_validator("registration_type", mode="after")
    @classmethod
    def validate_registration_type(cls, v: str | None) -> str | None:
        """Validate registration_type against the accepted choices."""
        return _validate_registration_type(v)


class AcademyUpdateSchema(BaseRequestSchema):
    """Request body for ``PUT /academies/{id}`` — full replace (all required).

    Empty strings / empty maps are accepted so optional model fields can be
    cleared; ``name`` still requires a non-empty value.

    Attributes:
        name:                  New display name.
        sport_ids:             New set of sport PKs.
        description:           New description.
        city:                  New city.
        status:                New lifecycle status.
        legal_name:            New legal entity name.
        address:               New postal address.
        email:                 New contact email.
        phone:                 New contact phone in E.164.
        registration_type:     New legal registration type.
        gst_number:            New GST registration number.
        website:               New website URL.
        social_links:          New ``{platform: url}`` map.
        athlete_count:         New self-reported athlete count.
        coach_count:           New self-reported coach count.
        primary_contact_name:  New primary contact name.
        primary_contact_phone: New primary contact phone in E.164.
    """

    name: str = Field(..., min_length=1, max_length=255, description=str(_("Name.")))
    sport_ids: list[int] = Field(..., description=str(_("New set of sport PKs.")))
    description: str = Field(..., description=str(_("Free-text description.")))
    city: str = Field(..., max_length=120, description=str(_("City of operation.")))
    status: str = Field(..., description=str(_("'active' or 'inactive'.")))
    legal_name: str = Field(
        ..., max_length=255, description=str(_("Registered legal entity name."))
    )
    address: str = Field(..., description=str(_("Full postal address.")))
    email: str = Field(..., description=str(_("Contact email.")))
    phone: str = Field(..., description=str(_("Contact phone in E.164 format.")))
    registration_type: str = Field(
        ..., description=str(_("Legal registration type."))
    )
    gst_number: str = Field(
        ..., max_length=20, description=str(_("GST registration number."))
    )
    website: str = Field(..., description=str(_("Public website URL.")))
    social_links: dict[str, str] = Field(
        ..., description=str(_("Map of {platform: url}."))
    )
    athlete_count: int = Field(
        ..., ge=0, description=str(_("Self-reported athlete count."))
    )
    coach_count: int = Field(
        ..., ge=0, description=str(_("Self-reported coach count."))
    )
    primary_contact_name: str = Field(
        ..., max_length=255, description=str(_("Primary contact name."))
    )
    primary_contact_phone: str = Field(
        ..., description=str(_("Primary contact phone in E.164 format."))
    )

    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate that status is an accepted lifecycle value."""
        return _validate_status(v)

    @field_validator("registration_type", mode="after")
    @classmethod
    def validate_registration_type(cls, v: str | None) -> str | None:
        """Validate registration_type against the accepted choices."""
        return _validate_registration_type(v)


class AcademyPatchSchema(BaseRequestSchema):
    """Request body for ``PATCH /academies/{id}`` — all fields optional.

    Unset fields are left unchanged.

    Attributes:
        name:                  New display name, or ``null``.
        sport_ids:             New set of sport PKs, or ``null``.
        description:           New description, or ``null``.
        city:                  New city, or ``null``.
        status:                New lifecycle status, or ``null``.
        legal_name:            New legal entity name, or ``null``.
        address:               New postal address, or ``null``.
        email:                 New contact email, or ``null``.
        phone:                 New contact phone, or ``null``.
        registration_type:     New legal registration type, or ``null``.
        gst_number:            New GST registration number, or ``null``.
        website:               New website URL, or ``null``.
        social_links:          New ``{platform: url}`` map, or ``null``.
        athlete_count:         New athlete count, or ``null``.
        coach_count:           New coach count, or ``null``.
        primary_contact_name:  New primary contact name, or ``null``.
        primary_contact_phone: New primary contact phone, or ``null``.
    """

    name: str | None = Field(
        None, min_length=1, max_length=255, description=str(_("Name."))
    )
    sport_ids: list[int] | None = Field(
        None, description=str(_("New set of sport PKs."))
    )
    description: str | None = Field(None, description=str(_("Free-text description.")))
    city: str | None = Field(
        None, max_length=120, description=str(_("City of operation."))
    )
    status: str | None = Field(None, description=str(_("'active' or 'inactive'.")))
    legal_name: str | None = Field(
        None, max_length=255, description=str(_("Registered legal entity name."))
    )
    address: str | None = Field(None, description=str(_("Full postal address.")))
    email: str | None = Field(None, description=str(_("Contact email.")))
    phone: str | None = Field(
        None, description=str(_("Contact phone in E.164 format."))
    )
    registration_type: str | None = Field(
        None, description=str(_("Legal registration type."))
    )
    gst_number: str | None = Field(
        None, max_length=20, description=str(_("GST registration number."))
    )
    website: str | None = Field(None, description=str(_("Public website URL.")))
    social_links: dict[str, str] | None = Field(
        None, description=str(_("Map of {platform: url}."))
    )
    athlete_count: int | None = Field(
        None, ge=0, description=str(_("Self-reported athlete count."))
    )
    coach_count: int | None = Field(
        None, ge=0, description=str(_("Self-reported coach count."))
    )
    primary_contact_name: str | None = Field(
        None, max_length=255, description=str(_("Primary contact name."))
    )
    primary_contact_phone: str | None = Field(
        None, description=str(_("Primary contact phone in E.164 format."))
    )

    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate that status is an accepted lifecycle value."""
        return _validate_status(v)

    @field_validator("registration_type", mode="after")
    @classmethod
    def validate_registration_type(cls, v: str | None) -> str | None:
        """Validate registration_type against the accepted choices."""
        return _validate_registration_type(v)


class AcademyResponseSchema(BaseResponseSchema):
    """Response shape for an academy.

    Attributes:
        id:                    Primary key.
        name:                  Display name.
        sports:                Sports trained (``{id, name}`` items).
        description:           Free-text description.
        city:                  City of operation.
        status:                Lifecycle status.
        legal_name:            Registered legal entity name.
        address:               Full postal address.
        email:                 Contact email.
        phone:                 Contact phone (E.164 string).
        registration_type:     Legal registration type.
        gst_number:            GST registration number.
        website:               Public website URL.
        social_links:          Map of ``{platform: url}``.
        athlete_count:         Self-reported number of athletes.
        coach_count:           Self-reported number of coaches.
        primary_contact_name:  Primary contact person's name.
        primary_contact_phone: Primary contact phone (E.164 string).
        created_by:            PK of the owning user.
        created_at:            Row creation timestamp.
        updated_at:            Row last-modified timestamp.
    """

    id: int = Field(..., description=str(_("Primary key.")))
    name: str = Field(..., description=str(_("Display name.")))
    sports: list[SportSchema] = Field(
        ..., description=str(_("Sports the academy trains."))
    )
    description: str = Field(..., description=str(_("Free-text description.")))
    city: str = Field(..., description=str(_("City of operation.")))
    status: str = Field(..., description=str(_("Lifecycle status.")))
    legal_name: str = Field(..., description=str(_("Registered legal entity name.")))
    address: str = Field(..., description=str(_("Full postal address.")))
    email: str = Field(..., description=str(_("Contact email.")))
    phone: str = Field(..., description=str(_("Contact phone (E.164).")))
    registration_type: str = Field(
        ..., description=str(_("Legal registration type."))
    )
    gst_number: str = Field(..., description=str(_("GST registration number.")))
    website: str = Field(..., description=str(_("Public website URL.")))
    social_links: dict[str, str] = Field(
        ..., description=str(_("Map of {platform: url}."))
    )
    athlete_count: int = Field(..., description=str(_("Self-reported athletes.")))
    coach_count: int = Field(..., description=str(_("Self-reported coaches.")))
    primary_contact_name: str = Field(
        ..., description=str(_("Primary contact name."))
    )
    primary_contact_phone: str = Field(
        ..., description=str(_("Primary contact phone (E.164)."))
    )
    created_by: int = Field(..., description=str(_("PK of the owning user.")))
    created_at: datetime = Field(..., description=str(_("Creation timestamp.")))
    updated_at: datetime = Field(..., description=str(_("Last-modified timestamp.")))
