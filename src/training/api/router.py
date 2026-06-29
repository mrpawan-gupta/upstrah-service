"""Top-level router for the training app (mounted at /training)."""

from fastapi import APIRouter

from training.api.v1.router import router as v1_router

router = APIRouter(prefix="/training")
router.include_router(v1_router)
