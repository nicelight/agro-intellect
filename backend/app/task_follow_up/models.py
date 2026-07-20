"""PostgreSQL mutable authority for FT-012 Approval, Task, and Outcome."""

from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..access_admin.models import Base, JSON_DOCUMENT


class OrdinaryTaskDispatchDisposition(Base):
    __tablename__ = "ordinary_task_dispatch_dispositions"
    __table_args__ = (
        PrimaryKeyConstraint(
            "classification_message_id",
            name="pk_ordinary_task_dispatch_dispositions",
        ),
        UniqueConstraint(
            "run_id", name="uq_ordinary_task_dispatch_dispositions_run"
        ),
        CheckConstraint(
            "input_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_ordinary_task_dispatch_dispositions_input_sha256",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "outcome IN ('consumed', 'denied')",
            name="ck_ordinary_task_dispatch_dispositions_outcome",
        ),
        CheckConstraint(
            "denial_code IS NULL OR denial_code IN "
            "('TASK_SCOPE_NOT_FOUND', 'TASK_COMMAND_FORBIDDEN', "
            "'TASK_PLANT_NOT_ACTIVE')",
            name="ck_ordinary_task_dispatch_dispositions_denial_code",
        ),
        CheckConstraint(
            "((outcome = 'consumed' AND denial_code IS NULL) OR "
            "(outcome = 'denied' AND denial_code IS NOT NULL))",
            name="ck_ordinary_task_dispatch_dispositions_terminal_matrix",
        ),
    )

    classification_message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("safety_classifications.message_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    farm_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farms.farm_id", ondelete="RESTRICT"),
        nullable=False,
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plants.plant_id", ondelete="RESTRICT"),
        nullable=False,
    )
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    denial_code: Mapped[str | None] = mapped_column(String(32))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (
        UniqueConstraint("safety_decision_id", name="uq_approvals_safety_decision"),
        UniqueConstraint("decision_request_id", name="uq_approvals_decision_request"),
        CheckConstraint(
            "action_kind IN ('ph_adjustment', 'ec_adjustment', 'solution_change')",
            name="ck_approvals_action_kind",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_approvals_status",
        ),
        CheckConstraint("record_version IN (1, 2)", name="ck_approvals_version"),
        CheckConstraint(
            "decision_actor_role_preset IS NULL OR "
            "decision_actor_role_preset IN ('boss', 'engineer')",
            name="ck_approvals_actor_role",
        ),
        CheckConstraint(
            "decision_permission_source IS NULL OR "
            "decision_permission_source IN ('boss_role', 'plant_access_grant')",
            name="ck_approvals_permission_source",
        ),
        CheckConstraint(
            "jsonb_typeof(source_refs) = 'array'",
            name="ck_approvals_source_refs_array",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "decision_event_ref IS NULL OR jsonb_typeof(decision_event_ref) = 'object'",
            name="ck_approvals_event_ref_object",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "decision_request_fingerprint IS NULL OR "
            "decision_request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_approvals_fingerprint",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "((status = 'pending' AND record_version = 1 "
            "AND decided_at IS NULL AND decision_actor_account_id IS NULL "
            "AND decision_actor_membership_id IS NULL "
            "AND decision_actor_role_preset IS NULL "
            "AND decision_permission_source IS NULL AND decision_grant_id IS NULL "
            "AND decision_request_id IS NULL "
            "AND decision_request_fingerprint IS NULL "
            "AND decision_event_ref IS NULL) OR "
            "(status IN ('approved', 'rejected') AND record_version = 2 "
            "AND decided_at IS NOT NULL AND decision_actor_account_id IS NOT NULL "
            "AND decision_actor_membership_id IS NOT NULL "
            "AND decision_actor_role_preset IS NOT NULL "
            "AND decision_permission_source IS NOT NULL "
            "AND decision_request_id IS NOT NULL "
            "AND decision_request_fingerprint IS NOT NULL "
            "AND decision_event_ref IS NOT NULL "
            "AND ((decision_permission_source = 'boss_role' "
            "AND decision_actor_role_preset = 'boss' AND decision_grant_id IS NULL) "
            "OR (decision_permission_source = 'plant_access_grant' "
            "AND decision_actor_role_preset = 'engineer' "
            "AND decision_grant_id IS NOT NULL))))",
            name="ck_approvals_state_matrix",
        ),
        Index("ix_approvals_plant_created", "plant_id", "created_at", "approval_id"),
    )

    approval_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    safety_decision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("safety_action_decisions.decision_id", ondelete="RESTRICT"),
        nullable=False,
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("farms.farm_id", ondelete="RESTRICT"), nullable=False
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("plants.plant_id", ondelete="RESTRICT"), nullable=False
    )
    action_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    record_version: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_refs: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_actor_account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("accounts.account_id", ondelete="RESTRICT")
    )
    decision_actor_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("farm_memberships.membership_id", ondelete="RESTRICT")
    )
    decision_actor_role_preset: Mapped[str | None] = mapped_column(String(16))
    decision_permission_source: Mapped[str | None] = mapped_column(String(32))
    decision_grant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("plant_access_grants.grant_id", ondelete="RESTRICT")
    )
    decision_request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    decision_request_fingerprint: Mapped[str | None] = mapped_column(String(64))
    decision_event_ref: Mapped[dict[str, object] | None] = mapped_column(JSON_DOCUMENT)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("classification_message_id", name="uq_tasks_classification_message"),
        UniqueConstraint("approval_id", name="uq_tasks_approval"),
        UniqueConstraint("parent_action_task_id", name="uq_tasks_parent_action"),
        UniqueConstraint("create_request_id", name="uq_tasks_create_request"),
        UniqueConstraint("completion_request_id", name="uq_tasks_completion_request"),
        CheckConstraint(
            "kind IN ('check', 'measurement', 'action', 'follow_up')",
            name="ck_tasks_kind",
        ),
        CheckConstraint("status IN ('open', 'completed')", name="ck_tasks_status"),
        CheckConstraint(
            "source_type IN ('safe_task_request', 'approved_action', "
            "'automatic_follow_up')",
            name="ck_tasks_source_type",
        ),
        CheckConstraint(
            "btrim(display_text) <> '' AND char_length(display_text) <= 2000",
            name="ck_tasks_display_text",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(source_refs) = 'array'",
            name="ck_tasks_source_refs_array",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(created_event_ref) = 'object' AND "
            "(completed_event_ref IS NULL OR jsonb_typeof(completed_event_ref) = 'object')",
            name="ck_tasks_event_refs_object",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "create_request_fingerprint IS NULL OR "
            "create_request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_tasks_create_fingerprint",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "completion_request_fingerprint IS NULL OR "
            "completion_request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_tasks_completion_fingerprint",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "((source_type = 'safe_task_request' "
            "AND kind IN ('check', 'measurement', 'follow_up') "
            "AND classification_message_id IS NOT NULL AND approval_id IS NULL "
            "AND parent_action_task_id IS NULL AND create_request_id IS NOT NULL "
            "AND create_request_fingerprint IS NOT NULL) OR "
            "(source_type = 'approved_action' AND kind = 'action' "
            "AND classification_message_id IS NULL AND approval_id IS NOT NULL "
            "AND parent_action_task_id IS NULL AND create_request_id IS NULL "
            "AND create_request_fingerprint IS NULL) OR "
            "(source_type = 'automatic_follow_up' AND kind = 'follow_up' "
            "AND classification_message_id IS NULL AND approval_id IS NULL "
            "AND parent_action_task_id IS NOT NULL AND due_at IS NOT NULL "
            "AND create_request_id IS NULL AND create_request_fingerprint IS NULL))",
            name="ck_tasks_source_matrix",
        ),
        CheckConstraint(
            "((status = 'open' AND completed_at IS NULL "
            "AND completed_by_account_id IS NULL "
            "AND completed_by_membership_id IS NULL "
            "AND completed_by_role_preset IS NULL "
            "AND completion_request_id IS NULL "
            "AND completion_request_fingerprint IS NULL "
            "AND completed_event_ref IS NULL) OR "
            "(status = 'completed' AND completed_at IS NOT NULL "
            "AND completed_by_account_id IS NOT NULL "
            "AND completed_by_membership_id IS NOT NULL "
            "AND completed_by_role_preset IS NOT NULL "
            "AND completion_request_id IS NOT NULL "
            "AND completion_request_fingerprint IS NOT NULL "
            "AND completed_event_ref IS NOT NULL))",
            name="ck_tasks_completion_matrix",
        ),
        CheckConstraint(
            "created_by_role_preset IN ('boss', 'engineer')",
            name="ck_tasks_created_role",
        ),
        CheckConstraint(
            "completed_by_role_preset IS NULL OR "
            "completed_by_role_preset IN ('boss', 'engineer')",
            name="ck_tasks_completed_role",
        ),
        Index("ix_tasks_plant_created", "plant_id", "created_at", "task_id"),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("farms.farm_id", ondelete="RESTRICT"), nullable=False
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("plants.plant_id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    display_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_refs: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False)
    classification_message_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("safety_classifications.message_id", ondelete="RESTRICT")
    )
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("approvals.approval_id", ondelete="RESTRICT")
    )
    parent_action_task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.task_id", ondelete="RESTRICT")
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("accounts.account_id", ondelete="RESTRICT"), nullable=False
    )
    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("farm_memberships.membership_id", ondelete="RESTRICT"), nullable=False
    )
    created_by_role_preset: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by_agent_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    create_request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    create_request_fingerprint: Mapped[str | None] = mapped_column(String(64))
    created_event_ref: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("accounts.account_id", ondelete="RESTRICT")
    )
    completed_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("farm_memberships.membership_id", ondelete="RESTRICT")
    )
    completed_by_role_preset: Mapped[str | None] = mapped_column(String(16))
    completion_request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    completion_request_fingerprint: Mapped[str | None] = mapped_column(String(64))
    completed_event_ref: Mapped[dict[str, object] | None] = mapped_column(JSON_DOCUMENT)


class Outcome(Base):
    __tablename__ = "outcomes"
    __table_args__ = (
        UniqueConstraint("follow_up_task_id", name="uq_outcomes_follow_up_task"),
        UniqueConstraint("request_id", name="uq_outcomes_request"),
        CheckConstraint(
            "value IN ('improved', 'worsened', 'unchanged', 'no_data')",
            name="ck_outcomes_value",
        ),
        CheckConstraint(
            "recorded_by_role_preset IN ('boss', 'engineer')",
            name="ck_outcomes_recorded_role",
        ),
        CheckConstraint(
            "jsonb_typeof(evidence_refs) = 'array'",
            name="ck_outcomes_evidence_refs_array",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_array_length(evidence_refs) <= 4",
            name="ck_outcomes_evidence_ref_limit",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "(value = 'no_data') OR jsonb_array_length(evidence_refs) >= 1",
            name="ck_outcomes_evidence_policy",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_outcomes_fingerprint",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(outcome_event_ref) = 'object' AND "
            "jsonb_typeof(task_completed_event_ref) = 'object'",
            name="ck_outcomes_event_refs_object",
        ).ddl_if(dialect="postgresql"),
        Index("ix_outcomes_plant_recorded", "plant_id", "recorded_at", "outcome_id"),
    )

    outcome_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    follow_up_task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.task_id", ondelete="RESTRICT"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("farms.farm_id", ondelete="RESTRICT"), nullable=False
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("plants.plant_id", ondelete="RESTRICT"), nullable=False
    )
    value: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("accounts.account_id", ondelete="RESTRICT"), nullable=False
    )
    recorded_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("farm_memberships.membership_id", ondelete="RESTRICT"), nullable=False
    )
    recorded_by_role_preset: Mapped[str] = mapped_column(String(16), nullable=False)
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome_event_ref: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    task_completed_event_ref: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)


__all__ = ["Approval", "OrdinaryTaskDispatchDisposition", "Outcome", "Task"]
