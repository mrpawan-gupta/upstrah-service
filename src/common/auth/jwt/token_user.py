"""Stateless token-backed user object for cross-service JWT authentication.

Provides :class:`TokenUser`, a lightweight user representation backed by a
validated JWT payload rather than a database row.  Modeled after
``django.contrib.auth.models.AnonymousUser`` and SimpleJWT's ``TokenUser``
so that downstream Django views, admin checks, and FastAPI route handlers
can access identity claims via typed attributes instead of raw ``dict``
look-ups — with zero database round-trips.

Classes:
    TokenUser: Stateless user object constructed from a decoded JWT payload.
"""

from functools import cached_property


class TokenUser:
    """Stateless user object backed by a validated JWT payload.

    Modeled after ``django.contrib.auth.models.AnonymousUser`` and
    SimpleJWT's ``TokenUser``.  Both :class:`~common.middleware.auth.JWTAuthenticationMiddleware`
    (Django) and :class:`~common.middleware.auth.FastAPIJWTMiddleware`
    (FastAPI) set this as the request's user object so that all downstream
    code can use attribute access regardless of framework.

    No database query is ever performed — this is safe to use in any
    microservice that does not own the ``User`` table.

    Attributes:
        is_active: Always ``True``; an invalid token is rejected before this
            object is constructed.
    """

    is_active = True

    def __init__(self, payload: dict) -> None:
        """Initialize from a decoded and validated JWT payload.

        Args:
            payload: Decoded JWT claims dict returned by
                ``jwt_handler.verify_token()``.
        """
        self._payload = payload

    @cached_property
    def token_type(self) -> str:
        """Which issuer flow produced the token.

        One of ``"access"`` (user login), ``"refresh"``,
        ``"service"`` (internal service-to-service), or ``"partner"``
        (external partner integration). Downstream dependencies use this
        to narrow which flows an endpoint accepts.
        """
        return self._payload.get("token_type", "access")

    @cached_property
    def client_id(self) -> str:
        """Caller's OAuth2 client_id, or ``""`` for user access tokens."""
        return self._payload.get("client_id", "")

    @cached_property
    def company_id(self) -> int | None:
        """Partner token's ``company_id`` claim, or ``None`` for other tokens.

        The partner's ``Company.id`` is baked into the token at issuance
        time; downstream services use it without any DB lookup.
        """
        value = self._payload.get("company_id")
        return int(value) if value is not None else None

    @cached_property
    def on_behalf_of(self) -> str:
        """Rudra ``User.id`` a partner token is acting for (``""`` if absent).

        Present only on partner tokens that were issued with an
        ``on_behalf_of`` parameter at the ``/oauth/token`` endpoint.
        """
        value = self._payload.get("on_behalf_of", "")
        return str(value) if value else ""

    @cached_property
    def acting_as(self) -> dict | None:
        """RFC 8693 ``act`` claim (``{"sub": <client_id>}``), or ``None``.

        Set alongside ``on_behalf_of`` to make it unambiguous that the
        acting principal is the partner client, not the OBO user. Useful
        for audit trails.
        """
        return self._payload.get("act")

    @property
    def is_user(self) -> bool:
        """``True`` when this token was issued by a user login flow."""
        return self.token_type == "access"

    @property
    def is_service(self) -> bool:
        """``True`` when this is an internal service-to-service token."""
        return self.token_type == "service"

    @property
    def is_partner(self) -> bool:
        """``True`` when this is an external partner token."""
        return self.token_type == "partner"

    @cached_property
    def user_id(self) -> str:
        """Primary user identifier.

        For user access tokens this is the ``user_id`` claim directly.
        For partner tokens that carry an ``on_behalf_of`` claim the
        method returns the OBO user id, so downstream code that reads
        ``current_user.user_id`` treats a partner-acting-for-user flow
        identically to a direct user login — scoped, of course, to the
        partner's company.
        """
        raw = self._payload.get("user_id")
        if raw:
            return str(raw)
        if self.on_behalf_of:
            return self.on_behalf_of
        return ""

    @cached_property
    def pk(self) -> str:
        """Alias for :attr:`user_id` — Django ORM compatibility."""
        return self.user_id

    @cached_property
    def id(self) -> str:
        """Alias for :attr:`user_id` — Django ORM compatibility."""
        return self.user_id

    @cached_property
    def jti(self) -> str:
        """JWT token ID (``jti`` claim) used for per-token revocation."""
        return self._payload.get("jti", "")

    @cached_property
    def ver(self) -> int:
        """Token-version claim used for per-user invalidation (``0`` if absent).

        Compared against the user's current version (see
        :mod:`common.auth.token_version`) at the auth gate: a token whose
        ``ver`` is below the current value is rejected, forcing a refresh.
        """
        return int(self._payload.get("ver", 0))

    @cached_property
    def is_superuser(self) -> bool:
        """``True`` when the token carries the superuser flag."""
        return bool(self._payload.get("is_superuser", False))

    @cached_property
    def is_staff(self) -> bool:
        """``True`` when the token carries the staff flag."""
        return bool(self._payload.get("is_staff", False))

    @cached_property
    def roles(self) -> list[str]:
        """List of role names from the ``roles`` JWT claim."""
        return self._payload.get("roles", [])

    @cached_property
    def scopes(self) -> list[str]:
        """List of permission strings from the ``scopes`` JWT claim."""
        return self._payload.get("scopes", [])

    @cached_property
    def companies(self) -> list[dict]:
        """List of company memberships from the ``companies`` JWT claim.

        Each entry is a dict with keys:
        - ``id`` (int): Company primary key.
        - ``is_default`` (bool): Whether this is the user's default company.
        - ``is_active`` (bool): Whether the membership is active.
        """
        return self._payload.get("companies", [])

    @property
    def is_anonymous(self) -> bool:
        """Always ``False`` — a ``TokenUser`` represents an authenticated caller."""
        return False

    @property
    def is_authenticated(self) -> bool:
        """Always ``True`` — the token was verified before construction."""
        return True

    def get_username(self) -> str:
        """Return the user identifier as a string.

        Returns:
            String representation of :attr:`user_id`.
        """
        return str(self.user_id)

    @property
    def groups(self):
        """Empty manager — token users have no DB group memberships.

        Returns ``EmptyManager(Group)`` when ``django.contrib.auth`` is
        installed (rudra-service, care-service) or a plain empty list when
        it is not (vms, kriya-service). The import is deferred to avoid
        triggering the Django app registry before ``django.setup()``
        completes.
        """
        try:
            from django.contrib.auth import models as auth_models
            from django.db.models.manager import EmptyManager

            return EmptyManager(auth_models.Group)
        except (ImportError, RuntimeError):
            return []

    @property
    def user_permissions(self):
        """Empty manager — token users have no DB permission records.

        Same deferred-import and fallback strategy as :attr:`groups`.
        """
        try:
            from django.contrib.auth import models as auth_models
            from django.db.models.manager import EmptyManager

            return EmptyManager(auth_models.Permission)
        except (ImportError, RuntimeError):
            return []

    def get_group_permissions(self, obj: object = None) -> set[str]:
        """Return an empty set — token users carry no group-sourced permissions.

        Args:
            obj: Ignored.

        Returns:
            Always an empty set.
        """
        return set()

    def get_all_permissions(self, obj: object = None) -> set[str]:
        """Return all permissions carried by the token.

        Args:
            obj: Ignored — token-level permissions are not object-scoped.

        Returns:
            Set of permission strings from :attr:`scopes`.
        """
        return set(self.scopes)

    async def aget_all_permissions(self, obj: object = None) -> set[str]:
        """Async variant of :meth:`get_all_permissions`.

        Args:
            obj: Ignored.

        Returns:
            Set of permission strings from :attr:`scopes`.
        """
        return self.get_all_permissions(obj)

    def has_perm(self, perm: str, obj: object = None) -> bool:
        """Check whether the token carries a specific permission.

        Args:
            perm: Django-style permission string (e.g. ``"accounts.view_user"``).
            obj: Ignored.

        Returns:
            ``True`` if ``perm`` is in :attr:`scopes`.
        """
        return perm in self.scopes

    async def ahas_perm(self, perm: str, obj: object = None) -> bool:
        """Async variant of :meth:`has_perm`.

        Args:
            perm: Django-style permission string.
            obj: Ignored.

        Returns:
            ``True`` if ``perm`` is in :attr:`scopes`.
        """
        return self.has_perm(perm, obj)

    def has_perms(self, perm_list: list[str], obj: object = None) -> bool:
        """Check whether the token carries all of the given permissions.

        Args:
            perm_list: Iterable of permission strings.
            obj: Ignored.

        Returns:
            ``True`` only if every entry in ``perm_list`` is in :attr:`scopes`.
        """
        return all(p in self.scopes for p in perm_list)

    async def ahas_perms(self, perm_list: list[str], obj: object = None) -> bool:
        """Async variant of :meth:`has_perms`.

        Args:
            perm_list: Iterable of permission strings.
            obj: Ignored.

        Returns:
            ``True`` only if every entry in ``perm_list`` is in :attr:`scopes`.
        """
        return self.has_perms(perm_list, obj)

    def has_module_perms(self, app_label: str) -> bool:
        """Always returns ``False`` — module-level permissions require a DB.

        Args:
            app_label: Django app label.

        Returns:
            Always ``False``.
        """
        return False

    async def ahas_module_perms(self, app_label: str) -> bool:
        """Async variant of :meth:`has_module_perms`.

        Args:
            app_label: Django app label.

        Returns:
            Always ``False``.
        """
        return False

    def has_role(self, role: str) -> bool:
        """Check whether the token carries a specific role.

        Args:
            role: Role name to check (e.g. ``"Platform Admin"``).

        Returns:
            ``True`` if ``role`` is in :attr:`roles`.
        """
        return role in self.roles

    async def ahas_role(self, role: str) -> bool:
        """Async variant of :meth:`has_role`.

        Args:
            role: Role name to check.

        Returns:
            ``True`` if ``role`` is in :attr:`roles`.
        """
        return self.has_role(role)

    def has_scope(self, scope: str) -> bool:
        """Check whether the token carries a specific scope/permission.

        Args:
            scope: Permission string to check.

        Returns:
            ``True`` if ``scope`` is in :attr:`scopes`.
        """
        return scope in self.scopes

    async def ahas_scope(self, scope: str) -> bool:
        """Async variant of :meth:`has_scope`.

        Args:
            scope: Permission string to check.

        Returns:
            ``True`` if ``scope`` is in :attr:`scopes`.
        """
        return self.has_scope(scope)

    def save(self) -> None:
        """Raise ``NotImplementedError`` — token users have no DB row."""
        raise NotImplementedError("TokenUser has no database representation")

    def delete(self) -> None:
        """Raise ``NotImplementedError`` — token users have no DB row."""
        raise NotImplementedError("TokenUser has no database representation")

    def set_password(self, raw_password: str) -> None:
        """Raise ``NotImplementedError`` — token users have no DB row."""
        raise NotImplementedError("TokenUser has no database representation")

    def check_password(self, raw_password: str) -> bool:
        """Raise ``NotImplementedError`` — token users have no DB row."""
        raise NotImplementedError("TokenUser has no database representation")

    def __str__(self) -> str:
        return f"TokenUser {self.user_id}"

    def __repr__(self) -> str:
        return f"TokenUser(user_id={self.user_id!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TokenUser):
            return self.user_id == other.user_id
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.user_id)

    def __getattr__(self, attr: str) -> object:
        """Fallback attribute access for arbitrary JWT claims.

        Called only when normal attribute lookup fails.  Allows endpoint
        code to read custom claims (e.g. ``current_user.tenant_id``) without
        explicit properties on this class.

        Args:
            attr: Attribute name to look up in the JWT payload.

        Returns:
            The claim value from the payload, or ``None`` if absent.
        """
        return self._payload.get(attr, None)
