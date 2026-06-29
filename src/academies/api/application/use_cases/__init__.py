"""Use cases for the academies application layer.

Business-logic facades for the academy and membership aggregates, each
extending :class:`common.api.BaseUseCase`. They thread no tenant scope
(academies are user-owned, not company-scoped) and map ORM rows to domain
entities via the aggregate mappers so the presentation layer works in
domain terms only.
"""

from academies.api.application.use_cases.academy_use_cases import AcademyUseCases
from academies.api.application.use_cases.membership_use_cases import (
    MembershipUseCases,
)

__all__ = ["AcademyUseCases", "MembershipUseCases"]
