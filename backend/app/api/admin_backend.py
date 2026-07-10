from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import uuid

from fastapi import Request

from ..access_admin.actor_context import ActorContext
from ..access_admin.admin_service import AdminService
from ..database import DatabaseHandle
from .admin_mapping import (
    account_summary_from_projection,
    account_summary_from_result,
    audit_summary,
    plant_projection_summary,
)
from .admin_schemas import (
    AdminAccountCreateRequest,
    AdminAccountSummary,
    AdminAuditSummary,
    AdminPlantProjection,
)


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
            projections = AdminService(session).list_personnel(
                actor,
                account_status=account_status,
                role_preset=role_preset,
            )
            return [account_summary_from_projection(item) for item in projections]

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
            return account_summary_from_result(result)

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
            return account_summary_from_result(result)

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
            return account_summary_from_result(result)

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
            return [plant_projection_summary(item) for item in projections]

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
            records = AdminService(session).list_audit(
                actor,
                limit=limit,
                offset=offset,
                target_type=target_type,
                target_id=target_id,
                plant_id=plant_id,
            )
            return [audit_summary(item) for item in records]


def get_admin_backend(request: Request) -> AdminApiBackend:
    return DatabaseAdminApiBackend(request.app.state.database)


__all__ = [
    "AdminApiBackend",
    "DatabaseAdminApiBackend",
    "get_admin_backend",
]
