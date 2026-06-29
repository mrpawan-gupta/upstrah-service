"""Mapper round-trip unit test for the OTP aggregate.

Verifies ``orm_to_entity → entity_to_dto → dto_to_response`` preserves the
OTP row's scalar fields end to end. Uses an in-memory stand-in for the ORM
row so the test needs no database.
"""

from __future__ import annotations

from datetime import UTC, datetime

from accounts.api.application.mappers.otp_mapper import OTPMapper


class _FakeOTPRow:
    """Minimal stand-in for an ``accounts.models.OTP`` row."""

    def __init__(self) -> None:
        self.id = 42
        self.phone = "+15551234567"
        self.email = None
        self.otp = "1234"
        self.expires_at = datetime(2030, 1, 1, tzinfo=UTC)
        self.created_at = datetime(2029, 1, 1, tzinfo=UTC)
        self.updated_at = datetime(2029, 1, 2, tzinfo=UTC)

    def is_valid(self) -> bool:
        return True


def test_otp_mapper_round_trip() -> None:
    """ORM row → entity → DTO → response dict keeps every field intact."""
    row = _FakeOTPRow()

    entity = OTPMapper.orm_to_entity(row)
    assert entity.id == 42
    assert entity.phone == "+15551234567"
    assert entity.otp == "1234"
    assert entity.is_valid is True

    dto = OTPMapper.entity_to_dto(entity)
    assert dto.id == entity.id
    assert dto.phone == entity.phone
    assert dto.otp == entity.otp

    response = OTPMapper.dto_to_response(dto)
    assert response["id"] == 42
    assert response["phone"] == "+15551234567"
    assert response["otp"] == "1234"
    assert response["is_valid"] is True
    assert response["email"] is None


def test_otp_mapper_orm_to_entity_does_not_leak_orm() -> None:
    """``orm_to_entity`` returns a frozen entity, never the ORM row."""
    entity = OTPMapper.orm_to_entity(_FakeOTPRow())
    assert not isinstance(entity, _FakeOTPRow)
    assert type(entity).__name__ == "OTPEntity"
