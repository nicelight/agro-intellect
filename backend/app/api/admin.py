from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Literal, Protocol
import uuid

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select

from ..access_admin.actor_context import ActorContext
from ..access_admin.admin_service import (
    AccountMembershipResult,
    AdminCommandError,
    AdminCommandErrorCode,
    AdminService,
    PlantProjection,
)
from ..access_admin.dependencies import ProtectedRouteDenied, require_actor_context
from ..access_admin.errors import AuthErrorCode
from ..access_admin.models import Account, FarmMembership
from ..access_admin.models import AdminAuditRecord
from ..database import DatabaseHandle


router = APIRouter(prefix="/api/admin", tags=["admin"])


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class AdminMembershipSummary(BaseModel):
    membership_id: uuid.UUID
    account_id: uuid.UUID
    farm_id: uuid.UUID
    role_preset: Literal["boss", "engineer", "consultant"]
    membership_status: Literal["active", "disabled"]
    disabled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminAccountSummary(BaseModel):
    account_id: uuid.UUID
    login_name: str
    display_name: str
    account_status: Literal["active", "disabled"]
    disabled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    membership: AdminMembershipSummary


class AdminAccountListResponse(BaseModel):
    items: list[AdminAccountSummary]


class AdminAccountCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login_name: str = Field(min_length=1, max_length=256)
    display_name: str = Field(min_length=1, max_length=256)
    password: SecretStr = Field(min_length=1, max_length=4096)
    role_preset: Literal["boss", "engineer", "consultant"]


class AdminAccountDisableRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=512)


class AdminMembershipRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_preset: Literal["boss", "engineer", "consultant"]


class AdminPlantGrantCounts(BaseModel):
    active: int
    revoked: int
    approve_actions_enabled: int


class AdminPlantProjection(BaseModel):
    plant_id: uuid.UUID
    farm_id: uuid.UUID
    plant_key: str
    display_name: str
    status: Literal["active", "archived"]
    created_at: datetime
    updated_at: datetime
    grant_counts: AdminPlantGrantCounts


class AdminPlantListResponse(BaseModel):
    items: list[AdminPlantProjection]


class AdminAuditSummary(BaseModel):
    admin_audit_id: uuid.UUID
    farm_id: uuid.UUID
    actor_kind: Literal["account", "system_bootstrap"]
    actor_account_id: uuid.UUID | None
    actor_membership_id: uuid.UUID | None
    actor_role_preset: Literal["boss", "engineer", "consultant"] | None
    action_type: str
    target_type: Literal["account", "membership", "farm", "plant", "plant_access_grant"]
    target_id: uuid.UUID
    plant_id: uuid.UUID | None
    request_id: str
    before_summary: dict[str, object]
    after_summary: dict[str, object]
    source_refs: list[object]
    created_at: datetime


class AdminAuditListResponse(BaseModel):
    items: list[AdminAuditSummary]
    next_cursor: str | None


class AdminApiBackend(Protocol):
    def list_accounts(
        self,
        actor: ActorContext,
        *,
        account_status: str | None,
        role_preset: str | None,
    ) -> list[AdminAccountSummary]: ...

    def create_account(
        self,
        actor: ActorContext,
        payload: AdminAccountCreateRequest,
    ) -> AdminAccountSummary: ...

    def disable_account(
        self,
        actor: ActorContext,
        *,
        account_id: uuid.UUID,
        reason: str | None,
    ) -> AdminAccountSummary: ...

    def change_membership_role(
        self,
        actor: ActorContext,
        *,
        membership_id: uuid.UUID,
        role_preset: str,
    ) -> AdminAccountSummary: ...

    def list_plants(
        self,
        actor: ActorContext,
        *,
        include_archived: bool,
    ) -> list[AdminPlantProjection]: ...

    def list_audit(
        self,
        actor: ActorContext,
        *,
        limit: int,
        offset: int,
        target_type: str | None,
        target_id: uuid.UUID | None,
        plant_id: uuid.UUID | None,
    ) -> list[AdminAuditSummary]: ...


@dataclass(frozen=True, slots=True)
class DatabaseAdminApiBackend:
    database: DatabaseHandle

    def list_accounts(
        self,
        actor: ActorContext,
        *,
        account_status: str | None,
        role_preset: str | None,
    ) -> list[AdminAccountSummary]:
        with self.database.session() as session:
            service = AdminService(session)
            summaries = service.list_personnel(
                actor,
                account_status=account_status,
                role_preset=role_preset,
            )
            return [_account_summary_from_service_dict(session, item) for item in summaries]

    def create_account(
        self,
        actor: ActorContext,
        payload: AdminAccountCreateRequest,
    ) -> AdminAccountSummary:
        with self.database.session() as session:
            result = AdminService(session).create_account(
                actor,
                login_name=payload.login_name,
                display_name=payload.display_name,
                password=payload.password.get_secret_value(),
                role_preset=payload.role_preset,
            )
            return _account_summary_from_result(result)

    def disable_account(
        self,
        actor: ActorContext,
        *,
        account_id: uuid.UUID,
        reason: str | None,
    ) -> AdminAccountSummary:
        with self.database.session() as session:
            result = AdminService(session).disable_account(
                actor,
                account_id=account_id,
                reason=reason,
            )
            return _account_summary_from_result(result)

    def change_membership_role(
        self,
        actor: ActorContext,
        *,
        membership_id: uuid.UUID,
        role_preset: str,
    ) -> AdminAccountSummary:
        with self.database.session() as session:
            result = AdminService(session).change_membership_role(
                actor,
                membership_id=membership_id,
                role_preset=role_preset,
            )
            return _account_summary_from_result(result)

    def list_plants(
        self,
        actor: ActorContext,
        *,
        include_archived: bool,
    ) -> list[AdminPlantProjection]:
        with self.database.session() as session:
            projections = AdminService(session).list_plant_projections(
                actor,
                include_archived=include_archived,
            )
            return [_plant_projection_summary(item) for item in projections]

    def list_audit(
        self,
        actor: ActorContext,
        *,
        limit: int,
        offset: int,
        target_type: str | None,
        target_id: uuid.UUID | None,
        plant_id: uuid.UUID | None,
    ) -> list[AdminAuditSummary]:
        with self.database.session() as session:
            AdminService(session).list_audit(actor, limit=1)
            statement = (
                select(AdminAuditRecord)
                .where(AdminAuditRecord.farm_id == actor.farm_id)
                .order_by(
                    AdminAuditRecord.created_at.desc(),
                    AdminAuditRecord.admin_audit_id.desc(),
                )
                .offset(offset)
                .limit(limit)
            )
            if target_type is not None:
                statement = statement.where(AdminAuditRecord.target_type == target_type)
            if target_id is not None:
                statement = statement.where(AdminAuditRecord.target_id == target_id)
            if plant_id is not None:
                statement = statement.where(AdminAuditRecord.plant_id == plant_id)
            try:
                records = list(session.scalars(statement))
            except Exception:
                raise AdminCommandError(
                    AdminCommandErrorCode.PERSISTENCE_FAILED
                ) from None
            return [_audit_summary_from_record(record) for record in records]


_ERROR_RESPONSES = {
    401: {"model": ErrorEnvelope},
    403: {"model": ErrorEnvelope},
    404: {"model": ErrorEnvelope},
    409: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
    500: {"model": ErrorEnvelope},
}
_AUDIT_TARGETS = {"account", "membership", "farm", "plant", "plant_access_grant"}


def get_admin_backend(request: Request) -> AdminApiBackend:
    return DatabaseAdminApiBackend(request.app.state.database)


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
    offset = _decode_audit_cursor(cursor)

    def command() -> AdminAuditListResponse:
        candidates = backend.list_audit(
            actor,
            limit=limit + 1,
            offset=offset,
            target_type=target_type,
            target_id=target_id,
            plant_id=plant_id,
        )
        page = candidates
        items = page[:limit]
        next_cursor = (
            _encode_audit_cursor(offset + len(items)) if len(page) > limit else None
        )
        return AdminAuditListResponse(items=items, next_cursor=next_cursor)

    return _admin_response(response, command)


def _admin_response(response: Response, command):
    try:
        result = command()
    except AdminCommandError as error:
        raise ProtectedRouteDenied(_admin_error_code(error.code)) from None
    _no_store(response)
    return result


def _admin_error_code(code: AdminCommandErrorCode) -> AuthErrorCode:
    return {
        AdminCommandErrorCode.FORBIDDEN: AuthErrorCode.FORBIDDEN,
        AdminCommandErrorCode.FARM_NOT_INITIALIZED: AuthErrorCode.FARM_NOT_INITIALIZED,
        AdminCommandErrorCode.FARM_STATE_CONFLICT: AuthErrorCode.FARM_STATE_CONFLICT,
        AdminCommandErrorCode.ACCOUNT_NOT_FOUND: AuthErrorCode.ADMIN_ACCOUNT_NOT_FOUND,
        AdminCommandErrorCode.MEMBERSHIP_NOT_FOUND: (
            AuthErrorCode.ADMIN_MEMBERSHIP_NOT_FOUND
        ),
        AdminCommandErrorCode.ACCOUNT_CONFLICT: AuthErrorCode.ADMIN_ACCOUNT_CONFLICT,
        AdminCommandErrorCode.LAST_BOSS_CONFLICT: (
            AuthErrorCode.ADMIN_LAST_BOSS_CONFLICT
        ),
        AdminCommandErrorCode.INVALID_INPUT: AuthErrorCode.VALIDATION_FAILED,
        AdminCommandErrorCode.PERSISTENCE_FAILED: (
            AuthErrorCode.ADMIN_PERSISTENCE_FAILED
        ),
    }[code]


def _account_summary_from_result(
    result: AccountMembershipResult,
) -> AdminAccountSummary:
    return _account_summary(result.account, result.membership)


def _account_summary_from_service_dict(session, item: dict[str, object]):
    account_id = uuid.UUID(str(item["account_id"]))
    membership = item.get("membership")
    if not isinstance(membership, dict):
        raise AdminCommandError(AdminCommandErrorCode.PERSISTENCE_FAILED)
    membership_id = uuid.UUID(str(membership["membership_id"]))
    row = session.execute(
        select(Account, FarmMembership)
        .join(FarmMembership, FarmMembership.account_id == Account.account_id)
        .where(
            Account.account_id == account_id,
            FarmMembership.membership_id == membership_id,
        )
    ).one_or_none()
    if row is None:
        raise AdminCommandError(AdminCommandErrorCode.PERSISTENCE_FAILED)
    return _account_summary(row[0], row[1])


def _account_summary(account: Account, membership: FarmMembership) -> AdminAccountSummary:
    return AdminAccountSummary(
        account_id=account.account_id,
        login_name=account.login_name,
        display_name=account.display_name,
        account_status=account.account_status,
        disabled_at=_timestamp_or_none(account.disabled_at),
        created_at=_timestamp(account.created_at),
        updated_at=_timestamp(account.updated_at),
        membership=AdminMembershipSummary(
            membership_id=membership.membership_id,
            account_id=membership.account_id,
            farm_id=membership.farm_id,
            role_preset=membership.role_preset,
            membership_status=membership.membership_status,
            disabled_at=_timestamp_or_none(membership.disabled_at),
            created_at=_timestamp(membership.created_at),
            updated_at=_timestamp(membership.updated_at),
        ),
    )


def _plant_projection_summary(item: PlantProjection) -> AdminPlantProjection:
    plant = item.plant
    return AdminPlantProjection(
        plant_id=plant.plant_id,
        farm_id=plant.farm_id,
        plant_key=plant.plant_key,
        display_name=plant.display_name,
        status=plant.status,
        created_at=_timestamp(plant.created_at),
        updated_at=_timestamp(plant.updated_at),
        grant_counts=AdminPlantGrantCounts(**item.grant_counts),
    )


def _audit_summary(item: dict[str, object]) -> AdminAuditSummary:
    return AdminAuditSummary(
        admin_audit_id=uuid.UUID(str(item["admin_audit_id"])),
        farm_id=uuid.UUID(str(item["farm_id"])),
        actor_kind=str(item["actor_kind"]),
        actor_account_id=_uuid_or_none(item["actor_account_id"]),
        actor_membership_id=_uuid_or_none(item["actor_membership_id"]),
        actor_role_preset=item["actor_role_preset"],
        action_type=str(item["action_type"]),
        target_type=str(item["target_type"]),
        target_id=uuid.UUID(str(item["target_id"])),
        plant_id=_uuid_or_none(item["plant_id"]),
        request_id=str(item["request_id"]),
        before_summary=_dict(item["before_summary"]),
        after_summary=_dict(item["after_summary"]),
        source_refs=_list(item["source_refs"]),
        created_at=_timestamp(item["created_at"]),
    )


def _audit_summary_from_record(record: AdminAuditRecord) -> AdminAuditSummary:
    return AdminAuditSummary(
        admin_audit_id=record.admin_audit_id,
        farm_id=record.farm_id,
        actor_kind=record.actor_kind,
        actor_account_id=record.actor_account_id,
        actor_membership_id=record.actor_membership_id,
        actor_role_preset=record.actor_role_preset,
        action_type=record.action_type,
        target_type=record.target_type,
        target_id=record.target_id,
        plant_id=record.plant_id,
        request_id=record.request_id,
        before_summary=_dict(record.before_summary),
        after_summary=_dict(record.after_summary),
        source_refs=_list(record.source_refs),
        created_at=_timestamp(record.created_at),
    )


def _decode_audit_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        offset = payload["offset"]
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ValueError
    except Exception:
        raise ProtectedRouteDenied(AuthErrorCode.ADMIN_AUDIT_CURSOR_INVALID) from None
    return offset


def _encode_audit_cursor(offset: int) -> str:
    payload = {"offset": offset}
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return encoded.rstrip("=")


def _uuid_or_none(value: object) -> uuid.UUID | None:
    if value is None:
        return None
    return uuid.UUID(str(value))


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _timestamp(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise AdminCommandError(AdminCommandErrorCode.PERSISTENCE_FAILED)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _timestamp_or_none(value: object) -> datetime | None:
    return None if value is None else _timestamp(value)


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


__all__ = [
    "AdminApiBackend",
    "DatabaseAdminApiBackend",
    "get_admin_backend",
    "router",
]
