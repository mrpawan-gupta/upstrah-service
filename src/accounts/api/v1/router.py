"""Versioned router for the accounts API (v1).

Mounts the v1 endpoint routers under the ``/api/v1`` prefix:

* ``auth_endpoints``         — phone → OTP → JWT login, refresh, logout, me
* ``otp_endpoints``          — OTP admin (create/list/get/invalidate)
* ``user_profile_endpoints`` — 1:1 onboarding profile read/update

The app-level router (:mod:`accounts.api.router`) mounts this under
``/accounts``, so the final paths are ``/accounts/api/v1/...``.
"""

from fastapi import APIRouter

from accounts.api.v1.auth_endpoints import router as auth_router
from accounts.api.v1.otp_endpoints import router as otp_router
from accounts.api.v1.user_profile_endpoints import router as user_profile_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(otp_router)
router.include_router(user_profile_router)
