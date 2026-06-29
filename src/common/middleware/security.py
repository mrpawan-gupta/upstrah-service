"""Security-header middleware for Django and FastAPI responses.

Provides two middleware classes:

* :class:`SecurityHeadersMiddleware` — Django ``MiddlewareMixin`` that injects
  security headers on every outgoing Django response.
* :class:`FastAPISecurityHeadersMiddleware` — Starlette ``BaseHTTPMiddleware``
  that injects the same headers in the FastAPI pipeline.

Both middlewares mitigate common web vulnerabilities such as clickjacking,
XSS, MIME sniffing, and insecure transport.
"""

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Django middleware that appends security headers to every response.

    Headers applied:

    * ``Content-Security-Policy`` — restricts resource origins.
    * ``X-Frame-Options: DENY`` — prevents clickjacking.
    * ``X-Content-Type-Options: nosniff`` — blocks MIME-type sniffing.
    * ``X-XSS-Protection: 1; mode=block`` — legacy XSS filter hint.
    * ``Referrer-Policy: strict-origin-when-cross-origin``.
    * ``Permissions-Policy`` — disables unused browser APIs.
    * ``Strict-Transport-Security`` — added only on HTTPS requests.
    """

    def __call__(self, request):
        """Pass the request through and let ``process_response`` add headers.

        Args:
            request: Incoming Django HTTP request.

        Returns:
            The HTTP response from the next layer in the middleware stack.
        """
        return self.get_response(request)

    @staticmethod
    def process_response(request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Append security headers to the outgoing HTTP response.

        Args:
            request: Incoming HTTP request (used to check HTTPS).
            response: HTTP response to augment with security headers.

        Returns:
            The modified HTTP response with all security headers set.
        """
        # Content Security Policy
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://storage.googleapis.com https://*.googleapis.com"
        )

        # X-Frame-Options
        response["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options
        response["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection
        response["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy
        response["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )

        # Strict Transport Security (HTTPS only)
        if request.is_secure():
            response["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


_DOCS_PATHS = frozenset({"/api/swagger/", "/api/swagger", "/api/redoc/", "/api/redoc"})


class FastAPISecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that injects security headers on every FastAPI response.

    Headers applied:

    * ``Content-Security-Policy`` — restricts resource origins.
    * ``X-Frame-Options: DENY`` — prevents clickjacking.
    * ``X-Content-Type-Options: nosniff`` — blocks MIME-type sniffing.
    * ``X-XSS-Protection: 1; mode=block`` — legacy XSS filter hint.
    * ``Referrer-Policy: strict-origin-when-cross-origin``.
    * ``Permissions-Policy`` — disables unused browser APIs.
    * ``Strict-Transport-Security`` — added only on HTTPS requests.

    The ``Content-Security-Policy`` header is intentionally omitted for
    ``/api/swagger/`` and ``/api/redoc/`` so that the Swagger / Redoc UI
    pages can load their scripts and stylesheets from the CDN without
    being blocked.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Invoke the next handler and attach security headers to the response.

        Args:
            request: Incoming Starlette/FastAPI request.
            call_next: Callable that passes the request to the next middleware
                or endpoint and returns its response.

        Returns:
            The HTTP response with all security headers set.
        """
        response = await call_next(request)

        if request.url.path not in _DOCS_PATHS:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://storage.googleapis.com https://*.googleapis.com"
            )

        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response
