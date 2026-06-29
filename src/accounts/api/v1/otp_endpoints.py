"""FastAPI endpoint handlers for OTP admin operations (v1).

Superuser-only create, read, and invalidation of OTP rows:

    POST   /otps            — create or reset an OTP for a phone
    GET    /otps            — paginated list of OTP rows
    GET    /otps/{otp_id}   — retrieve a single OTP row
    DELETE /otps/{otp_id}   — invalidate (delete) an OTP row

Resource path is plural kebab-case (``otps``). The login flow lives under
``/auth`` — these endpoints are for administration only.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from fastapi import APIRouter, Depends

from accounts.api.infrastructure.di_container import get_otp_controller
from accounts.api.presentation.controllers.otp_controller import OTPController
from accounts.api.presentation.schemas.otp_schemas import OTPRequestSchema
from common.api import BaseFilter
from common.api.response import APIResponse
from common.auth.jwt.token_user import TokenUser
from common.auth.permissions import require_superuser

router = APIRouter()


@router.post("/otps", response_model=APIResponse)
async def create_otp(
    payload: OTPRequestSchema,
    _caller: TokenUser = Depends(require_superuser),
    controller: OTPController = Depends(get_otp_controller),
) -> APIResponse:
    """Create or reset an OTP for the given phone (superuser only).

    Args:
        payload: Body with at least one of ``phone`` / ``email``.

    Returns:
        HTTP 201 ``APIResponse`` with the OTP row (including the code).
    """
    return APIResponse(
        data=await controller.create(payload),
        message=_("OTP created successfully"),
        status=201,
    )


@router.get("/otps", response_model=APIResponse)
async def list_otps(
    filter: BaseFilter = Depends(),
    _caller: TokenUser = Depends(require_superuser),
    controller: OTPController = Depends(get_otp_controller),
) -> APIResponse:
    """Return a paginated list of OTP rows (superuser only).

    Args:
        filter: Pagination (``limit``/``offset``) and sort parameters.

    Returns:
        HTTP 200 ``APIResponse`` with items and pagination ``meta``.
    """
    items, meta = await controller.list(filter=filter)
    return APIResponse(
        data=items,
        meta=meta,
        message=_("OTPs retrieved successfully"),
        status=200,
    )


@router.get("/otps/{otp_id}", response_model=APIResponse)
async def get_otp(
    otp_id: int,
    _caller: TokenUser = Depends(require_superuser),
    controller: OTPController = Depends(get_otp_controller),
) -> APIResponse:
    """Retrieve a single OTP row by primary key (superuser only).

    Args:
        otp_id: Primary key of the OTP row.

    Returns:
        HTTP 200 ``APIResponse`` with the OTP row.
    """
    return APIResponse(
        data=await controller.get(otp_id),
        message=_("OTP retrieved successfully"),
        status=200,
    )


@router.delete("/otps/{otp_id}", response_model=APIResponse)
async def delete_otp(
    otp_id: int,
    _caller: TokenUser = Depends(require_superuser),
    controller: OTPController = Depends(get_otp_controller),
) -> APIResponse:
    """Invalidate (delete) the OTP row by primary key (superuser only).

    Args:
        otp_id: Primary key of the OTP row to invalidate.

    Returns:
        HTTP 200 ``APIResponse`` confirming invalidation.
    """
    await controller.delete(otp_id)
    return APIResponse(
        message=_("OTP invalidated successfully"),
        status=200,
    )
