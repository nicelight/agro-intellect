from __future__ import annotations

from typing import Literal
import uuid

from fastapi import APIRouter, Depends, Query, Response

from ..access_admin.actor_context import ActorContext
from ..access_admin.admin_service import AdminCommandError
from ..access_admin.dependencies import ProtectedRouteDenied, require_actor_context
from .admin_backend import AdminApiBackend, DatabaseAdminApiBackend, get_admin_backend
from .admin_mapping import (
    admin_error_code,
    decode_audit_cursor,
    encode_audit_cursor,
)
from .admin_schemas import (
    AdminAccountCreateRequest,
    AdminAccountDisableRequest,
    AdminAccountListResponse,
    AdminAccountSummary,
    AdminAuditListResponse,
    AdminMembershipRoleRequest,
    AdminPlantListResponse,
    ErrorEnvelope,
)


router = APIRouter(prefix="/api/admin", tags=["admin"])

_ERROR_RESPONSES = {
    401: {"model": ErrorEnvelope},
    403: {"model": ErrorEnvelope},
    404: {"model": ErrorEnvelope},
    409: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
    500: {"model": ErrorEnvelope},
}


@router.get(
    "/accounts",
    response_model=AdminAccountListResponse,
    responses=_ERROR_RESPONSES,
)
def list_accounts(
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
    backend: AdminApiBackend = Depends(get_admin_backend),
    status: Literal["active", "disabled"] | None = None,
    role_preset: Literal["boss", "engineer", "consultant"] | None = None,
) -> AdminAccountListResponse:
    return _admin_response(
        response,
        lambda: AdminAccountListResponse(
            items=backend.list_accounts(
                actor,
                account_status=status,
                role_preset=role_preset,
            )
        ),
    )


@router.post(
    "/accounts",
    response_model=AdminAccountSummary,
    status_code=201,
    responses=_ERROR_RESPONSES,
)
def create_account(
    payload: AdminAccountCreateRequest,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
    backend: AdminApiBackend = Depends(get_admin_backend),
) -> AdminAccountSummary:
    return _admin_response(response, lambda: backend.create_account(actor, payload))


@router.post(
    "/accounts/{account_id}/disable",
    response_model=AdminAccountSummary,
    responses=_ERROR_RESPONSES,
)
def disable_account(
    account_id: uuid.UUID,
    response: Response,
    payload: AdminAccountDisableRequest | None = None,
    actor: ActorContext = Depends(require_actor_context),
    backend: AdminApiBackend = Depends(get_admin_backend),
) -> AdminAccountSummary:
    return _admin_response(
        response,
        lambda: backend.disable_account(
            actor,
            account_id=account_id,
            reason=payload.reason if payload is not None else None,
        ),
    )


@router.patch(
    "/memberships/{membership_id}/role",
    response_model=AdminAccountSummary,
    responses=_ERROR_RESPONSES,
)
def change_membership_role(
    membership_id: uuid.UUID,
    payload: AdminMembershipRoleRequest,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
    backend: AdminApiBackend = Depends(get_admin_backend),
) -> AdminAccountSummary:
    return _admin_response(
        response,
        lambda: backend.change_membership_role(
            actor,
            membership_id=membership_id,
            role_preset=payload.role_preset,
        ),
    )


@router.get(
    "/plants",
    response_model=AdminPlantListResponse,
    responses=_ERROR_RESPONSES,
)
def list_plants(
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
    backend: AdminApiBackend = Depends(get_admin_backend),
    include_archived: bool = False,
) -> AdminPlantListResponse:
    return _admin_response(
        response,
        lambda: AdminPlantListResponse(
            items=backend.list_plants(actor, include_archived=include_archived)
        ),
    )


@router.get(
    "/audit",
    response_model=AdminAuditListResponse,
    responses=_ERROR_RESPONSES,
)
def list_audit(
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
    backend: AdminApiBackend = Depends(get_admin_backend),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    target_type: Literal["account", "membership", "farm", "plant", "plant_access_grant"]
    | None = None,
    target_id: uuid.UUID | None = None,
    plant_id: uuid.UUID | None = None,
) -> AdminAuditListResponse:
    offset = decode_audit_cursor(cursor)

    def command() -> AdminAuditListResponse:
        page = backend.list_audit(
            actor,
            limit=limit + 1,
            offset=offset,
            target_type=target_type,
            target_id=target_id,
            plant_id=plant_id,
        )
        items = page[:limit]
        next_cursor = (
            encode_audit_cursor(offset + len(items)) if len(page) > limit else None
        )
        return AdminAuditListResponse(items=items, next_cursor=next_cursor)

    return _admin_response(response, command)


def _admin_response(response: Response, command):
    try:
        result = command()
    except AdminCommandError as error:
        raise ProtectedRouteDenied(admin_error_code(error.code)) from None
    _no_store(response)
    return result


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


__all__ = [
    "AdminApiBackend",
    "DatabaseAdminApiBackend",
    "get_admin_backend",
    "router",
]
