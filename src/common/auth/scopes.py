"""Token scope and role checking utilities for JWT-based authorisation.

Provides FastAPI dependencies that check ``roles`` and ``scopes`` claims
embedded in the JWT access token.  These work against the token payload
directly — no DB round-trip needed — making them suitable for both
rudra-service and downstream services (VMS, care-service) that verify
tokens via the JWKS endpoint.

Usage in rudra-service (alongside existing RBAC guards)::

    from common.auth.scopes import require_token_scopes, require_token_roles

    @router.get("/reports")
    async def get_reports(
        current_user=Depends(require_token_scopes("reports.view_report")),
    ): ...

Usage in downstream services (token-only, no Django ORM)::

    payload = jwt.decode(token, public_key, algorithms=["RS256"])
    if not has_scope(payload, "accounts.view_user"):
        raise HTTP 403

The ``require_roles`` / ``require_permissions`` dependencies in
``common.auth.permissions`` still work and check against the DB.
The token-based checks here are an **additional** option for cases
where a DB round-trip is undesirable (cross-service calls, API
gateways, etc.).
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from fastapi import Depends

from common.auth.dependencies import get_current_user
from common.exceptions.exceptions import PermissionDeniedError

INTEGRATION_INBOUND = "integration.inbound"


def has_scope(token_payload: dict, scope: str) -> bool:
    """Check if a decoded token payload contains a specific scope.

    Args:
        token_payload: Decoded JWT claims dict.
        scope: Permission string (``"app_label.codename"``).

    Returns:
        ``True`` if the scope is present or the user is a superuser.
    """
    if token_payload.get("is_superuser"):
        return True
    return scope in token_payload.get("scopes", [])


def has_any_scope(token_payload: dict, *scopes: str) -> bool:
    """Check if a decoded token payload contains any of the listed scopes.

    Args:
        token_payload: Decoded JWT claims dict.
        *scopes: One or more permission strings.

    Returns:
        ``True`` if at least one scope is present or the user is a superuser.
    """
    if token_payload.get("is_superuser"):
        return True
    token_scopes = set(token_payload.get("scopes", []))
    return bool(token_scopes.intersection(scopes))


def has_all_scopes(token_payload: dict, *scopes: str) -> bool:
    """Check if a decoded token payload contains all of the listed scopes.

    Args:
        token_payload: Decoded JWT claims dict.
        *scopes: One or more permission strings.

    Returns:
        ``True`` if all scopes are present or the user is a superuser.
    """
    if token_payload.get("is_superuser"):
        return True
    token_scopes = set(token_payload.get("scopes", []))
    return set(scopes).issubset(token_scopes)


def has_role(token_payload: dict, role: str) -> bool:
    """Check if a decoded token payload contains a specific role.

    Args:
        token_payload: Decoded JWT claims dict.
        role: Django group name.

    Returns:
        ``True`` if the role is present or the user is a superuser.
    """
    if token_payload.get("is_superuser"):
        return True
    return role in token_payload.get("roles", [])


def has_any_role(token_payload: dict, *roles: str) -> bool:
    """Check if a decoded token payload contains any of the listed roles.

    Args:
        token_payload: Decoded JWT claims dict.
        *roles: One or more Django group names.

    Returns:
        ``True`` if at least one role is present or the user is a superuser.
    """
    if token_payload.get("is_superuser"):
        return True
    token_roles = set(token_payload.get("roles", []))
    return bool(token_roles.intersection(roles))


def require_token_scopes(*scopes: str):
    """Return a FastAPI dependency that checks scopes in the JWT token.

    The user must hold **all** listed scopes in their token's ``scopes``
    claim.  Superusers bypass the check.

    Args:
        *scopes: One or more permission strings (``"app_label.codename"``).

    Returns:
        An async FastAPI dependency callable.
    """
    required = frozenset(scopes)

    async def _dependency(current_user=Depends(get_current_user)):
        """Enforce scope check using the current user's token claims.

        Args:
            current_user: Authenticated TokenUser injected by ``get_current_user``.

        Returns:
            The authenticated TokenUser if all scopes are present.

        Raises:
            PermissionDeniedError: If any required scope is missing.
        """
        if current_user.is_superuser:
            return current_user

        missing = required - set(current_user.scopes)
        if missing:
            raise PermissionDeniedError(
                str(
                    _("Insufficient permissions. Missing scopes: %(scopes)s.")
                    % {"scopes": ", ".join(sorted(missing))}
                )
            )
        return current_user

    return _dependency


def require_token_roles(*roles: str):
    """Return a FastAPI dependency that checks roles in the JWT token.

    The user must belong to **at least one** of the listed roles.
    Superusers bypass the check.  This is similar to ``require_roles``
    in ``permissions.py`` but is named for token-centric usage.

    Args:
        *roles: One or more Django group names.

    Returns:
        An async FastAPI dependency callable.
    """
    allowed = frozenset(roles)

    async def _dependency(current_user=Depends(get_current_user)):
        """Enforce role check using the current user's group memberships.

        Args:
            current_user: Authenticated ``User`` injected by ``get_current_user``.

        Returns:
            The authenticated ``User`` if at least one role matches.

        Raises:
            PermissionDeniedError: If the user has none of the required roles.
        """
        if current_user.is_superuser:
            return current_user

        if not set(current_user.roles).intersection(allowed):
            raise PermissionDeniedError(
                str(
                    _("Insufficient permissions. Required role: %(roles)s.")
                    % {"roles": ", ".join(sorted(allowed))}
                )
            )
        return current_user

    return _dependency
