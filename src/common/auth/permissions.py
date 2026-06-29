from django.utils.translation import gettext_lazy as _
from fastapi import Depends

from common.auth.jwt.token_user import TokenUser
from common.exceptions.exceptions import PermissionDeniedError

from .dependencies import get_current_user


async def require_superuser(current_user: TokenUser = Depends(get_current_user)):
    """Dependency that allows only superusers.

    Args:
        current_user: Authenticated TokenUser injected by ``get_current_user``.

    Returns:
        The authenticated TokenUser if ``is_superuser`` is ``True``.

    Raises:
        PermissionDeniedError: If the user is not a superuser.
    """
    if not current_user.is_superuser:
        raise PermissionDeniedError(str(_("Superuser access required.")))
    return current_user


async def require_staff_or_superuser(
    current_user: TokenUser = Depends(get_current_user),
):
    """Dependency that allows only staff members or superusers.

    Args:
        current_user: Authenticated TokenUser injected by ``get_current_user``.

    Returns:
        The authenticated TokenUser if ``is_staff`` or ``is_superuser`` is
        ``True``.

    Raises:
        PermissionDeniedError: If the user is neither staff nor a superuser.
    """
    if not (current_user.is_staff or current_user.is_superuser):
        raise PermissionDeniedError(str(_("Staff or superuser access required.")))
    return current_user


def require_roles(*group_names: str):
    """Return a FastAPI dependency that enforces group (role) membership.

    The user must belong to **at least one** of the named Django groups.
    Superusers bypass the check entirely.  Role membership is read from the
    ``roles`` claim embedded in the JWT by rudra-service — no database query
    is performed.

    Args:
        *group_names: One or more Django ``Group.name`` strings.

    Returns:
        An async FastAPI dependency callable.

    Example::

        @router.delete("/companies/{id}")
        async def delete_company(
            current_user=Depends(require_roles("Platform Admin")),
            ...
        ): ...
    """
    allowed: frozenset[str] = frozenset(group_names)

    async def _dependency(current_user: TokenUser = Depends(get_current_user)):
        """Enforce role membership for the current request.

        Args:
            current_user: Authenticated TokenUser injected by ``get_current_user``.

        Returns:
            The authenticated TokenUser if the role check passes.

        Raises:
            PermissionDeniedError: If the user is not in any of the allowed groups.
        """
        if current_user.is_superuser:
            return current_user

        user_roles = set(current_user.roles)
        if not user_roles.intersection(allowed):
            raise PermissionDeniedError(
                str(
                    _(
                        "You do not have permission to perform this action. "
                        "Required role: %(roles)s."
                    )
                    % {"roles": ", ".join(sorted(allowed))}
                )
            )
        return current_user

    return _dependency


def require_permissions(*perms: str):
    """Return a FastAPI dependency that enforces permission checks.

    The user must hold **all** listed permissions (``"app_label.codename"``).
    Superusers bypass the check entirely.  Permission data is read from the
    ``scopes`` claim embedded in the JWT by rudra-service — no database query
    is performed.

    Args:
        *perms: One or more permission strings in ``"app_label.codename"`` form.

    Returns:
        An async FastAPI dependency callable.

    Example::

        @router.post("/companies/{id}/users")
        async def add_company_user(
            current_user=Depends(require_permissions("companies.manage_company_users")),
            ...
        ): ...
    """
    required: frozenset[str] = frozenset(perms)

    async def _dependency(current_user: TokenUser = Depends(get_current_user)):
        """Enforce permission checks for the current request.

        Args:
            current_user: Authenticated TokenUser injected by ``get_current_user``.

        Returns:
            The authenticated TokenUser if all permission checks pass.

        Raises:
            PermissionDeniedError: If the user lacks any of the required permissions.
        """
        if current_user.is_superuser:
            return current_user

        user_scopes = set(current_user.scopes)
        missing = required - user_scopes
        if missing:
            raise PermissionDeniedError(
                str(
                    _(
                        "You do not have permission to perform this action. "
                        "Missing permission: %(perm)s."
                    )
                    % {"perm": ", ".join(sorted(missing))}
                )
            )
        return current_user

    return _dependency
