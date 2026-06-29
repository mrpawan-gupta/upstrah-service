"""Concrete Django-ORM repositories for the academies app.

Implement the domain repository interfaces over the ``Academy`` and
``Membership`` models, inheriting the shared async CRUD surface from
:class:`common.api.BaseRepository`. Data access only.
"""

from academies.api.infrastructure.repositories.academy_repository_impl import (
    AcademyRepositoryImpl,
)
from academies.api.infrastructure.repositories.membership_repository_impl import (
    MembershipRepositoryImpl,
)

__all__ = ["AcademyRepositoryImpl", "MembershipRepositoryImpl"]
