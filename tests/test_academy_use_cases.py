"""Use-case unit tests for the academies aggregates with fake repositories.

Exercises the business rules against in-memory fakes (no DB): academy
create/get/partial-update/delete and the membership apply → approve/reject
status transitions, plus the not-found and duplicate paths.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from academies.api.application.dtos.academy_dtos import (
    AcademyCreateDTO,
    AcademyPatchDTO,
)
from academies.api.application.dtos.membership_dtos import MembershipCreateDTO
from academies.api.application.use_cases.academy_use_cases import AcademyUseCases
from academies.api.application.use_cases.membership_use_cases import (
    MembershipUseCases,
)
from common.exceptions.exceptions import (
    DuplicateResourceError,
    ResourceNotFoundError,
)


class _Row:
    """Mutable attribute bag standing in for an ORM row."""

    def __init__(self, **kwargs) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        self.created_at = now
        self.updated_at = now
        for k, v in kwargs.items():
            setattr(self, k, v)


class _FakeAcademyRepo:
    """Fake ``IAcademyRepository`` keeping academy rows in a dict."""

    def __init__(self) -> None:
        self.rows: dict[int, _Row] = {}
        self._next = 1

    async def get(self, id_: int):
        return self.rows.get(id_)

    async def create(self, **fields):
        row = _Row(id=self._next, **fields)
        self.rows[self._next] = row
        self._next += 1
        return row

    async def update(self, id_: int, **fields):
        row = self.rows[id_]
        for k, v in fields.items():
            setattr(row, k, v)
        return row

    async def partial_update(self, id_: int, **fields):
        return await self.update(id_, **fields)

    async def delete(self, id_: int) -> None:
        self.rows.pop(id_, None)

    async def list(self, *, limit=100, offset=0, order_by=None, **filters):
        return list(self.rows.values())[offset : offset + limit]

    async def count(self, **filters) -> int:
        return len(self.rows)


class _FakeMembershipRepo:
    """Fake ``IMembershipRepository`` keeping membership rows in a dict."""

    def __init__(self) -> None:
        self.rows: dict[int, _Row] = {}
        self._next = 1
        self._seen: set[tuple[int, int]] = set()

    async def get(self, id_: int):
        return self.rows.get(id_)

    async def create(self, **fields):
        key = (fields["user_id"], fields["academy_id"])
        if key in self._seen:
            raise ValueError("duplicate membership")
        self._seen.add(key)
        row = _Row(id=self._next, **fields)
        self.rows[self._next] = row
        self._next += 1
        return row

    async def list(self, *, limit=100, offset=0, order_by=None, **filters):
        rows = [
            r
            for r in self.rows.values()
            if r.academy_id == filters.get("academy_id", r.academy_id)
        ]
        return rows[offset : offset + limit]

    async def count(self, **filters) -> int:
        return len(
            [
                r
                for r in self.rows.values()
                if r.academy_id == filters.get("academy_id", r.academy_id)
            ]
        )

    async def set_status(self, id_: int, *, status: str):
        row = self.rows[id_]
        row.status = status
        return row


async def test_academy_create_get_patch_delete() -> None:
    """Create → get → patch → delete round-trips through the use case."""
    uc = AcademyUseCases(_FakeAcademyRepo())

    created = await uc.create(
        AcademyCreateDTO(name="A", sport="Tennis", created_by=5)
    )
    assert created.id == 1
    assert created.status == "active"
    assert created.created_by == 5

    fetched = await uc.get(1)
    assert fetched.name == "A"

    patched = await uc.partial_update(1, AcademyPatchDTO(city="Abuja"))
    assert patched.city == "Abuja"
    assert patched.sport == "Tennis"  # unchanged

    await uc.delete(1)
    with pytest.raises(ResourceNotFoundError):
        await uc.get(1)


async def test_academy_get_missing_raises() -> None:
    """Getting a non-existent academy raises ``ResourceNotFoundError``."""
    uc = AcademyUseCases(_FakeAcademyRepo())
    with pytest.raises(ResourceNotFoundError):
        await uc.get(999)


async def test_membership_apply_then_approve_and_reject() -> None:
    """Apply persists pending; approve/reject transition the status."""
    uc = MembershipUseCases(_FakeMembershipRepo())

    applied = await uc.apply(
        MembershipCreateDTO(user_id=42, academy_id=7, role="athlete")
    )
    assert applied.status == "pending"

    approved = await uc.approve(applied.id)
    assert approved.status == "approved"

    rejected = await uc.reject(applied.id)
    assert rejected.status == "rejected"


async def test_membership_duplicate_apply_raises() -> None:
    """A second application for the same (user, academy) raises a 409."""
    uc = MembershipUseCases(_FakeMembershipRepo())
    await uc.apply(MembershipCreateDTO(user_id=42, academy_id=7, role="coach"))
    with pytest.raises(DuplicateResourceError):
        await uc.apply(MembershipCreateDTO(user_id=42, academy_id=7, role="coach"))


async def test_membership_approve_missing_raises() -> None:
    """Approving a non-existent membership raises ``ResourceNotFoundError``."""
    uc = MembershipUseCases(_FakeMembershipRepo())
    with pytest.raises(ResourceNotFoundError):
        await uc.approve(999)
