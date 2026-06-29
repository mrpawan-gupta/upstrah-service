"""Top-level router for the teams app (mounted at /teams)."""

from fastapi import APIRouter

from teams.api.v1.router import router as v1_router

router = APIRouter(prefix="/teams")
router.include_router(v1_router)
