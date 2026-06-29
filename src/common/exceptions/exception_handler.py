"""Universal exception handler for FastAPI applications.

Catches all exceptions raised during request processing and converts
them into standardised ``APIResponse`` JSON envelopes. Each exception
family (app-domain, HTTP, validation, generic Python) has a dedicated
handler so that clients always receive a meaningful status code and
message.
"""

import re

import structlog
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import utils as db_utils
from django.utils.translation import gettext_lazy as _
from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from common.api.response import APIResponse
from common.exceptions.exceptions import AppBaseError

logger = structlog.get_logger(__name__)


def _error_response(
    message: str = "",
    status_code: int = 200,
    data: object = None,
) -> JSONResponse:
    return JSONResponse(
        content=APIResponse(
            data=data if data is not None else {},
            message=message,
            status=status_code,
        ).model_dump(),
        status_code=status_code,
    )


def _format_validation_error(error: dict) -> str:
    """Build a human-readable message naming the offending field.

    Pydantic's raw ``msg`` ("Field required") omits which field failed; the
    field only lives in ``loc``. Prefix the message with the humanised field
    name (last string segment of ``loc``, dropping the ``body``/``query``
    request-part prefix) so the top-level message is actionable on its own.
    """
    msg = error.get("msg") or str(_("Validation failed"))
    loc = [part for part in error.get("loc", []) if isinstance(part, str)]
    if loc and loc[0] in {"body", "query", "path", "header", "cookie"}:
        loc = loc[1:]
    if not loc:
        return msg
    field = loc[-1].replace("_", " ").capitalize()
    return f"{field}: {msg}"


class UniversalExceptionHandler:
    """Universal exception handler for generating appropriate HTTP responses."""

    @staticmethod
    def _handle_validation_exception(
        _request: Request, exc: RequestValidationError
    ) -> Response:
        errors = jsonable_encoder(exc.errors())
        first_error_msg = str(_("Validation failed"))
        if errors:
            first_error_msg = _format_validation_error(errors[0])
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=first_error_msg,
            data=errors,
        )

    @staticmethod
    def _handle_pydantic_validation_error(
        _request: Request, exc: ValidationError
    ) -> Response:
        errors = exc.errors()
        first_error_msg = str(_("Data validation failed"))
        if errors:
            first_error_msg = errors[0].get("msg", first_error_msg)
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=first_error_msg,
        )

    @staticmethod
    def _handle_django_validation_error(
        _request: Request, exc: DjangoValidationError
    ) -> Response:
        errors = (
            exc.message_dict if hasattr(exc, "message_dict") else {"error": [str(exc)]}
        )
        first_field = next(iter(errors), "")
        first_error_msg = (
            errors[first_field][0]
            if first_field and errors[first_field]
            else str(_("Invalid data"))
        )
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=first_error_msg,
            data=jsonable_encoder(errors),
        )

    @staticmethod
    def _handle_http_exception(
        _request: Request, exc: HTTPException | StarletteHTTPException
    ) -> Response:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _error_response(message=detail, status_code=exc.status_code)

    @staticmethod
    def _handle_app_base_exception(_request: Request, exc: AppBaseError) -> Response:
        return _error_response(message=exc.message, status_code=exc.status_code)

    @staticmethod
    def _handle_integrity_error(
        _request: Request, exc: db_utils.IntegrityError
    ) -> Response:
        raw = str(exc)

        if "foreign key constraint" in raw.lower():
            return _error_response(
                message=str(_("A referenced record does not exist")),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        field = ""
        match = re.search(r"UNIQUE constraint failed: \w+\.(\w+)", raw) or re.search(
            r"Key \((\w+)\)", raw
        )
        if match:
            field = match.group(1)

        if field:
            message = str(
                _("A record with this %(field)s already exists") % {"field": field}
            )
        else:
            message = str(_("A record with the provided values already exists"))

        return _error_response(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
        )

    @staticmethod
    def _handle_generic_exception(_request: Request, exc: Exception) -> Response:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_message = str(_("Internal Server Error"))

        if isinstance(exc, ValueError | TypeError | KeyError):
            status_code = status.HTTP_400_BAD_REQUEST
            error_message = str(exc)
        elif isinstance(exc, FileNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
            error_message = str(exc)
        elif isinstance(exc, PermissionError):
            status_code = status.HTTP_403_FORBIDDEN
            error_message = str(exc)
        elif isinstance(exc, TimeoutError):
            status_code = status.HTTP_408_REQUEST_TIMEOUT
            error_message = str(exc)
        elif isinstance(exc, ConnectionError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            error_message = str(exc)
        else:
            logger.info(
                "unhandled_exception",
                ex_msg=str(exc),
                ex_type=type(exc).__name__,
                path=_request.url.path,
                exc_info=True,
            )

        return _error_response(message=error_message, status_code=status_code)

    async def handle_all_exceptions(self, request: Request, exc: Exception) -> Response:
        if isinstance(exc, AppBaseError):
            return self._handle_app_base_exception(request, exc)

        if isinstance(exc, HTTPException | StarletteHTTPException):
            return self._handle_http_exception(request, exc)

        if isinstance(exc, RequestValidationError):
            return self._handle_validation_exception(request, exc)

        if isinstance(exc, ValidationError):
            return self._handle_pydantic_validation_error(request, exc)

        if isinstance(exc, DjangoValidationError):
            return self._handle_django_validation_error(request, exc)

        if isinstance(exc, db_utils.IntegrityError):
            return self._handle_integrity_error(request, exc)

        if isinstance(exc, db_utils.DatabaseError):
            logger.info(
                "database_error",
                ex_msg=str(exc),
                ex_type=type(exc).__name__,
                path=request.url.path,
                exc_info=True,
            )
            return _error_response(
                message=str(_("A database error occurred")),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return self._handle_generic_exception(request, exc)


universal_handler = UniversalExceptionHandler()


async def universal_exception_handler(request: Request, exc: Exception) -> Response:
    return await universal_handler.handle_all_exceptions(request, exc)
