"""Domain entity for the Academy aggregate.

Immutable representation of an :class:`academies.models.Academy` row,
including the sports it trains as a tuple of frozen :class:`SportRef` value
objects. ORM models never escape the infrastructure layer; this entity
carries only the fields the use cases and presentation layer need.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from common.api import BaseEntity


@dataclass(frozen=True)
class SportRef(BaseEntity):
    """Immutable reference to a sport an academy trains.

    Attributes:
        id:   Primary key of the sport.
        name: Display name of the sport.
    """

    id: int
    name: str


@dataclass(frozen=True)
class AcademyEntity(BaseEntity):
    """Immutable domain representation of an ``Academy`` row.

    Attributes:
        id:                    Primary key.
        name:                  Display name.
        sports:                Sports trained (frozen :class:`SportRef` items).
        description:           Free-text description (may be empty).
        city:                  City of operation (may be empty).
        status:                ``"active"`` or ``"inactive"``.
        legal_name:            Registered legal entity name.
        address:               Full postal address.
        email:                 Contact email.
        phone:                 Contact phone (E.164 string, may be empty).
        registration_type:     Legal registration type (may be empty).
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
    sports: tuple[SportRef, ...]
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
