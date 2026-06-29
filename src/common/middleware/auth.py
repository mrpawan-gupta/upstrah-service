"""JWT authentication middleware for Django and FastAPI.

Provides two middleware classes:

* :class:`JWTAuthenticationMiddleware` — Django ``MiddlewareMixin`` that
  validates bearer tokens on traditional Django view paths.
* :class:`FastAPIJWTMiddleware` — Starlette ``BaseHTTPMiddleware`` that
  validates bearer tokens in the FastAPI/Starlette request pipeline.

No User model query is performed — a :class:`~common.auth.token_user.TokenUser`
is constructed from the validated payload and attached to the request,
mirroring the SimpleJWT pattern.  Identity resolution is left to each
endpoint's ``get_current_user`` dependency.

Note: The primary authentication path for FastAPI endpoints uses the
``get_current_user`` dependency in ``common.auth.dependencies``, not these
middleware classes.
"""

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from common.api.response import APIResponse
from common.auth.jwt.token_user import TokenUser
from common.context import set_company_ids, set_user_id, set_user_token


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """Django middleware that validates JWT bearer tokens without a DB lookup.

    Verifies the token via ``jwt_handler.verify_token()`` (RS256 + blacklist
    check) and wraps the decoded payload in a :class:`~common.auth.token_user.TokenUser`.
    No User model query is made — identity is read from the payload claims,
    keeping this middleware safe to use in services that do not own the User
    table (microservice pattern).

    Attributes:
        get_response: The next callable in the Django middleware chain.
        exempt_paths: Path prefixes that bypass authentication entirely.
    """

    def __init__(self, get_response) -> None:
        """Initialise the middleware with settings and exempt-path configuration.

        Args:
            get_response: Django callable that returns a response for a request.
        """
        super().__init__(get_response=get_response)
        self.get_response = get_response
        self.exempt_paths = getattr(
            settings,
            "JWT_EXEMPT_PATHS",
            [
                "/api/v1/ping",
                "/api/health",
                "/docs",
                "/openapi.json",
                "/admin/login",
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
        """Validate the JWT bearer token on incoming Django requests.

        Skips authentication for paths listed in ``exempt_paths``.  On
        success, ``request.user`` is set to a :class:`~common.auth.token_user.TokenUser`
        built from the decoded JWT claims and ``None`` is returned so Django
        continues processing.  No User model query is performed.

        Args:
            request: Incoming Django HTTP request.

        Returns:
            ``None`` when authentication succeeds or the path is exempt;
            a 401 ``JsonResponse`` when authentication fails.
        """
        if any(request.path.startswith(path) for path in self.exempt_paths):
            return None

        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse(
                APIResponse(
                    message="Missing or invalid authorization header",
                    success=False,
                    status=401,
                ).model_dump(),
                status=401,
            )

        token = auth_header.split(" ")[1]

        from common.auth.jwt.handler import jwt_handler

        try:
            payload = jwt_handler.verify_token(token)
        except Exception as exc:
            return JsonResponse(
                APIResponse(message=str(exc), success=False, status=401).model_dump(),
                status=401,
            )

        request.user = TokenUser(payload)
        # Stash the raw bearer token so outbound ``ServiceDispatcher`` calls
        # (common/services/dispatch.py) can forward it verbatim for on-behalf-of
        # propagation. When no user token is in context, the dispatcher
        # falls back to a service token from ``ServiceTokenManager``.
        set_user_token(token)
        set_user_id(int(request.user.user_id) if request.user.user_id else None)
        raw_company_ids = request.headers.get("x-company-ids", "")
        if raw_company_ids:
            set_company_ids(
                [int(c.strip()) for c in raw_company_ids.split(",") if c.strip()]
            )
        return None


class FastAPIJWTMiddleware(BaseHTTPMiddleware):
    """Starlette middleware for JWT authentication in FastAPI applications.

    Intercepts incoming HTTP requests to validate the JWT bearer token in
    the ``Authorization`` header.  Requests to paths in ``exempt_paths``
    bypass authentication.  On success, ``request.state.user`` is set to a
    :class:`~common.auth.token_user.TokenUser` for downstream handlers.

    Attributes:
        exempt_paths: Set of URL paths that skip authentication.
    """

    def __init__(self, app, secret_key: str, algorithm: str = "RS256") -> None:
        """Initialise with JWT configuration and exempt-path set.

        Args:
            app: ASGI application wrapped by this middleware.
            secret_key: RSA public key PEM used to verify JWT signatures.
            algorithm: JWT signing algorithm — always ``"RS256"``.
        """
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithm = algorithm

        # Exempt paths
        self.exempt_paths = {
            "/api/v1/ping",
            "/api/v1/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        }

    async def dispatch(self, request: Request, call_next):
        """Intercept each request and enforce JWT authentication.

        Args:
            request: Incoming Starlette/FastAPI request.
            call_next: Next middleware or route handler in the ASGI stack.

        Returns:
            The downstream response, or a 401 ``APIResponse`` when
            authentication fails.
        """
        # Skip authentication for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Check for JWT token
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                content=APIResponse(
                    message="Missing or invalid authorization header",
                    success=False,
                    status=401,
                ).model_dump(),
                status_code=401,
            )

        token = auth_header.split(" ")[1]

        from common.auth.jwt.handler import jwt_handler

        try:
            payload = jwt_handler.verify_token(token)
            request.state.user = TokenUser(payload)
            # Stash the raw bearer token so outbound ``ServiceDispatcher``
            # calls (common/services/dispatch.py) can forward it verbatim for
            # on-behalf-of propagation. When no user token is in context,
            # the dispatcher falls back to a service token from
            # ``ServiceTokenManager``.
            set_user_token(token)
            set_user_id(
                int(request.state.user.user_id) if request.state.user.user_id else None
            )
            raw_company_ids = request.headers.get("x-company-ids", "")
            if raw_company_ids:
                set_company_ids(
                    [int(c.strip()) for c in raw_company_ids.split(",") if c.strip()]
                )
        except Exception as exc:
            return JSONResponse(
                content=APIResponse(
                    message=str(exc), success=False, status=401
                ).model_dump(),
                status_code=401,
            )

        return await call_next(request)
