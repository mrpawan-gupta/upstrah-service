"""Rate-limiting middleware for Django and FastAPI.

Provides two middleware classes:

* :class:`RateLimitMiddleware` — Django ``MiddlewareMixin`` that enforces an
  hourly request cap per client (user ID or IP) using the Django cache backend.
* :class:`FastAPIRateLimitMiddleware` — Starlette ``BaseHTTPMiddleware`` that
  enforces per-minute and per-hour caps in the FastAPI pipeline.

Both middlewares fail-open: if the cache backend is unavailable, requests are
allowed through to avoid service disruption.
"""

import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext_lazy as _
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from common.api.response import APIResponse


class RateLimitMiddleware(MiddlewareMixin):
    """Django middleware that enforces a per-client hourly request cap.

    Uses the Django cache backend (Redis in production) to track request counts
    per client.  Clients are identified by authenticated user ID or IP address.
    Requests to paths in ``exempt_paths`` bypass the check entirely.

    Attributes:
        rate_limit_requests: Maximum allowed requests per window (default 100).
        rate_limit_window: Window length in seconds (default 3600 — 1 hour).
        rate_limit_enabled: Feature flag; when ``False`` no limiting is applied.
        exempt_paths: List of URL path prefixes exempt from rate limiting.
    """

    def __init__(self, get_response) -> None:
        """Initialise rate-limit settings from Django settings.

        Args:
            get_response: Django callable that returns a response for a request.
        """
        super().__init__(get_response=get_response)
        # Rate limiting settings
        self.rate_limit_requests = getattr(settings, "RATE_LIMIT_REQUESTS", 100)
        self.rate_limit_window = getattr(settings, "RATE_LIMIT_WINDOW", 3600)  # 1 hour
        self.rate_limit_enabled = getattr(settings, "RATE_LIMIT_ENABLED", True)

        # Exempt paths from rate limiting
        self.exempt_paths = getattr(
            settings,
            "RATE_LIMIT_EXEMPT_PATHS",
            [
                "/api/health",
                "/api/swagger",
                "/api/redoc",
                "/api/openapi.json",
            ],
        )

    def __call__(self, request):
        """Process the request through the Django middleware chain.

        Args:
            request: Incoming Django HTTP request.

        Returns:
            The HTTP response from the next layer in the middleware stack.
        """
        return self.get_response(request)

    def process_request(self, request: HttpRequest) -> JsonResponse | None:
        """Check the per-client request rate and reject over-limit requests.

        Skips rate limiting when disabled or when the path is in
        ``exempt_paths``.

        Args:
            request: Incoming Django HTTP request.

        Returns:
            ``None`` when the request is allowed through; a 429
            ``JsonResponse`` when the rate limit is exceeded.
        """
        if not self.rate_limit_enabled:
            return None

        # Skip rate limiting for exempt paths
        if any(request.path.startswith(path) for path in self.exempt_paths):
            return None

        # Determine client identifier
        client_id = self._get_client_id(request)

        # Check rate limit
        if self._is_rate_limited(client_id):
            return self._rate_limit_response()

        return None

    @staticmethod
    def _get_client_id(request: HttpRequest) -> str:
        """Extract a stable client identifier for rate-limit tracking.

        Uses ``user:<id>`` for authenticated users, falling back to
        ``ip:<address>`` resolved from the ``X-Forwarded-For`` header or
        ``REMOTE_ADDR``.

        Args:
            request: Incoming Django HTTP request.

        Returns:
            A string key in the form ``"user:<id>"`` or ``"ip:<addr>"``.
        """
        # Try to get user ID if authenticated
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = getattr(request.user, "id", None)
            if user_id is not None:
                return f"user:{user_id}"

        # Fall back to IP address
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")

        return f"ip:{ip}"

    def _is_rate_limited(self, client_id: str) -> bool:
        """Check whether a client has exceeded the configured hourly request limit.

        Increments the cache counter on each call.  Fails open (returns
        ``False``) if the cache backend raises an exception.

        Args:
            client_id: Client identifier string (see :meth:`_get_client_id`).

        Returns:
            ``True`` when the client is over the limit; ``False`` otherwise.
        """
        try:
            cache_key = f"rate_limit:{client_id}"
            current_requests = cache.get(cache_key, 0)
            if current_requests >= self.rate_limit_requests:
                return True
            # Increment request count
            cache.set(cache_key, current_requests + 1, self.rate_limit_window)
        except Exception:
            # Fail open - don't block requests if cache is down
            return False
        else:
            return False

    @staticmethod
    def _rate_limit_response() -> JsonResponse:
        """Build a 429 Too Many Requests ``JsonResponse``.

        Returns:
            ``JsonResponse`` wrapping the standard ``APIResponse`` envelope
            with ``status=429`` and ``success=False``.
        """
        return JsonResponse(
            APIResponse(
                message=str(_("Too many requests")),
                status=429,
                success=False,
            ).model_dump(),
            status=429,
        )


class FastAPIRateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware for per-minute and per-hour rate limiting in FastAPI.

    Enforces two independent sliding-window rate limits per client (identified
    by user ID or IP address).  Paths listed in ``exempt_paths`` bypass all
    checks.  Fails open when the cache backend is unavailable.

    Attributes:
        requests_per_minute: Maximum requests allowed per 60-second window.
        requests_per_hour: Maximum requests allowed per 3600-second window.
        exempt_paths: Set of URL paths exempt from rate limiting.
    """

    def __init__(
        self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000
    ) -> None:
        """Initialise with per-minute and per-hour request limits.

        Args:
            app: ASGI application wrapped by this middleware.
            requests_per_minute: Maximum requests per 60-second window (default 60).
            requests_per_hour: Maximum requests per 3600-second window (default 1000).
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour

        # Exempt path prefixes (health probes must never be rate-limited)
        self.exempt_paths = (
            "/api/health",
            "/api/swagger",
            "/api/redoc",
            "/api/openapi.json",
        )

    async def dispatch(self, request: Request, call_next):
        """Process request for rate limiting.
        Args:
            request: Starlette request
            call_next: Next middleware/endpoint

        Returns:
            Response from next middleware or rate limit error
        """
        # Skip rate limiting for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Check rate limits
        if self._is_rate_limited(client_id):
            return JSONResponse(
                content=APIResponse(
                    message=str(_("Too many requests")), status=429, success=False
                ).model_dump(),
                status_code=429,
            )

        return await call_next(request)

    @staticmethod
    def _get_client_id(request: Request) -> str:
        """Extract a stable client identifier for rate-limit tracking.

        Prefers ``request.state.user_id`` (set by auth middleware); falls
        back to the client IP, honouring ``X-Forwarded-For``.

        Args:
            request: Incoming Starlette/FastAPI request.

        Returns:
            A string key in the form ``"user:<id>"`` or ``"ip:<addr>"``.
        """
        # Try to get user ID from request state (set by auth middleware)
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"

        # Check for forwarded IP
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        return f"ip:{client_ip}"

    def _is_rate_limited(self, client_id: str) -> bool:
        """Check whether a client has exceeded either the per-minute or per-hour limit.

        Increments both cache counters on each call.  Fails open when the
        cache backend raises an exception.

        Args:
            client_id: Client identifier string (see :meth:`_get_client_id`).

        Returns:
            ``True`` when either limit is exceeded; ``False`` otherwise.
        """
        try:
            current_time = int(time.time())

            # Check minute-based rate limit
            minute_key = f"rate_limit:minute:{client_id}:{current_time // 60}"
            minute_requests = cache.get(minute_key, 0)

            if minute_requests >= self.requests_per_minute:
                return True

            # Check hour-based rate limit
            hour_key = f"rate_limit:hour:{client_id}:{current_time // 3600}"
            hour_requests = cache.get(hour_key, 0)

            if hour_requests >= self.requests_per_hour:
                return True

            # Increment counters
            cache.set(minute_key, minute_requests + 1, 120)  # 2 minutes TTL
            cache.set(hour_key, hour_requests + 1, 7200)  # 2 hours TTL

        except Exception:
            # Fail open
            return False
        else:
            return False
