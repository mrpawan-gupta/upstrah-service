"""Data Transfer Objects for the Academy application layer.

Defines the dataclass boundaries between the presentation layer and the
``Academy`` use-case facade. Write DTOs carry ``sport_ids: list[int]`` for
the M2M plus the registration scalar fields; ``AcademyPatchDTO`` uses
``| None`` defaults so a PATCH leaves unset fields unchanged;
``AcademyResponseDTO`` is the read boundary serialised to the response and
carries the resolved sports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from academies.api.domain.entities.academy import SportRef
from common.api import BaseModelDTO


@dataclass
class AcademyCreateDTO(BaseModelDTO):
    """Fields required to create an academy (POST).

    Attributes:
        name:                  Display name.
        created_by:            PK of the owning user (resolved from caller).
        sport_ids:             PKs of the sports the academy trains.
        description:           Free-text description (defaults to empty).
        city:                  City of operation (defaults to empty).
        status:                Lifecycle status (defaults to ``active``).
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
    """

    name: str
    created_by: int
    sport_ids: list[int] = field(default_factory=list)
    description: str = ""
    city: str = ""
    status: str = "active"
    legal_name: str = ""
    address: str = ""
    email: str = ""
    phone: str = ""
    registration_type: str = ""
    gst_number: str = ""
    website: str = ""
    social_links: dict[str, str] = field(default_factory=dict)
    athlete_count: int = 0
    coach_count: int = 0
    primary_contact_name: str = ""
    primary_contact_phone: str = ""


@dataclass
class AcademyUpdateDTO(BaseModelDTO):
    """Fields for a full replace of an academy (PUT) — all required.

    Attributes:
        name:                  New display name.
        sport_ids:             New set of sport PKs.
        description:           New description.
        city:                  New city.
        status:                New lifecycle status.
        legal_name:            New legal entity name.
        address:               New postal address.
        email:                 New contact email.
        phone:                 New contact phone (E.164 string).
        registration_type:     New legal registration type.
        gst_number:            New GST registration number.
        website:               New website URL.
        social_links:          New map of ``{platform: url}``.
        athlete_count:         New self-reported athlete count.
        coach_count:           New self-reported coach count.
        primary_contact_name:  New primary contact name.
        primary_contact_phone: New primary contact phone (E.164 string).
    """

    name: str
    sport_ids: list[int]
    description: str
    city: str
    status: str
    legal_name: str
    address: str
    email: str
    phone: str
    registration_type: str
    gst_number: str
    website: str
    social_links: dict[str, str]
    athlete_count: int
    coach_count: int
    primary_contact_name: str
    primary_contact_phone: str


@dataclass
class AcademyPatchDTO(BaseModelDTO):
    """Fields for a partial update of an academy (PATCH).

    ``None`` means "leave unchanged".

    Attributes:
        name:                  New display name, or ``None``.
        sport_ids:             New set of sport PKs, or ``None``.
        description:           New description, or ``None``.
        city:                  New city, or ``None``.
        status:                New lifecycle status, or ``None``.
        legal_name:            New legal entity name, or ``None``.
        address:               New postal address, or ``None``.
        email:                 New contact email, or ``None``.
        phone:                 New contact phone, or ``None``.
        registration_type:     New legal registration type, or ``None``.
        gst_number:            New GST registration number, or ``None``.
        website:               New website URL, or ``None``.
        social_links:          New ``{platform: url}`` map, or ``None``.
        athlete_count:         New athlete count, or ``None``.
        coach_count:           New coach count, or ``None``.
        primary_contact_name:  New primary contact name, or ``None``.
        primary_contact_phone: New primary contact phone, or ``None``.
    """

    name: str | None = None
    sport_ids: list[int] | None = None
    description: str | None = None
    city: str | None = None
    status: str | None = None
    legal_name: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    registration_type: str | None = None
    gst_number: str | None = None
    website: str | None = None
    social_links: dict[str, str] | None = None
    athlete_count: int | None = None
    coach_count: int | None = None
    primary_contact_name: str | None = None
    primary_contact_phone: str | None = None


@dataclass
class AcademyResponseDTO(BaseModelDTO):
    """Read representation of an academy returned by use cases.

    Attributes:
        id:                    Primary key.
        name:                  Display name.
        sports:                Sports trained (:class:`SportRef` items).
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

    id: int
    name: str
    sports: list[SportRef]
    description: str
    city: str
    status: str
    legal_name: str
    address: str
    email: str
    phone: str
    registration_type: str
    gst_number: str
    website: str
    social_links: dict[str, str]
    athlete_count: int
    coach_count: int
    primary_contact_name: str
    primary_contact_phone: str
    created_by: int
    created_at: datetime
    updated_at: datetime
