"""FastAPI route handlers for the 1:1 UserProfile (onboarding) endpoints (v1).

    GET   /users/{user_id}/profile  — read a user's onboarding profile
    PATCH /users/{user_id}/profile  — update sex/dob/role/sub_role/notif prefs

Non-superusers may only read or modify their own profile; a mismatch
raises :class:`PermissionDeniedError`. The ``UserProfile`` row is created
lazily on first read/write.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from fastapi import APIRouter, Body, Depends, Path

from accounts.api.infrastructure.di_container import get_user_profile_controller
from accounts.api.presentation.controllers.user_profile_controller import (
    UserProfileController,
)
from accounts.api.presentation.schemas.user_profile_schemas import (
    UserProfilePatchSchema,
)
from common.api.response import APIResponse
from common.auth.dependencies import get_current_user
from common.auth.jwt.token_user import TokenUser
from common.exceptions.exceptions import PermissionDeniedError

router = APIRouter(tags=["user-profiles"])


def _assert_can_access(caller: TokenUser, user_id: int) -> None:
    """Reject access when a non-superuser targets another user's profile.

    Args:
        caller:  Authenticated principal.
        user_id: Target profile owner's PK.

    Raises:
        PermissionDeniedError: Caller is neither the owner nor a superuser.
    """
    if not caller.is_superuser and str(caller.user_id) != str(user_id):
        raise PermissionDeniedError(
            str(_("You may only access your own profile."))
        )


@router.get("/users/{user_id}/profile", response_model=APIResponse)
async def get_user_profile(
    user_id: int = Path(..., description="PK of the profile owner."),
    caller: TokenUser = Depends(get_current_user),
    controller: UserProfileController = Depends(get_user_profile_controller),
) -> APIResponse:
    """Return the onboarding profile for ``user_id``.

    Args:
        user_id: PK of the profile owner.

    Returns:
        HTTP 200 ``APIResponse`` with the user + profile payload.
    """
    _assert_can_access(caller, user_id)
    return APIResponse(
        data=await controller.get(user_id),
        message=_("Profile retrieved successfully"),
        status=200,
    )


@router.patch("/users/{user_id}/profile", response_model=APIResponse)
async def patch_user_profile(
    user_id: int = Path(..., description="PK of the profile owner."),
    payload: UserProfilePatchSchema = Body(...),
    caller: TokenUser = Depends(get_current_user),
    controller: UserProfileController = Depends(get_user_profile_controller),
) -> APIResponse:
    """Update the onboarding profile for ``user_id`` (unset fields unchanged).

    Args:
        user_id: PK of the profile owner.
        payload: PATCH body; at least one field must be provided.

    Returns:
        HTTP 200 ``APIResponse`` with the updated user + profile payload.
    """
    _assert_can_access(caller, user_id)
    return APIResponse(
        data=await controller.partial_update(user_id, payload),
        message=_("Profile updated successfully"),
        status=200,
    )
