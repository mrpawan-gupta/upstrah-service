"""FastAPI application factory.

Aggregates each Django app's own ``api`` router (apps expose
``<app>/api/router.py``) into a single FastAPI app, mounted under ``/api`` by
the ASGI entrypoint. The accounts router mounts under ``/accounts``, so its
endpoints are reachable at ``/accounts/api/v1/...``.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from accounts.api.router import router as accounts_router
from common.exceptions.exception_handler import universal_exception_handler
from common.exceptions.exceptions import AppBaseError


def create_fastapi_app() -> FastAPI:
    """Build and return the configured FastAPI application.

    Wires CORS, the universal exception handler (so typed
    ``common.exceptions`` errors render the standard ``APIResponse``
    envelope), a health probe, and the accounts app router.
    """
    app = FastAPI(title="Upstrah API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Route typed/validation/HTTP/generic errors through the shared envelope.
    app.add_exception_handler(AppBaseError, universal_exception_handler)
    app.add_exception_handler(RequestValidationError, universal_exception_handler)
    app.add_exception_handler(StarletteHTTPException, universal_exception_handler)
    app.add_exception_handler(Exception, universal_exception_handler)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(accounts_router)
    return app
