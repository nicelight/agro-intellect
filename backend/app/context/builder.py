"""Permission-aware context builder — assembles a ContextPackage for agent harness runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from backend.app.access.authorization import get_role_permissions
from backend.app.api.errors import AppError, ErrorCode
from backend.app.context.models import ActorContext, ActorContextState


@dataclass(frozen=True)
class ContextPackage:
    actor_context: ActorContext
    farm_id: str | None
    plant_ids: list[str]
    role: str | None
    permissions: dict
    built_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class PermissionAwareContextBuilder:
    def __init__(self, repo, audit_repo=None) -> None:
        self._repo = repo
        self._audit_repo = audit_repo

    def build_context(
        self, actor_context: ActorContext, request_ref: str | None = None
    ) -> ContextPackage:
        if actor_context.state is not ActorContextState.RESOLVED:
            raise AppError(
                code=ErrorCode.PERMISSION_DENIED,
                message="A resolved ActorContext is required to build context.",
                request_ref=request_ref or actor_context.request_ref,
                next_actions=["authenticate"],
            )

        farm_id = actor_context.farm_id
        role = actor_context.role
        membership_status = actor_context.membership_status

        role_permissions = get_role_permissions(role)

        plant_perms = actor_context.plant_permissions
        plant_approve_actions = any(
            pp.plant_approve_actions for pp in plant_perms
        )
        permissions = {
            **role_permissions,
            "plant_approve_actions": plant_approve_actions,
        }

        authorized_plants = [
            pp.plant_id
            for pp in plant_perms
            if pp.grant_state == "granted"
        ]

        return ContextPackage(
            actor_context=actor_context,
            farm_id=farm_id,
            plant_ids=authorized_plants,
            role=role,
            permissions=permissions,
        )

    def authorize_plant_access(
        self, actor_context: ActorContext, plant_id: str
    ) -> None:
        if actor_context.state is not ActorContextState.RESOLVED:
            raise AppError(
                code=ErrorCode.PERMISSION_DENIED,
                message="A resolved ActorContext is required for plant access.",
                request_ref=actor_context.request_ref,
                next_actions=["authenticate"],
            )

        for pp in actor_context.plant_permissions:
            if pp.plant_id == plant_id:
                if pp.grant_state == "revoked":
                    raise AppError(
                        code=ErrorCode.PERMISSION_DENIED,
                        message="Plant access has been revoked.",
                        request_ref=actor_context.request_ref,
                        next_actions=["contact_admin"],
                    )
                return

        raise AppError(
            code=ErrorCode.PERMISSION_DENIED,
            message="You do not have access to this plant.",
            request_ref=actor_context.request_ref,
            next_actions=["select_authorized_plant"],
        )
