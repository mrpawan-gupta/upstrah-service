"""Top-level FastAPI router for the accounts app.

Mounts the versioned v1 router under the ``/accounts`` prefix so every
accounts endpoint is reachable at ``/accounts/api/v1/...``. This router is
included by the project FastAPI factory in ``upstrah/api.py``.
"""

from fastapi import APIRouter

from accounts.api.v1.router import router as v1_router

router = APIRouter(prefix="/accounts")
router.include_router(v1_router)
