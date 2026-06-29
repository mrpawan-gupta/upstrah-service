"""Dependency-injection container for the academies app.

Single composition root: one ``DIContainer`` holding one explicit, typed,
lazily-memoised slot per collaborator, and one ``get_<x>_controller``
factory per controller. The container assembles repository → use case →
controller; endpoints obtain a controller only via
``Depends(get_<x>_controller)``. No business logic, no request/tenant
state, no ``functools.cached_property`` / ``lru_cache`` / generic dict.
"""

from __future__ import annotations

from academies.api.application.use_cases.academy_use_cases import AcademyUseCases
from academies.api.application.use_cases.membership_use_cases import (
    MembershipUseCases,
)
from academies.api.domain.repositories.academy_repository import IAcademyRepository
from academies.api.domain.repositories.membership_repository import (
    IMembershipRepository,
)
from academies.api.infrastructure.repositories.academy_repository_impl import (
    AcademyRepositoryImpl,
)
from academies.api.infrastructure.repositories.membership_repository_impl import (
    MembershipRepositoryImpl,
)
from academies.api.presentation.controllers.academy_controller import (
    AcademyController,
)
from academies.api.presentation.controllers.membership_controller import (
    MembershipController,
)


class DIContainer:
    """Composition root for the academies app — one typed slot per collaborator.

    Component stacks:

    * **Academy**: ``AcademyRepositoryImpl`` → ``AcademyUseCases`` →
      ``AcademyController``.
    * **Membership**: ``MembershipRepositoryImpl`` → ``MembershipUseCases`` →
      ``MembershipController``.
    """

    def __init__(self) -> None:
        """Initialise every cached component slot to ``None``."""
        self._academy_repository: IAcademyRepository | None = None
        self._membership_repository: IMembershipRepository | None = None

        self._academy_use_cases: AcademyUseCases | None = None
        self._membership_use_cases: MembershipUseCases | None = None

        self._academy_controller: AcademyController | None = None
        self._membership_controller: MembershipController | None = None

    # --- Repositories -----------------------------------------------------
    async def get_academy_repository(self) -> IAcademyRepository:
        """Return the cached ``AcademyRepositoryImpl`` singleton."""
        if self._academy_repository is None:
            self._academy_repository = AcademyRepositoryImpl()
        return self._academy_repository

    async def get_membership_repository(self) -> IMembershipRepository:
        """Return the cached ``MembershipRepositoryImpl`` singleton."""
        if self._membership_repository is None:
            self._membership_repository = MembershipRepositoryImpl()
        return self._membership_repository

    # --- Use cases --------------------------------------------------------
    async def get_academy_use_cases(self) -> AcademyUseCases:
        """Return the cached ``AcademyUseCases`` singleton."""
        if self._academy_use_cases is None:
            self._academy_use_cases = AcademyUseCases(
                await self.get_academy_repository()
            )
        return self._academy_use_cases

    async def get_membership_use_cases(self) -> MembershipUseCases:
        """Return the cached ``MembershipUseCases`` singleton."""
        if self._membership_use_cases is None:
            self._membership_use_cases = MembershipUseCases(
                await self.get_membership_repository()
            )
        return self._membership_use_cases

    # --- Controllers ------------------------------------------------------
    async def get_academy_controller(self) -> AcademyController:
        """Return the cached ``AcademyController`` singleton."""
        if self._academy_controller is None:
            self._academy_controller = AcademyController(
                await self.get_academy_use_cases()
            )
        return self._academy_controller

    async def get_membership_controller(self) -> MembershipController:
        """Return the cached ``MembershipController`` singleton."""
        if self._membership_controller is None:
            self._membership_controller = MembershipController(
                await self.get_membership_use_cases()
            )
        return self._membership_controller


di_container = DIContainer()


async def get_academy_controller() -> AcademyController:
    """FastAPI dependency — the ONLY way an endpoint gets an ``AcademyController``."""
    return await di_container.get_academy_controller()


async def get_membership_controller() -> MembershipController:
    """FastAPI dependency — the ONLY way an endpoint gets a ``MembershipController``."""
    return await di_container.get_membership_controller()
