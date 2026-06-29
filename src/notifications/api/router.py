"""Top-level router for the notifications app (mounted at /notifications)."""

from fastapi import APIRouter

from notifications.api.v1.router import router as v1_router

router = APIRouter(prefix="/notifications")
router.include_router(v1_router)
