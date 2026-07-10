from __future__ import annotations

from datetime import datetime
from typing import Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field, SecretStr


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


__all__ = [
    "AdminAccountCreateRequest",
    "AdminAccountDisableRequest",
    "AdminAccountListResponse",
    "AdminAccountSummary",
    "AdminAuditListResponse",
    "AdminAuditSummary",
    "AdminMembershipRoleRequest",
    "AdminMembershipSummary",
    "AdminPlantGrantCounts",
    "AdminPlantListResponse",
    "AdminPlantProjection",
    "ErrorDetail",
    "ErrorEnvelope",
]
