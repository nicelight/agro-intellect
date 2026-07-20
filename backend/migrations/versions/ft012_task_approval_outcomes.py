"""Add authoritative FT-012 approvals, tasks, follow-ups, and outcomes."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ft012_task_approval_outcomes"
down_revision: str | None = "ft011_safety_action_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "approvals",
        sa.Column("approval_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("safety_decision_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("action_kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_refs", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_actor_account_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("decision_actor_membership_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("decision_actor_role_preset", sa.String(length=16), nullable=True),
        sa.Column("decision_permission_source", sa.String(length=32), nullable=True),
        sa.Column("decision_grant_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("decision_request_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("decision_request_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("decision_event_ref", JSONB, nullable=True),
        sa.CheckConstraint("action_kind IN ('ph_adjustment', 'ec_adjustment', 'solution_change')", name="ck_approvals_action_kind"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_approvals_status"),
        sa.CheckConstraint("record_version IN (1, 2)", name="ck_approvals_version"),
        sa.CheckConstraint("jsonb_typeof(source_refs) = 'array'", name="ck_approvals_source_refs_array"),
        sa.CheckConstraint("decision_event_ref IS NULL OR jsonb_typeof(decision_event_ref) = 'object'", name="ck_approvals_event_ref_object"),
        sa.CheckConstraint("decision_request_fingerprint IS NULL OR decision_request_fingerprint ~ '^[0-9a-f]{64}$'", name="ck_approvals_fingerprint"),
        sa.CheckConstraint("decision_actor_role_preset IS NULL OR decision_actor_role_preset IN ('boss', 'engineer')", name="ck_approvals_actor_role"),
        sa.CheckConstraint("decision_permission_source IS NULL OR decision_permission_source IN ('boss_role', 'plant_access_grant')", name="ck_approvals_permission_source"),
        sa.CheckConstraint(
            "((status = 'pending' AND record_version = 1 AND decided_at IS NULL "
            "AND decision_actor_account_id IS NULL AND decision_actor_membership_id IS NULL "
            "AND decision_actor_role_preset IS NULL AND decision_permission_source IS NULL "
            "AND decision_grant_id IS NULL AND decision_request_id IS NULL "
            "AND decision_request_fingerprint IS NULL AND decision_event_ref IS NULL) OR "
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
            "AND decision_actor_role_preset = 'engineer' AND decision_grant_id IS NOT NULL))))",
            name="ck_approvals_state_matrix",
        ),
        sa.ForeignKeyConstraint(["safety_decision_id"], ["safety_action_decisions.decision_id"], name="fk_approvals_safety_decision", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.farm_id"], name="fk_approvals_farm", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.plant_id"], name="fk_approvals_plant", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decision_actor_account_id"], ["accounts.account_id"], name="fk_approvals_decision_account", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decision_actor_membership_id"], ["farm_memberships.membership_id"], name="fk_approvals_decision_membership", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decision_grant_id"], ["plant_access_grants.grant_id"], name="fk_approvals_decision_grant", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("approval_id", name="pk_approvals"),
        sa.UniqueConstraint("safety_decision_id", name="uq_approvals_safety_decision"),
        sa.UniqueConstraint("decision_request_id", name="uq_approvals_decision_request"),
    )
    op.create_index("ix_approvals_plant_created", "approvals", ["plant_id", "created_at", "approval_id"])

    op.create_table(
        "tasks",
        sa.Column("task_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("display_text", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_refs", JSONB, nullable=False),
        sa.Column("classification_message_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("approval_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("parent_action_task_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_by_membership_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_by_role_preset", sa.String(length=16), nullable=False),
        sa.Column("created_by_agent_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("create_request_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("create_request_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("created_event_ref", JSONB, nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_account_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("completed_by_membership_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("completed_by_role_preset", sa.String(length=16), nullable=True),
        sa.Column("completion_request_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("completion_request_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("completed_event_ref", JSONB, nullable=True),
        sa.CheckConstraint("kind IN ('check', 'measurement', 'action', 'follow_up')", name="ck_tasks_kind"),
        sa.CheckConstraint("status IN ('open', 'completed')", name="ck_tasks_status"),
        sa.CheckConstraint("source_type IN ('safe_task_request', 'approved_action', 'automatic_follow_up')", name="ck_tasks_source_type"),
        sa.CheckConstraint("btrim(display_text) <> '' AND char_length(display_text) <= 2000", name="ck_tasks_display_text"),
        sa.CheckConstraint("jsonb_typeof(source_refs) = 'array'", name="ck_tasks_source_refs_array"),
        sa.CheckConstraint("jsonb_typeof(created_event_ref) = 'object' AND (completed_event_ref IS NULL OR jsonb_typeof(completed_event_ref) = 'object')", name="ck_tasks_event_refs_object"),
        sa.CheckConstraint("create_request_fingerprint IS NULL OR create_request_fingerprint ~ '^[0-9a-f]{64}$'", name="ck_tasks_create_fingerprint"),
        sa.CheckConstraint("completion_request_fingerprint IS NULL OR completion_request_fingerprint ~ '^[0-9a-f]{64}$'", name="ck_tasks_completion_fingerprint"),
        sa.CheckConstraint(
            "((source_type = 'safe_task_request' AND kind IN ('check', 'measurement', 'follow_up') "
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
        sa.CheckConstraint(
            "((status = 'open' AND completed_at IS NULL AND completed_by_account_id IS NULL "
            "AND completed_by_membership_id IS NULL AND completed_by_role_preset IS NULL "
            "AND completion_request_id IS NULL AND completion_request_fingerprint IS NULL "
            "AND completed_event_ref IS NULL) OR "
            "(status = 'completed' AND completed_at IS NOT NULL "
            "AND completed_by_account_id IS NOT NULL AND completed_by_membership_id IS NOT NULL "
            "AND completed_by_role_preset IS NOT NULL AND completion_request_id IS NOT NULL "
            "AND completion_request_fingerprint IS NOT NULL AND completed_event_ref IS NOT NULL))",
            name="ck_tasks_completion_matrix",
        ),
        sa.CheckConstraint("created_by_role_preset IN ('boss', 'engineer')", name="ck_tasks_created_role"),
        sa.CheckConstraint("completed_by_role_preset IS NULL OR completed_by_role_preset IN ('boss', 'engineer')", name="ck_tasks_completed_role"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.farm_id"], name="fk_tasks_farm", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.plant_id"], name="fk_tasks_plant", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["classification_message_id"], ["safety_classifications.message_id"], name="fk_tasks_classification", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approval_id"], ["approvals.approval_id"], name="fk_tasks_approval", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["parent_action_task_id"], ["tasks.task_id"], name="fk_tasks_parent_action", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_account_id"], ["accounts.account_id"], name="fk_tasks_created_account", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_membership_id"], ["farm_memberships.membership_id"], name="fk_tasks_created_membership", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["completed_by_account_id"], ["accounts.account_id"], name="fk_tasks_completed_account", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["completed_by_membership_id"], ["farm_memberships.membership_id"], name="fk_tasks_completed_membership", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("task_id", name="pk_tasks"),
        sa.UniqueConstraint("classification_message_id", name="uq_tasks_classification_message"),
        sa.UniqueConstraint("approval_id", name="uq_tasks_approval"),
        sa.UniqueConstraint("parent_action_task_id", name="uq_tasks_parent_action"),
        sa.UniqueConstraint("create_request_id", name="uq_tasks_create_request"),
        sa.UniqueConstraint("completion_request_id", name="uq_tasks_completion_request"),
    )
    op.create_index("ix_tasks_plant_created", "tasks", ["plant_id", "created_at", "task_id"])

    op.create_table(
        "outcomes",
        sa.Column("outcome_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("follow_up_task_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("value", sa.String(length=16), nullable=False),
        sa.Column("evidence_refs", JSONB, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by_account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("recorded_by_membership_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("recorded_by_role_preset", sa.String(length=16), nullable=False),
        sa.Column("request_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("outcome_event_ref", JSONB, nullable=False),
        sa.Column("task_completed_event_ref", JSONB, nullable=False),
        sa.CheckConstraint("value IN ('improved', 'worsened', 'unchanged', 'no_data')", name="ck_outcomes_value"),
        sa.CheckConstraint("jsonb_typeof(evidence_refs) = 'array'", name="ck_outcomes_evidence_refs_array"),
        sa.CheckConstraint("jsonb_array_length(evidence_refs) <= 4", name="ck_outcomes_evidence_ref_limit"),
        sa.CheckConstraint("(value = 'no_data') OR jsonb_array_length(evidence_refs) >= 1", name="ck_outcomes_evidence_policy"),
        sa.CheckConstraint("request_fingerprint ~ '^[0-9a-f]{64}$'", name="ck_outcomes_fingerprint"),
        sa.CheckConstraint("jsonb_typeof(outcome_event_ref) = 'object' AND jsonb_typeof(task_completed_event_ref) = 'object'", name="ck_outcomes_event_refs_object"),
        sa.CheckConstraint("recorded_by_role_preset IN ('boss', 'engineer')", name="ck_outcomes_recorded_role"),
        sa.ForeignKeyConstraint(["follow_up_task_id"], ["tasks.task_id"], name="fk_outcomes_follow_up_task", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.farm_id"], name="fk_outcomes_farm", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.plant_id"], name="fk_outcomes_plant", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by_account_id"], ["accounts.account_id"], name="fk_outcomes_recorded_account", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by_membership_id"], ["farm_memberships.membership_id"], name="fk_outcomes_recorded_membership", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("outcome_id", name="pk_outcomes"),
        sa.UniqueConstraint("follow_up_task_id", name="uq_outcomes_follow_up_task"),
        sa.UniqueConstraint("request_id", name="uq_outcomes_request"),
    )
    op.create_index("ix_outcomes_plant_recorded", "outcomes", ["plant_id", "recorded_at", "outcome_id"])


def downgrade() -> None:
    connection = op.get_bind()
    populated = connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM approvals LIMIT 1) OR "
            "EXISTS (SELECT 1 FROM tasks LIMIT 1) OR "
            "EXISTS (SELECT 1 FROM outcomes LIMIT 1)"
        )
    ).scalar_one()
    if populated:
        raise RuntimeError(
            "FT-012 downgrade refused because Approval, Task, or Outcome authority exists; "
            "remove it only through an explicit reviewed recovery procedure."
        )
    op.drop_table("outcomes")
    op.drop_table("tasks")
    op.drop_table("approvals")
