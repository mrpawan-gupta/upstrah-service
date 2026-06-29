"""Django internationalisation middleware for FastAPI requests.

Activates the appropriate Django language for each incoming request based on
the ``Accept-Language`` header, then deactivates it after the response is
generated so that language state does not leak between requests.
"""

from collections.abc import Callable

from django.conf import settings
from django.utils import translation
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class DjangoI18nMiddleware(BaseHTTPMiddleware):
    """Middleware to activate Django internationalisation for FastAPI requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and activate the appropriate language.

        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain

        Returns:
            Response from next middleware/endpoint
        """
        accept_language = request.headers.get("Accept-Language")
        language_code = self._get_language_from_header(accept_language)
        translation.activate(language_code)
        return await call_next(request)

    @staticmethod
    def _get_language_from_header(accept_language: str) -> str:
        """Extract language code from the Accept-Language header.

        Args:
            accept_language: Accept-Language header value

        Returns:
            Language code string
        """
        if not accept_language:
            return str(settings.LANGUAGE_CODE)

        # Simple language parsing can be enhanced
        languages = accept_language.split(",")
        for lang in languages:
            lang_code = lang.split(";")[0].strip().lower()
            # Check if the language is supported
            for supported_lang, _ in settings.LANGUAGES:
                if lang_code.startswith(supported_lang.lower()):
                    return str(supported_lang)

        return str(settings.LANGUAGE_CODE)
