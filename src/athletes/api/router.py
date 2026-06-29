"""Top-level router for the athletes app (mounted at /athletes)."""

from fastapi import APIRouter

from athletes.api.v1.router import router as v1_router

router = APIRouter(prefix="/athletes")
router.include_router(v1_router)
