"""Top-level router for the feed app (mounted at /feed)."""

from fastapi import APIRouter

from feed.api.v1.router import router as v1_router

router = APIRouter(prefix="/feed")
router.include_router(v1_router)
