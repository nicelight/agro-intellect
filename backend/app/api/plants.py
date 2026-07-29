from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
import uuid

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from ..access_admin.actor_context import ActorContext
from ..access_admin.dependencies import (
    AuthorizedPlantRequest,
    ProtectedRouteDenied,
    require_actor_context,
    require_plant_permission,
)
from ..access_admin.errors import AuthErrorCode
from ..access_admin.farm_service import (
    FarmCommandError,
    FarmCommandErrorCode,
    FarmService,
)
from ..access_admin.models import Farm, PLANT_KEY_PATTERN, Plant, PlantAccessGrant
from ..access_admin.permissions import OperationKind, PlantPermissionContext


router = APIRouter(prefix="/api", tags=["farm-plants"])


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class FarmDisplayNameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str


class PlantCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_key: str = Field(
        json_schema_extra={"pattern": r"^[a-z0-9]+(?:_[a-z0-9]+)*$"}
    )
    display_name: str


class PlantDisplayNameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str


class PlantAccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_approve_actions: bool


class FarmSummary(BaseModel):
    farm_id: uuid.UUID
    farm_key: Literal["local_farm"]
    display_name: str
    created_at: datetime
    updated_at: datetime


class PlantPermissionSummary(BaseModel):
    can_read: bool
    can_comment: bool
    can_operate: bool
    can_create_domain_tasks: bool
    can_manage_access: bool
    can_approve_actions: bool
    source: Literal["boss_role", "plant_access_grant"]
    grant_id: uuid.UUID | None


class PlantSummary(BaseModel):
    plant_id: uuid.UUID
    farm_id: uuid.UUID
    plant_key: str
    display_name: str
    status: Literal["active", "archived"]
    created_at: datetime
    updated_at: datetime
    permissions: PlantPermissionSummary


class PlantListResponse(BaseModel):
    items: list[PlantSummary]


class PlantAccessGrantSummary(BaseModel):
    grant_id: uuid.UUID
    membership_id: uuid.UUID
    plant_id: uuid.UUID
    status: Literal["active", "revoked"]
    plant_approve_actions: bool
    created_at: datetime
    updated_at: datetime


class PlantAccessListResponse(BaseModel):
    items: list[PlantAccessGrantSummary]


_ERROR_RESPONSES = {
    401: {"model": ErrorEnvelope},
    403: {"model": ErrorEnvelope},
    404: {"model": ErrorEnvelope},
    409: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
    500: {"model": ErrorEnvelope},
}
_ACCESS_UPSERT_RESPONSES = {
    **_ERROR_RESPONSES,
    201: {"model": PlantAccessGrantSummary},
}
_normal_read = require_plant_permission(OperationKind.NORMAL_READ)
_manage_lifecycle = require_plant_permission(OperationKind.MANAGE_LIFECYCLE)
_manage_access = require_plant_permission(OperationKind.MANAGE_ACCESS)


@router.get("/farm", response_model=FarmSummary, responses=_ERROR_RESPONSES)
def get_farm(
    response: Response,
    request: Request,
    actor: ActorContext = Depends(require_actor_context),
) -> FarmSummary:
    _no_store(response)
    return _farm_summary(_read_actor_farm(request, actor))


@router.patch("/farm", response_model=FarmSummary, responses=_ERROR_RESPONSES)
def patch_farm(
    payload: FarmDisplayNameRequest,
    response: Response,
    request: Request,
    actor: ActorContext = Depends(require_actor_context),
) -> FarmSummary:
    _read_actor_farm(request, actor)
    _require_display_name(payload.display_name)
    with request.app.state.database.session() as session:
        result = _farm_command(
            lambda: FarmService(session).change_farm_display_name(
                actor,
                display_name=payload.display_name,
            ),
            persistence_code=AuthErrorCode.FARM_PERSISTENCE_FAILED,
        )
    _no_store(response)
    return _farm_summary(result.entity)


@router.get("/plants", response_model=PlantListResponse, responses=_ERROR_RESPONSES)
def list_plants(
    response: Response,
    request: Request,
    actor: ActorContext = Depends(require_actor_context),
) -> PlantListResponse:
    try:
        with request.app.state.database.session() as session:
            plants = list(
                session.scalars(
                    select(Plant)
                    .where(Plant.farm_id == actor.farm_id, Plant.status == "active")
                    .order_by(Plant.plant_key, Plant.plant_id)
                )
            )
    except Exception:
        raise ProtectedRouteDenied(AuthErrorCode.PLANT_STATE_CONFLICT) from None
    items = []
    for plant in plants:
        permission = actor.resolve_plant_permission(
            plant.plant_id,
            OperationKind.NORMAL_READ,
        )
        if permission.can_read:
            items.append(_plant_summary(plant, permission))
    _no_store(response)
    return PlantListResponse(items=items)


@router.post(
    "/plants",
    response_model=PlantSummary,
    status_code=201,
    responses=_ERROR_RESPONSES,
)
def create_plant(
    payload: PlantCreateRequest,
    response: Response,
    request: Request,
    actor: ActorContext = Depends(require_actor_context),
) -> PlantSummary:
    _read_actor_farm(request, actor)
    if PLANT_KEY_PATTERN.fullmatch(payload.plant_key) is None:
        raise ProtectedRouteDenied(AuthErrorCode.PLANT_KEY_INVALID)
    _require_display_name(payload.display_name)
    with request.app.state.database.session() as session:
        result = _farm_command(
            lambda: FarmService(session).create_plant(
                actor,
                plant_key=payload.plant_key,
                display_name=payload.display_name,
            )
        )
    permission = actor.resolve_plant_permission(
        result.plant.plant_id,
        OperationKind.NORMAL_READ,
    )
    if not permission.can_read:
        raise ProtectedRouteDenied(AuthErrorCode.PLANT_STATE_CONFLICT)
    summary = _plant_summary(result.plant, permission)
    _no_store(response)
    return summary


@router.get(
    "/plants/{plant_id}",
    response_model=PlantSummary,
    responses=_ERROR_RESPONSES,
)
def get_plant(
    plant_id: uuid.UUID,
    response: Response,
    request: Request,
    authorized: AuthorizedPlantRequest = Depends(_normal_read),
) -> PlantSummary:
    plant = _read_plant(request, authorized.actor, plant_id, active_only=True)
    _no_store(response)
    return _plant_summary(plant, authorized.permission)


@router.patch(
    "/plants/{plant_id}",
    response_model=PlantSummary,
    responses=_ERROR_RESPONSES,
)
def patch_plant(
    plant_id: uuid.UUID,
    payload: PlantDisplayNameRequest,
    response: Response,
    request: Request,
    authorized: AuthorizedPlantRequest = Depends(_normal_read),
) -> PlantSummary:
    _require_display_name(payload.display_name)
    with request.app.state.database.session() as session:
        result = _farm_command(
            lambda: FarmService(session).rename_plant(
                authorized.actor,
                plant_id=plant_id,
                display_name=payload.display_name,
            ),
            unavailable_code=AuthErrorCode.PLANT_FORBIDDEN,
        )
    permission = authorized.actor.resolve_plant_permission(
        plant_id,
        OperationKind.NORMAL_READ,
    )
    if not permission.can_read:
        raise ProtectedRouteDenied(AuthErrorCode.PLANT_FORBIDDEN)
    _no_store(response)
    return _plant_summary(result.entity, permission)


@router.post(
    "/plants/{plant_id}/archive",
    response_model=PlantSummary,
    responses=_ERROR_RESPONSES,
)
def archive_plant(
    plant_id: uuid.UUID,
    response: Response,
    request: Request,
    authorized: AuthorizedPlantRequest = Depends(_manage_lifecycle),
) -> PlantSummary:
    return _set_plant_lifecycle(
        request,
        response,
        authorized,
        plant_id,
        archive=True,
    )


@router.post(
    "/plants/{plant_id}/restore",
    response_model=PlantSummary,
    responses=_ERROR_RESPONSES,
)
def restore_plant(
    plant_id: uuid.UUID,
    response: Response,
    request: Request,
    authorized: AuthorizedPlantRequest = Depends(_manage_lifecycle),
) -> PlantSummary:
    return _set_plant_lifecycle(
        request,
        response,
        authorized,
        plant_id,
        archive=False,
    )


@router.get(
    "/plants/{plant_id}/access",
    response_model=PlantAccessListResponse,
    responses=_ERROR_RESPONSES,
)
def list_plant_access(
    plant_id: uuid.UUID,
    response: Response,
    request: Request,
    authorized: AuthorizedPlantRequest = Depends(_manage_access),
) -> PlantAccessListResponse:
    try:
        with request.app.state.database.session() as session:
            grants = list(
                session.scalars(
                    select(PlantAccessGrant)
                    .where(PlantAccessGrant.plant_id == plant_id)
                    .order_by(PlantAccessGrant.membership_id)
                )
            )
    except Exception:
        raise ProtectedRouteDenied(AuthErrorCode.PLANT_STATE_CONFLICT) from None
    _no_store(response)
    return PlantAccessListResponse(items=[_grant_summary(grant) for grant in grants])


@router.put(
    "/plants/{plant_id}/access/{membership_id}",
    response_model=PlantAccessGrantSummary,
    responses=_ACCESS_UPSERT_RESPONSES,
)
def put_plant_access(
    plant_id: uuid.UUID,
    membership_id: uuid.UUID,
    payload: PlantAccessRequest,
    response: Response,
    request: Request,
    authorized: AuthorizedPlantRequest = Depends(_manage_access),
) -> PlantAccessGrantSummary:
    created = not _grant_exists(request, plant_id, membership_id)
    with request.app.state.database.session() as session:
        result = _farm_command(
            lambda: FarmService(session).grant_access(
                authorized.actor,
                plant_id=plant_id,
                membership_id=membership_id,
                plant_approve_actions=payload.plant_approve_actions,
            ),
            invalid_code=(
                AuthErrorCode.PLANT_GRANT_APPROVAL_FORBIDDEN
                if payload.plant_approve_actions
                else AuthErrorCode.VALIDATION_FAILED
            ),
            unavailable_code=AuthErrorCode.PLANT_FORBIDDEN,
        )
    response.status_code = 201 if created else 200
    _no_store(response)
    return _grant_summary(result.entity)


@router.post(
    "/plants/{plant_id}/access/{membership_id}/revoke",
    response_model=PlantAccessGrantSummary,
    responses=_ERROR_RESPONSES,
)
def revoke_plant_access(
    plant_id: uuid.UUID,
    membership_id: uuid.UUID,
    response: Response,
    request: Request,
    authorized: AuthorizedPlantRequest = Depends(_manage_access),
) -> PlantAccessGrantSummary:
    if not _grant_exists(request, plant_id, membership_id):
        raise ProtectedRouteDenied(AuthErrorCode.PLANT_GRANT_NOT_FOUND)
    with request.app.state.database.session() as session:
        result = _farm_command(
            lambda: FarmService(session).revoke_access(
                authorized.actor,
                plant_id=plant_id,
                membership_id=membership_id,
            ),
            unavailable_code=AuthErrorCode.PLANT_GRANT_NOT_FOUND,
        )
    _no_store(response)
    return _grant_summary(result.entity)


def _set_plant_lifecycle(
    request: Request,
    response: Response,
    authorized: AuthorizedPlantRequest,
    plant_id: uuid.UUID,
    *,
    archive: bool,
) -> PlantSummary:
    with request.app.state.database.session() as session:
        service = FarmService(session)
        result = _farm_command(
            lambda: (
                service.archive_plant(authorized.actor, plant_id=plant_id)
                if archive
                else service.restore_plant(authorized.actor, plant_id=plant_id)
            ),
            unavailable_code=AuthErrorCode.PLANT_FORBIDDEN,
        )
    permission = authorized.actor.resolve_plant_permission(
        plant_id,
        OperationKind.MANAGE_LIFECYCLE,
    )
    if not permission.can_manage_access:
        raise ProtectedRouteDenied(AuthErrorCode.PLANT_STATE_CONFLICT)
    _no_store(response)
    return _plant_summary(result.entity, permission)


def _read_actor_farm(request: Request, actor: ActorContext) -> Farm:
    try:
        with request.app.state.database.session() as session:
            farms = list(session.scalars(select(Farm).order_by(Farm.farm_id)))
    except Exception:
        raise ProtectedRouteDenied(AuthErrorCode.FARM_STATE_CONFLICT) from None
    if not farms:
        raise ProtectedRouteDenied(AuthErrorCode.FARM_NOT_INITIALIZED)
    if (
        len(farms) != 1
        or farms[0].farm_id != actor.farm_id
        or farms[0].farm_key != "local_farm"
    ):
        raise ProtectedRouteDenied(AuthErrorCode.FARM_STATE_CONFLICT)
    return farms[0]


def _read_plant(
    request: Request,
    actor: ActorContext,
    plant_id: uuid.UUID,
    *,
    active_only: bool,
) -> Plant:
    try:
        with request.app.state.database.session() as session:
            statement = select(Plant).where(
                Plant.farm_id == actor.farm_id,
                Plant.plant_id == plant_id,
            )
            if active_only:
                statement = statement.where(Plant.status == "active")
            plant = session.scalar(statement)
    except Exception:
        raise ProtectedRouteDenied(AuthErrorCode.PLANT_STATE_CONFLICT) from None
    if plant is None:
        raise ProtectedRouteDenied(AuthErrorCode.PLANT_FORBIDDEN)
    return plant


def _grant_exists(request: Request, plant_id: uuid.UUID, membership_id: uuid.UUID) -> bool:
    try:
        with request.app.state.database.session() as session:
            return session.scalar(
                select(PlantAccessGrant.grant_id).where(
                    PlantAccessGrant.plant_id == plant_id,
                    PlantAccessGrant.membership_id == membership_id,
                )
            ) is not None
    except Exception:
        raise ProtectedRouteDenied(AuthErrorCode.PLANT_STATE_CONFLICT) from None


def _farm_command(
    command,
    *,
    invalid_code: AuthErrorCode = AuthErrorCode.VALIDATION_FAILED,
    unavailable_code: AuthErrorCode = AuthErrorCode.PLANT_FORBIDDEN,
    persistence_code: AuthErrorCode = AuthErrorCode.PLANT_PERSISTENCE_FAILED,
):
    try:
        return command()
    except FarmCommandError as error:
        code = {
            FarmCommandErrorCode.FORBIDDEN: AuthErrorCode.FORBIDDEN,
            FarmCommandErrorCode.PLANT_UNAVAILABLE: unavailable_code,
            FarmCommandErrorCode.MEMBERSHIP_UNAVAILABLE: (
                AuthErrorCode.PLANT_GRANT_TARGET_INVALID
            ),
            FarmCommandErrorCode.INVALID_INPUT: invalid_code,
            FarmCommandErrorCode.CONFLICT: AuthErrorCode.PLANT_KEY_CONFLICT,
            FarmCommandErrorCode.PERSISTENCE_FAILED: persistence_code,
        }[error.code]
        raise ProtectedRouteDenied(code) from None


def _require_display_name(value: str) -> None:
    if not value.strip():
        raise ProtectedRouteDenied(AuthErrorCode.VALIDATION_FAILED)


def _farm_summary(farm: Farm) -> FarmSummary:
    return FarmSummary(
        farm_id=farm.farm_id,
        farm_key=farm.farm_key,
        display_name=farm.display_name,
        created_at=_timestamp(farm.created_at),
        updated_at=_timestamp(farm.updated_at),
    )


def _plant_summary(
    plant: Plant,
    permission: PlantPermissionContext,
) -> PlantSummary:
    if permission.source.value == "denied":
        raise ProtectedRouteDenied(AuthErrorCode.PLANT_FORBIDDEN)
    return PlantSummary(
        plant_id=plant.plant_id,
        farm_id=plant.farm_id,
        plant_key=plant.plant_key,
        display_name=plant.display_name,
        status=plant.status,
        created_at=_timestamp(plant.created_at),
        updated_at=_timestamp(plant.updated_at),
        permissions=PlantPermissionSummary(
            can_read=permission.can_read,
            can_comment=permission.can_comment,
            can_operate=permission.can_operate,
            can_create_domain_tasks=permission.can_create_domain_tasks,
            can_manage_access=permission.can_manage_access,
            can_approve_actions=permission.can_approve_actions,
            source=permission.source.value,
            grant_id=permission.grant_id,
        ),
    )


def _grant_summary(grant: PlantAccessGrant) -> PlantAccessGrantSummary:
    return PlantAccessGrantSummary(
        grant_id=grant.grant_id,
        membership_id=grant.membership_id,
        plant_id=grant.plant_id,
        status=grant.status,
        plant_approve_actions=grant.plant_approve_actions,
        created_at=_timestamp(grant.created_at),
        updated_at=_timestamp(grant.updated_at),
    )


def _timestamp(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


__all__ = ["router"]
