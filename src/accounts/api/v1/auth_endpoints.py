"""FastAPI endpoint handlers for the auth (phone-OTP) resource (v1).

The phone → OTP → JWT login surface:

    POST /auth/otp/send    — send an OTP to a phone number
    POST /auth/otp/verify  — verify an OTP → JWT access + refresh pair
    POST /auth/refresh     — exchange a refresh token for a new access token
    POST /auth/logout      — revoke an access + refresh token pair
    GET  /auth/me          — return the authenticated caller's profile

Each handler injects the controller via ``Depends(get_auth_controller)``,
calls exactly one controller method, and wraps the result in
``APIResponse`` (added here, never in the controller). All user-facing
messages use ``gettext_lazy``.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from fastapi import APIRouter, Depends

from accounts.api.infrastructure.di_container import get_auth_controller
from accounts.api.presentation.controllers.auth_controller import AuthController
from accounts.api.presentation.schemas.auth_schemas import (
    LogoutRequest,
    OTPSendRequest,
    OTPVerifyRequest,
    RefreshRequest,
)
from common.api.response import APIResponse
from common.auth.dependencies import get_current_user
from common.auth.jwt.token_user import TokenUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/otp/send", response_model=APIResponse)
async def send_otp(
    payload: OTPSendRequest,
    controller: AuthController = Depends(get_auth_controller),
) -> APIResponse:
    """Send an OTP to the given phone number.

    Args:
        payload: Body with the ``phone`` number in E.164 format.

    Returns:
        HTTP 200 ``APIResponse`` with ``message`` and ``expires_in``.
    """
    return APIResponse(
        data=await controller.send_otp(payload),
        message=_("OTP sent successfully"),
        status=200,
    )


@router.post("/otp/verify", response_model=APIResponse)
async def verify_otp(
    payload: OTPVerifyRequest,
    controller: AuthController = Depends(get_auth_controller),
) -> APIResponse:
    """Verify an OTP code and issue a JWT access + refresh token pair.

    Args:
        payload: Body with ``phone`` and the numeric ``code``.

    Returns:
        HTTP 200 ``APIResponse`` with the token pair.
    """
    return APIResponse(
        data=await controller.verify_otp(payload),
        message=_("OTP verified successfully"),
        status=200,
    )


@router.post("/refresh", response_model=APIResponse)
async def refresh_token(
    payload: RefreshRequest,
    controller: AuthController = Depends(get_auth_controller),
) -> APIResponse:
    """Exchange a refresh token for a new access token (rotates the refresh).

    Args:
        payload: Body with the current ``refresh_token``.

    Returns:
        HTTP 200 ``APIResponse`` with a new token pair.
    """
    return APIResponse(
        data=await controller.refresh(payload),
        message=_("Token refreshed successfully"),
        status=200,
    )


@router.post("/logout", response_model=APIResponse)
async def logout(
    payload: LogoutRequest,
    _caller: TokenUser = Depends(get_current_user),
    controller: AuthController = Depends(get_auth_controller),
) -> APIResponse:
    """Revoke the provided access and refresh tokens (requires a valid token).

    Args:
        payload: Body with ``access_token`` and ``refresh_token`` to revoke.

    Returns:
        HTTP 200 ``APIResponse`` confirming logout.
    """
    return APIResponse(
        data=await controller.logout(payload),
        message=_("Logged out successfully"),
        status=200,
    )


@router.get("/me", response_model=APIResponse)
async def get_me(
    caller: TokenUser = Depends(get_current_user),
    controller: AuthController = Depends(get_auth_controller),
) -> APIResponse:
    """Return the authenticated caller's onboarding profile.

    Args:
        caller: Authenticated principal resolved from the bearer token.

    Returns:
        HTTP 200 ``APIResponse`` with the caller's user + profile payload.
    """
    return APIResponse(
        data=await controller.me(int(caller.user_id)),
        message=_("Current user retrieved successfully"),
        status=200,
    )
