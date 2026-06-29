"""Top-level FastAPI router for the academies app.

Mounts the versioned v1 router under the ``/academies`` prefix so every
academies endpoint is reachable at ``/academies/api/v1/...``. This router is
included by the project top-level router in ``upstrah/routers.py``.
"""

from fastapi import APIRouter

from academies.api.v1.router import router as v1_router

router = APIRouter(prefix="/academies")
router.include_router(v1_router)
