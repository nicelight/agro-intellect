"""Task-loop repository with explicit parent/current-authority locks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.models import (
    Account,
    FarmMembership,
    LocalSession,
    Plant,
    PlantAccessGrant,
)
from ..photo_intake.models import PhotoCatalogItem
from ..plant_operations.models import DailyCheckIn, ManualMeasurement
from ..plant_state.models import PlantStateRecord
from ..safety_gate.models import SafetyActionDecision, SafetyClassification
from .models import (
    Approval,
    OrdinaryTaskDispatchDisposition,
    Outcome,
    Task,
    TaskFollowUpRuntimeDisposition,
)


@dataclass(frozen=True, slots=True)
class CurrentTaskScope:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    plant_status: str
    role_preset: str
    permission_source: str
    grant_id: uuid.UUID | None
    can_read: bool
    can_mutate_tasks: bool
    can_approve_actions: bool


class TaskFollowUpRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def lock_current_scope(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        now: datetime,
    ) -> CurrentTaskScope | None:
        local_session = self.session.scalar(
            select(LocalSession)
            .where(LocalSession.session_id == actor.session_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        account = self.session.scalar(
            select(Account)
            .where(Account.account_id == actor.account_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        membership = self.session.scalar(
            select(FarmMembership)
            .where(
                FarmMembership.membership_id == actor.membership_id,
                FarmMembership.account_id == actor.account_id,
                FarmMembership.farm_id == actor.farm_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        plant = self.session.scalar(
            select(Plant)
            .where(Plant.plant_id == plant_id, Plant.farm_id == actor.farm_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if any(item is None for item in (local_session, account, membership, plant)):
            return None
        assert local_session is not None and account is not None
        assert membership is not None and plant is not None
        instant = _utc(now)
        expires_at = _utc(local_session.expires_at)
        if (
            local_session.account_id != actor.account_id
            or local_session.revoked_at is not None
            or instant >= expires_at
            or account.account_status != "active"
            or membership.membership_status != "active"
            or membership.role_preset != actor.role_preset.value
        ):
            return None

        role = membership.role_preset
        grant = None
        if role in {"engineer", "consultant"}:
            grant = self.session.scalar(
                select(PlantAccessGrant)
                .where(
                    PlantAccessGrant.membership_id == membership.membership_id,
                    PlantAccessGrant.plant_id == plant.plant_id,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        if role == "boss":
            can_read = True
            can_mutate = True
            can_approve = True
            source = "boss_role"
            grant_id = None
        elif grant is not None and grant.status == "active":
            can_read = True
            can_mutate = role == "engineer"
            can_approve = role == "engineer" and grant.plant_approve_actions is True
            source = "plant_access_grant"
            grant_id = grant.grant_id
        else:
            can_read = can_mutate = can_approve = False
            source = "denied"
            grant_id = None
        return CurrentTaskScope(
            farm_id=plant.farm_id,
            plant_id=plant.plant_id,
            plant_status=plant.status,
            role_preset=role,
            permission_source=source,
            grant_id=grant_id,
            can_read=can_read,
            can_mutate_tasks=can_mutate,
            can_approve_actions=can_approve,
        )

    def acquire_task_follow_up_run_lock(
        self,
        run_id: uuid.UUID,
        *,
        lock_key: int | None = None,
    ) -> None:
        if not isinstance(run_id, uuid.UUID):
            raise ValueError("A UUID run identity is required.")
        key = task_follow_up_run_lock_key(run_id) if lock_key is None else lock_key
        if (
            isinstance(key, bool)
            or not isinstance(key, int)
            or not -(2**63) <= key < 2**63
        ):
            raise ValueError("A signed PostgreSQL advisory key is required.")
        self.session.execute(select(func.pg_advisory_xact_lock(key))).one()

    def runtime_disposition_for_run(
        self,
        run_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> TaskFollowUpRuntimeDisposition | None:
        query = select(TaskFollowUpRuntimeDisposition).where(
            TaskFollowUpRuntimeDisposition.run_id == run_id
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def safety_classification(
        self, message_id: uuid.UUID, *, for_update: bool = False
    ) -> SafetyClassification | None:
        query = select(SafetyClassification).where(
            SafetyClassification.message_id == message_id
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def safety_decision(
        self, decision_id: uuid.UUID, *, for_update: bool = False
    ) -> SafetyActionDecision | None:
        query = select(SafetyActionDecision).where(
            SafetyActionDecision.decision_id == decision_id
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def approval_for_decision(
        self, decision_id: uuid.UUID, *, for_update: bool = False
    ) -> Approval | None:
        query = select(Approval).where(Approval.safety_decision_id == decision_id)
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def approval_for_request(self, request_id: uuid.UUID) -> Approval | None:
        return self.session.scalar(
            select(Approval)
            .where(Approval.decision_request_id == request_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def task_for_classification(
        self, message_id: uuid.UUID, *, for_update: bool = False
    ) -> Task | None:
        query = select(Task).where(Task.classification_message_id == message_id)
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def dispatch_disposition_for_message(
        self, message_id: uuid.UUID, *, for_update: bool = False
    ) -> OrdinaryTaskDispatchDisposition | None:
        query = select(OrdinaryTaskDispatchDisposition).where(
            OrdinaryTaskDispatchDisposition.classification_message_id == message_id
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def dispatch_disposition_for_run(
        self, run_id: uuid.UUID, *, for_update: bool = False
    ) -> OrdinaryTaskDispatchDisposition | None:
        query = select(OrdinaryTaskDispatchDisposition).where(
            OrdinaryTaskDispatchDisposition.run_id == run_id
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def task_for_create_request(self, request_id: uuid.UUID) -> Task | None:
        return self.session.scalar(
            select(Task)
            .where(Task.create_request_id == request_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def task_for_completion_request(self, request_id: uuid.UUID) -> Task | None:
        return self.session.scalar(
            select(Task)
            .where(Task.completion_request_id == request_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def task_for_approval(
        self, approval_id: uuid.UUID, *, for_update: bool = False
    ) -> Task | None:
        query = select(Task).where(Task.approval_id == approval_id)
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def task(
        self, task_id: uuid.UUID, *, for_update: bool = False
    ) -> Task | None:
        query = select(Task).where(Task.task_id == task_id)
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def follow_up_for_action(
        self, task_id: uuid.UUID, *, for_update: bool = False
    ) -> Task | None:
        query = select(Task).where(Task.parent_action_task_id == task_id)
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def outcome_for_follow_up(
        self, task_id: uuid.UUID, *, for_update: bool = False
    ) -> Outcome | None:
        query = select(Outcome).where(Outcome.follow_up_task_id == task_id)
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def outcome_for_request(self, request_id: uuid.UUID) -> Outcome | None:
        return self.session.scalar(
            select(Outcome)
            .where(Outcome.request_id == request_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def lock_measurement(self, measurement_id: uuid.UUID) -> ManualMeasurement | None:
        return self.session.scalar(
            select(ManualMeasurement)
            .where(ManualMeasurement.measurement_id == measurement_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def lock_authoritative_ref(
        self,
        ref: str,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> bool:
        kind, identifier = ref.split(":", maxsplit=1)
        item_id = uuid.UUID(identifier)
        if kind == "plant":
            row = self.session.scalar(
                select(Plant)
                .where(Plant.plant_id == item_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        else:
            model = {
                "daily_checkin": (DailyCheckIn, DailyCheckIn.check_in_id),
                "manual_measurement": (ManualMeasurement, ManualMeasurement.measurement_id),
                "photo_catalog_item": (PhotoCatalogItem, PhotoCatalogItem.photo_id),
                "plant_state_record": (PlantStateRecord, PlantStateRecord.state_record_id),
            }.get(kind)
            if model is None:
                return False
            entity, key = model
            row = self.session.scalar(
                select(entity)
                .where(key == item_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        return (
            row is not None
            and getattr(row, "farm_id", farm_id) == farm_id
            and getattr(row, "plant_id", None) == plant_id
        )

    def lock_task_follow_up_source_ref(
        self,
        ref: str,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> bool:
        """Resolve only the competence's Task/Outcome/evidence source union."""

        try:
            kind, identifier = ref.split(":", maxsplit=1)
            item_id = uuid.UUID(identifier)
        except (ValueError, TypeError, AttributeError):
            return False
        model = {
            "task": (Task, Task.task_id),
            "outcome": (Outcome, Outcome.outcome_id),
            "daily_checkin": (DailyCheckIn, DailyCheckIn.check_in_id),
            "manual_measurement": (
                ManualMeasurement,
                ManualMeasurement.measurement_id,
            ),
            "plant_state_record": (
                PlantStateRecord,
                PlantStateRecord.state_record_id,
            ),
        }.get(kind)
        if model is None:
            return False
        entity, key = model
        row = self.session.scalar(
            select(entity)
            .where(key == item_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return (
            row is not None
            and getattr(row, "farm_id", None) == farm_id
            and getattr(row, "plant_id", None) == plant_id
        )

    def evidence_for_ref(self, ref: str) -> object | None:
        """Resolve one closed Task Follow-Up evidence descriptor source."""

        try:
            kind, identifier = ref.split(":", maxsplit=1)
            item_id = uuid.UUID(identifier)
        except (ValueError, TypeError, AttributeError):
            return None
        model = {
            "daily_checkin": (DailyCheckIn, DailyCheckIn.check_in_id),
            "manual_measurement": (
                ManualMeasurement,
                ManualMeasurement.measurement_id,
            ),
            "plant_state_record": (
                PlantStateRecord,
                PlantStateRecord.state_record_id,
            ),
        }.get(kind)
        if model is None:
            return None
        entity, key = model
        return self.session.scalar(
            select(entity)
            .where(key == item_id)
            .execution_options(populate_existing=True)
        )

    def list_tasks(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
        status: str | None,
        kind: str | None,
        limit: int,
    ) -> list[Task]:
        query = select(Task).where(Task.farm_id == farm_id, Task.plant_id == plant_id)
        if status is not None:
            query = query.where(Task.status == status)
        if kind is not None:
            query = query.where(Task.kind == kind)
        return list(
            self.session.scalars(
                query.order_by(Task.created_at.desc(), Task.task_id.desc()).limit(limit)
            )
        )

    def list_approvals(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
        status: str | None,
        limit: int,
    ) -> list[Approval]:
        query = select(Approval).where(
            Approval.farm_id == farm_id, Approval.plant_id == plant_id
        )
        if status is not None:
            query = query.where(Approval.status == status)
        return list(
            self.session.scalars(
                query.order_by(Approval.created_at.desc(), Approval.approval_id.desc()).limit(limit)
            )
        )


def _utc(value: datetime) -> datetime:
    normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    if normalized.utcoffset() is None:
        raise ValueError("A timezone-aware instant is required.")
    return normalized.astimezone(timezone.utc)


def task_follow_up_run_lock_key(run_id: uuid.UUID) -> int:
    if not isinstance(run_id, uuid.UUID):
        raise ValueError("A UUID run identity is required.")
    digest = sha256(b"ft012-task-follow-up:" + run_id.bytes).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


__all__ = [
    "CurrentTaskScope",
    "TaskFollowUpRepository",
    "task_follow_up_run_lock_key",
]
