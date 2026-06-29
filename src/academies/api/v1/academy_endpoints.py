"""FastAPI route handlers for the Academy resource (v1).

    POST   /academies        — create an academy (owned by the caller)
    GET    /academies        — paginated list of academies
    GET    /academies/{id}    — retrieve a single academy
    PUT    /academies/{id}    — full replace
    PATCH  /academies/{id}    — partial update
    DELETE /academies/{id}    — delete

Resource path is plural kebab-case (``academies``). Every endpoint wraps
its result in :class:`APIResponse`; messages use ``gettext_lazy``. The
authenticated caller is required via ``require_user``.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from fastapi import APIRouter, Depends, Path, Query

from academies.api.infrastructure.di_container import get_academy_controller
from academies.api.presentation.controllers.academy_controller import (
    AcademyController,
)
from academies.api.presentation.schemas.academy_schemas import (
    AcademyCreateSchema,
    AcademyPatchSchema,
    AcademyUpdateSchema,
)
from common.api.response import APIResponse
from common.auth.dependencies import require_user
from common.auth.jwt.token_user import TokenUser

router = APIRouter()


@router.post("/academies", response_model=APIResponse, status_code=201)
async def create_academy(
    payload: AcademyCreateSchema,
    caller: TokenUser = Depends(require_user),
    controller: AcademyController = Depends(get_academy_controller),
) -> APIResponse:
    """Create an academy owned by the authenticated caller.

    Args:
        payload: Academy fields.

    Returns:
        HTTP 201 ``APIResponse`` with the created academy.
    """
    return APIResponse(
        data=await controller.create(payload, created_by=int(caller.user_id)),
        message=_("Academy created successfully"),
        status=201,
    )


@router.get("/academies", response_model=APIResponse)
async def list_academies(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    _caller: TokenUser = Depends(require_user),
    controller: AcademyController = Depends(get_academy_controller),
) -> APIResponse:
    """Return a paginated list of academies.

    Args:
        offset: Pagination offset.
        limit:  Items per page (1–100).

    Returns:
        HTTP 200 ``APIResponse`` with items and pagination ``meta``.
    """
    items, meta = await controller.list(offset=offset, limit=limit)
    return APIResponse(
        data=items,
        meta=meta,
        message=_("Academies retrieved successfully"),
        status=200,
    )


@router.get("/academies/{academy_id}", response_model=APIResponse)
async def get_academy(
    academy_id: int = Path(..., description="Primary key of the academy."),
    _caller: TokenUser = Depends(require_user),
    controller: AcademyController = Depends(get_academy_controller),
) -> APIResponse:
    """Retrieve a single academy by primary key.

    Args:
        academy_id: Primary key of the academy.

    Returns:
        HTTP 200 ``APIResponse`` with the academy.
    """
    return APIResponse(
        data=await controller.get(academy_id),
        message=_("Academy {id_} retrieved successfully").format(id_=academy_id),
        status=200,
    )


@router.put("/academies/{academy_id}", response_model=APIResponse)
async def update_academy(
    payload: AcademyUpdateSchema,
    academy_id: int = Path(..., description="Primary key of the academy."),
    _caller: TokenUser = Depends(require_user),
    controller: AcademyController = Depends(get_academy_controller),
) -> APIResponse:
    """Full replace of an academy (PUT) — every field overwrites.

    Args:
        academy_id: Primary key of the academy.
        payload:    PUT body; every field required.

    Returns:
        HTTP 200 ``APIResponse`` with the updated academy.
    """
    return APIResponse(
        data=await controller.update(academy_id, payload),
        message=_("Academy {id_} updated successfully").format(id_=academy_id),
        status=200,
    )


@router.patch("/academies/{academy_id}", response_model=APIResponse)
async def patch_academy(
    payload: AcademyPatchSchema,
    academy_id: int = Path(..., description="Primary key of the academy."),
    _caller: TokenUser = Depends(require_user),
    controller: AcademyController = Depends(get_academy_controller),
) -> APIResponse:
    """Partial update of an academy (PATCH) — unset fields unchanged.

    Args:
        academy_id: Primary key of the academy.
        payload:    PATCH body; any subset of fields.

    Returns:
        HTTP 200 ``APIResponse`` with the updated academy.
    """
    return APIResponse(
        data=await controller.partial_update(academy_id, payload),
        message=_("Academy {id_} updated successfully").format(id_=academy_id),
        status=200,
    )


@router.delete("/academies/{academy_id}", response_model=APIResponse)
async def delete_academy(
    academy_id: int = Path(..., description="Primary key of the academy."),
    _caller: TokenUser = Depends(require_user),
    controller: AcademyController = Depends(get_academy_controller),
) -> APIResponse:
    """Delete an academy by primary key (DELETE).

    Args:
        academy_id: Primary key of the academy to delete.

    Returns:
        HTTP 200 ``APIResponse`` confirming deletion.
    """
    await controller.delete(academy_id)
    return APIResponse(
        message=_("Academy {id_} deleted successfully").format(id_=academy_id),
        status=200,
    )
