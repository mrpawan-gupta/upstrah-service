"""Versioned router for the academies API (v1).

Mounts the v1 endpoint routers under the ``/api/v1`` prefix:

* ``academy_endpoints``    — academy CRUD
* ``membership_endpoints`` — apply / list / approve / reject memberships

The app-level router (:mod:`academies.api.router`) mounts this under
``/academies``, so the final paths are ``/academies/api/v1/...``.
"""

from fastapi import APIRouter

from academies.api.v1.academy_endpoints import router as academy_router
from academies.api.v1.membership_endpoints import router as membership_router

router = APIRouter(prefix="/api/v1")
router.include_router(academy_router)
router.include_router(membership_router)
