"""Top-level FastAPI router — mounts the accounts and scheduler routers.

Wires the ``accounts`` and ``scheduler`` routers under a single root router
that is included in the FastAPI ``app`` instance created in ``rudra/asgi.py``.
"""

from fastapi import APIRouter, status

from academies.api.router import router as academies_router
from accounts.api.router import router as accounts_router
from athletes.api.router import router as athletes_router
from chat.api.router import router as chat_router
from feed.api.router import router as feed_router
from notifications.api.router import router as notifications_router
from scouting.api.router import router as scouting_router
from teams.api.router import router as teams_router
from training.api.router import router as training_router

router = APIRouter()

router.include_router(accounts_router)
router.include_router(academies_router)
router.include_router(athletes_router)
router.include_router(teams_router)
router.include_router(training_router)
router.include_router(scouting_router)
router.include_router(feed_router)
router.include_router(chat_router)
router.include_router(notifications_router)


@router.get(
    "/.well-known/jwks.json",
    status_code=status.HTTP_200_OK,
    summary="JSON Web Key Set (JWKS)",
    tags=["jwks"],
)
async def jwks() -> dict:
    """Return the public JWKS so downstream services can verify RS256 tokens.

    The JWKS contains the RSA public key used to sign all access tokens.
    Downstream services (VMS, care-service) should fetch this on startup and
    cache the result; refresh when they encounter a ``kid`` mismatch.

    Returns:
        Standard JWKS document: ``{"keys": [<JWK>]}``.
    """
    from common.auth.jwt.handler import jwt_handler

    return {"keys": [jwt_handler.get_public_jwk()]}


@router.get("/api/health/live", status_code=status.HTTP_200_OK, tags=["health"])
async def liveness() -> dict:
    """Kubernetes liveness probe — returns 200 if the process is alive."""
    from common.observability.health import HealthCheckService

    return HealthCheckService.instance().liveness_probe()


@router.get("/api/health/ready", status_code=status.HTTP_200_OK, tags=["health"])
async def readiness() -> dict:
    """Kubernetes readiness probe — 200 when DB and Redis are reachable."""
    from common.observability.health import HealthCheckService

    return await HealthCheckService.instance().readiness_probe()
