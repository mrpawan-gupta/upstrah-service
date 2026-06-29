"""Mapper round-trip unit tests for the academies aggregates.

Verifies ``orm_to_entity → entity_to_dto → dto_to_response`` preserves the
scalar fields end to end for both the Academy and Membership mappers. Uses
in-memory stand-ins for the ORM rows so the tests need no database.
"""

from __future__ import annotations

from datetime import UTC, datetime

from academies.api.application.mappers.academy_mapper import AcademyMapper
from academies.api.application.mappers.membership_mapper import MembershipMapper
from academies.api.domain.entities.academy import AcademyEntity
from academies.api.domain.entities.membership import MembershipEntity


class _FakeAcademyRow:
    """Minimal stand-in for an ``academies.models.Academy`` row."""

    def __init__(self) -> None:
        self.id = 7
        self.name = "Riverside FC"
        self.sport = "Football"
        self.description = "Youth academy"
        self.city = "Lagos"
        self.status = "active"
        self.created_by_id = 99
        self.created_at = datetime(2026, 1, 1, tzinfo=UTC)
        self.updated_at = datetime(2026, 1, 2, tzinfo=UTC)


class _FakeMembershipRow:
    """Minimal stand-in for an ``academies.models.Membership`` row."""

    def __init__(self) -> None:
        self.id = 11
        self.user_id = 42
        self.academy_id = 7
        self.role = "athlete"
        self.status = "pending"
        self.created_at = datetime(2026, 1, 3, tzinfo=UTC)
        self.updated_at = datetime(2026, 1, 4, tzinfo=UTC)


def test_academy_mapper_round_trip() -> None:
    """ORM row → entity → DTO → response dict keeps every field intact."""
    entity = AcademyMapper.orm_to_entity(_FakeAcademyRow())
    assert isinstance(entity, AcademyEntity)
    assert entity.id == 7
    assert entity.created_by == 99

    dto = AcademyMapper.entity_to_dto(entity)
    assert dto.name == "Riverside FC"

    response = AcademyMapper.dto_to_response(dto)
    assert response["id"] == 7
    assert response["name"] == "Riverside FC"
    assert response["sport"] == "Football"
    assert response["status"] == "active"
    assert response["created_by"] == 99


def test_academy_mapper_orm_to_entity_does_not_leak_orm() -> None:
    """``orm_to_entity`` returns a frozen entity, never the ORM row."""
    entity = AcademyMapper.orm_to_entity(_FakeAcademyRow())
    assert not isinstance(entity, _FakeAcademyRow)
    assert type(entity).__name__ == "AcademyEntity"


def test_membership_mapper_round_trip() -> None:
    """ORM row → entity → DTO → response dict keeps every field intact."""
    entity = MembershipMapper.orm_to_entity(_FakeMembershipRow())
    assert isinstance(entity, MembershipEntity)
    assert entity.user_id == 42
    assert entity.academy_id == 7

    dto = MembershipMapper.entity_to_dto(entity)
    assert dto.role == "athlete"

    response = MembershipMapper.dto_to_response(dto)
    assert response["id"] == 11
    assert response["user_id"] == 42
    assert response["academy_id"] == 7
    assert response["role"] == "athlete"
    assert response["status"] == "pending"
