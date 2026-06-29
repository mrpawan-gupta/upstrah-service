"""FastAPI route handlers for the Membership resource (v1).

    POST /academies/{academy_id}/memberships  — apply (status=pending)
    GET  /academies/{academy_id}/memberships  — paginated list
    POST /memberships/{id}/approve            — approve (status=approved)
    POST /memberships/{id}/reject             — reject (status=rejected)

Resource path is plural kebab-case (``memberships``). Every endpoint wraps
its result in :class:`APIResponse`; messages use ``gettext_lazy``. The
authenticated caller is required via ``require_user``.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from fastapi import APIRouter, Depends, Path, Query

from academies.api.infrastructure.di_container import get_membership_controller
from academies.api.presentation.controllers.membership_controller import (
    MembershipController,
)
from academies.api.presentation.schemas.membership_schemas import (
    MembershipCreateSchema,
)
from common.api.response import APIResponse
from common.auth.dependencies import require_user
from common.auth.jwt.token_user import TokenUser

router = APIRouter()


@router.post(
    "/academies/{academy_id}/memberships",
    response_model=APIResponse,
    status_code=201,
)
async def apply_membership(
    payload: MembershipCreateSchema,
    academy_id: int = Path(..., description="Primary key of the academy."),
    caller: TokenUser = Depends(require_user),
    controller: MembershipController = Depends(get_membership_controller),
) -> APIResponse:
    """Apply for membership of an academy (status set to ``pending``).

    Args:
        academy_id: Primary key of the academy to apply to.
        payload:    Requested role.

    Returns:
        HTTP 201 ``APIResponse`` with the created (pending) membership.
    """
    return APIResponse(
        data=await controller.apply(
            payload, user_id=int(caller.user_id), academy_id=academy_id
        ),
        message=_("Membership application submitted successfully"),
        status=201,
    )


@router.get(
    "/academies/{academy_id}/memberships",
    response_model=APIResponse,
)
async def list_memberships(
    academy_id: int = Path(..., description="Primary key of the academy."),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    _caller: TokenUser = Depends(require_user),
    controller: MembershipController = Depends(get_membership_controller),
) -> APIResponse:
    """Return a paginated list of an academy's memberships.

    Args:
        academy_id: Primary key of the academy.
        offset:     Pagination offset.
        limit:      Items per page (1–100).

    Returns:
        HTTP 200 ``APIResponse`` with items and pagination ``meta``.
    """
    items, meta = await controller.list_for_academy(
        academy_id, offset=offset, limit=limit
    )
    return APIResponse(
        data=items,
        meta=meta,
        message=_("Memberships retrieved successfully"),
        status=200,
    )


@router.post("/memberships/{membership_id}/approve", response_model=APIResponse)
async def approve_membership(
    membership_id: int = Path(..., description="Primary key of the membership."),
    _caller: TokenUser = Depends(require_user),
    controller: MembershipController = Depends(get_membership_controller),
) -> APIResponse:
    """Approve a membership application (status → ``approved``).

    Args:
        membership_id: Primary key of the membership row.

    Returns:
        HTTP 200 ``APIResponse`` with the approved membership.
    """
    return APIResponse(
        data=await controller.approve(membership_id),
        message=_("Membership {id_} approved successfully").format(id_=membership_id),
        status=200,
    )


@router.post("/memberships/{membership_id}/reject", response_model=APIResponse)
async def reject_membership(
    membership_id: int = Path(..., description="Primary key of the membership."),
    _caller: TokenUser = Depends(require_user),
    controller: MembershipController = Depends(get_membership_controller),
) -> APIResponse:
    """Reject a membership application (status → ``rejected``).

    Args:
        membership_id: Primary key of the membership row.

    Returns:
        HTTP 200 ``APIResponse`` with the rejected membership.
    """
    return APIResponse(
        data=await controller.reject(membership_id),
        message=_("Membership {id_} rejected successfully").format(id_=membership_id),
        status=200,
    )
