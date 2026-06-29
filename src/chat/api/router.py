"""Top-level router for the chat app (mounted at /chat)."""

from fastapi import APIRouter

from chat.api.v1.router import router as v1_router

router = APIRouter(prefix="/chat")
router.include_router(v1_router)
