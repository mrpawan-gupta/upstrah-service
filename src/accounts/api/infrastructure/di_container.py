"""Dependency-injection container for the accounts app.

Single composition root: one ``DIContainer`` holding one explicit, typed,
lazily-memoised slot per collaborator, and one ``get_<x>_controller``
factory per controller. The container assembles repository → use case →
controller; endpoints obtain a controller only via
``Depends(get_<x>_controller)``. No business logic, no request/tenant
state, no ``functools.cached_property`` / ``lru_cache`` / generic dict.
"""

from __future__ import annotations

from accounts.api.application.interfaces.otp_dispatcher import IOTPDispatcher
from accounts.api.application.use_cases.auth_use_cases import AuthUseCases
from accounts.api.application.use_cases.otp_use_cases import OTPUseCases
from accounts.api.application.use_cases.user_profile_use_cases import (
    UserProfileUseCases,
)
from accounts.api.domain.repositories.auth_repository import IAuthRepository
from accounts.api.domain.repositories.otp_repository import IOTPRepository
from accounts.api.domain.repositories.user_profile_repository import (
    IUserProfileRepository,
)
from accounts.api.infrastructure.repositories.auth_repository_impl import (
    AuthRepositoryImpl,
)
from accounts.api.infrastructure.repositories.otp_repository_impl import (
    OTPRepositoryImpl,
)
from accounts.api.infrastructure.repositories.user_profile_repository_impl import (
    UserProfileRepositoryImpl,
)
from accounts.api.infrastructure.services.mock_otp_dispatcher import MockOTPDispatcher
from accounts.api.presentation.controllers.auth_controller import AuthController
from accounts.api.presentation.controllers.otp_controller import OTPController
from accounts.api.presentation.controllers.user_profile_controller import (
    UserProfileController,
)


class DIContainer:
    """Composition root for the accounts app — one typed slot per collaborator.

    Component stacks:

    * **Auth**: ``AuthRepositoryImpl`` + ``MockOTPDispatcher`` →
      ``AuthUseCases`` → ``AuthController`` (also composes
      ``UserProfileUseCases`` for ``/auth/me``).
    * **OTP**: ``OTPRepositoryImpl`` → ``OTPUseCases`` → ``OTPController``.
    * **UserProfile**: ``UserProfileRepositoryImpl`` →
      ``UserProfileUseCases`` → ``UserProfileController``.
    """

    def __init__(self) -> None:
        """Initialise every cached component slot to ``None``."""
        self._auth_repository: IAuthRepository | None = None
        self._otp_repository: IOTPRepository | None = None
        self._user_profile_repository: IUserProfileRepository | None = None
        self._otp_dispatcher: IOTPDispatcher | None = None

        self._auth_use_cases: AuthUseCases | None = None
        self._otp_use_cases: OTPUseCases | None = None
        self._user_profile_use_cases: UserProfileUseCases | None = None

        self._auth_controller: AuthController | None = None
        self._otp_controller: OTPController | None = None
        self._user_profile_controller: UserProfileController | None = None

    # --- Repositories -----------------------------------------------------
    async def get_auth_repository(self) -> IAuthRepository:
        """Return the cached ``AuthRepositoryImpl`` singleton."""
        if self._auth_repository is None:
            self._auth_repository = AuthRepositoryImpl()
        return self._auth_repository

    async def get_otp_repository(self) -> IOTPRepository:
        """Return the cached ``OTPRepositoryImpl`` singleton."""
        if self._otp_repository is None:
            self._otp_repository = OTPRepositoryImpl()
        return self._otp_repository

    async def get_user_profile_repository(self) -> IUserProfileRepository:
        """Return the cached ``UserProfileRepositoryImpl`` singleton."""
        if self._user_profile_repository is None:
            self._user_profile_repository = UserProfileRepositoryImpl()
        return self._user_profile_repository

    async def get_otp_dispatcher(self) -> IOTPDispatcher:
        """Return the cached mocked ``MockOTPDispatcher`` singleton."""
        if self._otp_dispatcher is None:
            self._otp_dispatcher = MockOTPDispatcher()
        return self._otp_dispatcher

    # --- Use cases --------------------------------------------------------
    async def get_auth_use_cases(self) -> AuthUseCases:
        """Return the cached ``AuthUseCases`` singleton."""
        if self._auth_use_cases is None:
            self._auth_use_cases = AuthUseCases(
                repo=await self.get_auth_repository(),
                otp_repo=await self.get_otp_repository(),
                otp_dispatcher=await self.get_otp_dispatcher(),
            )
        return self._auth_use_cases

    async def get_otp_use_cases(self) -> OTPUseCases:
        """Return the cached ``OTPUseCases`` singleton."""
        if self._otp_use_cases is None:
            self._otp_use_cases = OTPUseCases(await self.get_otp_repository())
        return self._otp_use_cases

    async def get_user_profile_use_cases(self) -> UserProfileUseCases:
        """Return the cached ``UserProfileUseCases`` singleton."""
        if self._user_profile_use_cases is None:
            self._user_profile_use_cases = UserProfileUseCases(
                await self.get_user_profile_repository()
            )
        return self._user_profile_use_cases

    # --- Controllers ------------------------------------------------------
    async def get_auth_controller(self) -> AuthController:
        """Return the cached ``AuthController`` singleton."""
        if self._auth_controller is None:
            self._auth_controller = AuthController(
                await self.get_auth_use_cases(),
                await self.get_user_profile_use_cases(),
            )
        return self._auth_controller

    async def get_otp_controller(self) -> OTPController:
        """Return the cached ``OTPController`` singleton."""
        if self._otp_controller is None:
            self._otp_controller = OTPController(await self.get_otp_use_cases())
        return self._otp_controller

    async def get_user_profile_controller(self) -> UserProfileController:
        """Return the cached ``UserProfileController`` singleton."""
        if self._user_profile_controller is None:
            self._user_profile_controller = UserProfileController(
                await self.get_user_profile_use_cases()
            )
        return self._user_profile_controller


di_container = DIContainer()


async def get_auth_controller() -> AuthController:
    """FastAPI dependency — the ONLY way an endpoint gets an ``AuthController``."""
    return await di_container.get_auth_controller()


async def get_otp_controller() -> OTPController:
    """FastAPI dependency — the ONLY way an endpoint gets an ``OTPController``."""
    return await di_container.get_otp_controller()


async def get_user_profile_controller() -> UserProfileController:
    """FastAPI dependency — the ONLY way an endpoint gets a ``UserProfileController``."""
    return await di_container.get_user_profile_controller()
