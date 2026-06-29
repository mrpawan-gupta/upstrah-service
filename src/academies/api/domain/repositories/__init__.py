"""Abstract repository interfaces for the academies app.

Pure ``abc.ABC`` contracts the use-case layer depends on. The concrete
implementations live in ``infrastructure/repositories`` and pair these
with :class:`common.api.BaseRepository`.
"""

from academies.api.domain.repositories.academy_repository import IAcademyRepository
from academies.api.domain.repositories.membership_repository import (
    IMembershipRepository,
)

__all__ = ["IAcademyRepository", "IMembershipRepository"]
