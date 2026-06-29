"""ASGI entry-point for the Rudra auth service (Django + FastAPI hybrid)."""

# ruff: noqa: E402
import os

from django.apps import apps
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "upstrah.settings.local")

application = get_wsgi_application()
apps.populate(settings.INSTALLED_APPS)

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import utils as db_utils
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from common.exceptions.exception_handler import universal_exception_handler
from common.exceptions.exceptions import AppBaseError
from common.middleware.i18n import DjangoI18nMiddleware
from common.middleware.logging import FastAPIRequestLoggingMiddleware
from common.middleware.ratelimiting import FastAPIRateLimitMiddleware
from common.middleware.security import FastAPISecurityHeadersMiddleware
from upstrah.routers import router as api_router


def get_application() -> FastAPI:
    """Construct and configure the FastAPI application instance.

    Attaches:

    * :class:`~fastapi.middleware.cors.CORSMiddleware` — cross-origin headers.
    * :class:`~common.middleware.i18n.DjangoI18nMiddleware` — i18n activation.
    * :class:`~common.middleware.logging.FastAPIRequestLoggingMiddleware` — structured
      request/response logging.
    * Exception handlers for every exception family the app may raise, all
      routing to :func:`~common.exceptions.exception_handler.universal_exception_handler`.
    * The top-level API router from ``rudra.routers``.

    Returns:
        Fully configured :class:`~fastapi.FastAPI` application instance.
    """
    fastapi_app = FastAPI(
        title="Upstrah Service",
        openapi_url="/api/openapi.json",
        docs_url="/api/swagger/",
        redoc_url="/api/redoc/",
        debug=settings.DEBUG,
    )

    _cors_origins = (
        ["*"]
        if getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False)
        else getattr(settings, "CORS_ALLOWED_ORIGINS", [])
    )
    _cors_origin_regex = getattr(settings, "CORS_ALLOWED_ORIGIN_REGEXES", None)
    # Starlette accepts a single regex; combine multiple patterns with |.
    _combined_regex = (
        "|".join(f"({r})" for r in _cors_origin_regex) if _cors_origin_regex else None
    )

    # Starlette middleware execution order is LIFO — the last add_middleware
    # call becomes the outermost layer.  CORSMiddleware MUST be outermost so
    # it can handle OPTIONS preflight requests before any other middleware
    # (rate limiter, security headers) can reject or modify the response.
    fastapi_app.add_middleware(DjangoI18nMiddleware)
    fastapi_app.add_middleware(FastAPIRequestLoggingMiddleware)
    fastapi_app.add_middleware(FastAPISecurityHeadersMiddleware)
    fastapi_app.add_middleware(FastAPIRateLimitMiddleware)
    # CORSMiddleware added last → outermost → handles preflight first.
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_origin_regex=_combined_regex,
        allow_credentials=getattr(settings, "CORS_ALLOW_CREDENTIALS", False),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    fastapi_app.add_exception_handler(AppBaseError, universal_exception_handler)
    fastapi_app.add_exception_handler(
        StarletteHTTPException, universal_exception_handler
    )
    fastapi_app.add_exception_handler(
        RequestValidationError, universal_exception_handler
    )
    fastapi_app.add_exception_handler(
        PydanticValidationError, universal_exception_handler
    )
    fastapi_app.add_exception_handler(
        DjangoValidationError, universal_exception_handler
    )
    fastapi_app.add_exception_handler(
        db_utils.IntegrityError, universal_exception_handler
    )
    fastapi_app.add_exception_handler(
        db_utils.DatabaseError, universal_exception_handler
    )
    # Catch-all fallback (goes to ServerErrorMiddleware — last resort).
    fastapi_app.add_exception_handler(Exception, universal_exception_handler)
    fastapi_app.include_router(api_router, prefix="")

    return fastapi_app


app = get_application()
