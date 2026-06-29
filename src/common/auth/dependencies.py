"""FastAPI dependencies for JWT-based authentication and authorization.

Provides the full ladder of principal-resolution dependencies:

* :func:`get_current_principal` — accepts any valid token type and returns
  the :class:`TokenUser`. Use when an endpoint is happy with a user,
  service, or partner caller.
* :func:`get_current_user` — backwards-compatible shim that still accepts
  only user access tokens. Kept for existing call sites.
* :func:`require_user` — explicit name for user-only endpoints (alias of
  :func:`get_current_user`).
* :func:`require_service_or_user` — user access tokens OR service tokens.
* :func:`require_partner_or_user` — user access tokens OR partner tokens.
* :func:`require_any_authenticated` — alias of :func:`get_current_principal`.
* :func:`require_scope` — dependency factory that rejects tokens missing
  a specific OAuth2 scope (supports fnmatch wildcards on the token side).

Company resolution (:func:`get_company_ids`) gains a partner-token fallback:
when the header is absent and the token carries ``company_id``, that claim
is used; superusers still get ``[]`` when no context is provided.
"""

from __future__ import annotations

import fnmatch

import jwt
from django.utils.translation import gettext_lazy as _
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from common.auth.jwt.token_user import TokenUser
from common.auth.token_version import token_version_service
from common.exceptions.exceptions import AuthenticationError, PermissionDeniedError

from .jwt import jwt_handler

# Security scheme for bearer token
security = HTTPBearer(auto_error=False)


def _raise_auth(message: str) -> None:
    """Tiny helper to keep auth-error raises inline-friendly."""
    raise AuthenticationError(message)


async def _decode_bearer(
    credentials: HTTPAuthorizationCredentials | None,
) -> dict:
    """Extract and verify a bearer token, returning the decoded payload.

    Args:
        credentials: HTTP bearer credentials from ``HTTPBearer``.

    Returns:
        Decoded JWT payload dict.

    Raises:
        AuthenticationError: Missing, malformed, or invalid token.
    """
    if not credentials:
        _raise_auth(str(_("Authentication token required")))

    token = (
        credentials.credentials
        if credentials and hasattr(credentials, "credentials")
        else None
    )
    if not token:
        _raise_auth(str(_("Authentication token required")))

    try:
        return jwt_handler.verify_token(str(token))
    except AuthenticationError:
        raise
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError(str(_("Token has expired"))) from exc
    except jwt.DecodeError as exc:
        raise AuthenticationError(str(_("Malformed authentication token"))) from exc
    except jwt.InvalidTokenError as exc:
        msg = str(exc) if str(exc) else str(_("Invalid authentication token"))
        raise AuthenticationError(msg) from exc
    except Exception as exc:
        raise AuthenticationError(str(_("Authentication failed"))) from exc


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TokenUser:
    """Return the :class:`TokenUser` for any valid token type.

    Accepts user access tokens, service tokens, and partner tokens.
    Endpoints that need to narrow which flows are allowed should use one
    of the ``require_*`` helpers instead.

    Args:
        credentials: HTTP bearer credentials.

    Returns:
        :class:`TokenUser` wrapping the verified JWT payload.

    Raises:
        AuthenticationError: Missing, malformed, or invalid token.
    """
    payload = await _decode_bearer(credentials)
    return TokenUser(payload)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TokenUser:
    """Return the authenticated user for an **access** token.

    Kept as the default identity dependency used across existing
    endpoints. Rejects service and partner tokens — those endpoints
    should opt into :func:`require_service_or_user` or
    :func:`require_partner_or_user` explicitly.

    Args:
        credentials: HTTP bearer credentials.

    Returns:
        :class:`TokenUser` with a populated ``user_id``.

    Raises:
        AuthenticationError: Token is missing, invalid, not an access
            token, or lacks a ``user_id`` claim.
    """
    user = await get_current_principal(credentials)
    if not user.is_user:
        _raise_auth(str(_("Access token required")))
    if not user.user_id:
        _raise_auth(str(_("Invalid authentication token")))
    if await token_version_service.aget(user.user_id) > user.ver:
        _raise_auth(str(_("Session expired, please re-authenticate")))
    return user


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TokenUser:
    """Alias of :func:`get_current_user` with an explicit name."""
    return await get_current_user(credentials)


async def require_service_or_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TokenUser:
    """Accept user access tokens and service tokens; reject partner tokens.

    Used by internal endpoints that receive either a forwarded user
    bearer token (for on-behalf-of propagation) or a service-to-service
    token issued via ``client_credentials``.

    Raises:
        AuthenticationError: Token is a partner token or invalid.
    """
    user = await get_current_principal(credentials)
    if user.is_partner:
        _raise_auth(str(_("Partner tokens are not accepted on this endpoint")))
    return user


async def require_partner_or_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TokenUser:
    """Accept user access tokens and partner tokens; reject service tokens.

    Used by public-facing endpoints that accept either a logged-in user
    OR a partner backend (optionally on-behalf-of one of its users).

    Raises:
        AuthenticationError: Token is a service token or invalid.
    """
    user = await get_current_principal(credentials)
    if user.is_service:
        _raise_auth(str(_("Service tokens are not accepted on this endpoint")))
    return user


async def require_any_authenticated(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TokenUser:
    """Alias of :func:`get_current_principal`.

    Use when an endpoint wants to document that *any* authenticated
    caller is accepted, rather than relying on the implicit semantics
    of ``get_current_principal``.
    """
    return await get_current_principal(credentials)


def require_scope(scope: str):
    """Dependency factory that rejects tokens missing a specific scope.

    The token's ``scopes`` claim may contain fnmatch-style wildcards
    (e.g. ``"internal:*"``); a single wildcard grant covers all matching
    concrete scopes. Use this alongside :func:`require_partner_or_user`
    (or similar) so the endpoint carries two deps: one for who may call,
    one for what they may do.

    Args:
        scope: The required scope (e.g. ``"policy:issue"``).

    Returns:
        A FastAPI dependency coroutine that returns the authenticated
        :class:`TokenUser` when the scope is present, or raises
        :class:`PermissionDeniedError` when it is not.
    """

    async def _dep(
        user: TokenUser = Depends(get_current_principal),
    ) -> TokenUser:
        for granted in user.scopes:
            if granted == scope or fnmatch.fnmatchcase(scope, granted):
                return user
        raise PermissionDeniedError(
            str(_("Missing required scope: {scope}")).format(scope=scope)
        )

    return _dep


async def get_company_ids(
    current_user: TokenUser = Depends(get_current_principal),
    x_company_ids: str | None = Header(default=None, alias="X-Company-IDs"),
) -> list[int]:
    """Resolve effective company IDs with a documented precedence.

    Resolution order:

    1. **Explicit header** — if ``X-Company-IDs`` is present, parse and
       return it. No membership check is performed; the header is
       trusted as-is.
    2. **Partner token** — when the caller is a partner, the token
       carries its ``company_id`` claim; return a single-element list.
       Partners cannot act outside their own company.
    3. **Superuser** — returns ``[]`` so the endpoint treats it as
       "all companies" (preserves the existing contract).
    4. **User token default membership** — returns a single-element
       list when the token has exactly one ``is_default=True`` company.
    5. **Error** — raise :class:`PermissionDeniedError`.

    Args:
        current_user: Authenticated principal.
        x_company_ids: Raw header value.

    Returns:
        List of integer company PKs, or ``[]`` for a superuser with no
        explicit context.

    Raises:
        PermissionDeniedError: Header malformed, or no fallback applies.
    """
    if x_company_ids is not None:
        try:
            ids = [int(s.strip()) for s in x_company_ids.split(",") if s.strip()]
        except ValueError as exc:
            raise PermissionDeniedError(
                str(_("X-Company-IDs must be a comma-separated list of integers."))
            ) from exc
        if not ids:
            raise PermissionDeniedError(
                str(_("X-Company-IDs header must contain at least one ID."))
            )
        return ids

    # 2. Partner token: company is baked into the token claim.
    if current_user.is_partner and current_user.company_id is not None:
        return [current_user.company_id]

    # 3. Superuser fallback — preserves the "[] = all" contract.
    if current_user.is_superuser:
        return []

    # 4. User access token with a single default-company membership.
    if current_user.is_user:
        defaults = [
            int(c["id"])
            for c in current_user.companies
            if isinstance(c, dict) and c.get("is_default") and c.get("is_active")
        ]
        if len(defaults) == 1:
            return defaults

    raise PermissionDeniedError(str(_("X-Company-IDs header is required.")))
