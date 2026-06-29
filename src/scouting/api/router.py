"""Top-level router for the scouting app (mounted at /scouting)."""

from fastapi import APIRouter

from scouting.api.v1.router import router as v1_router

router = APIRouter(prefix="/scouting")
router.include_router(v1_router)
