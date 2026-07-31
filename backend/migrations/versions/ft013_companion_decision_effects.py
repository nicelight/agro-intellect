"""Add binding Companion DecisionRecord Task and Bus effects."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "ft013_decision_effects"
down_revision: str | None = "ft008_lazy_introductions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TASK_SOURCE_MATRIX = (
    "((source_type = 'safe_task_request' "
    "AND kind IN ('check', 'measurement', 'follow_up') "
    "AND classification_message_id IS NOT NULL AND approval_id IS NULL "
    "AND parent_action_task_id IS NULL AND decision_record_id IS NULL "
    "AND create_request_id IS NOT NULL "
    "AND create_request_fingerprint IS NOT NULL) OR "
    "(source_type = 'approved_action' AND kind = 'action' "
    "AND classification_message_id IS NULL AND approval_id IS NOT NULL "
    "AND parent_action_task_id IS NULL AND decision_record_id IS NULL "
    "AND create_request_id IS NULL AND create_request_fingerprint IS NULL) OR "
    "(source_type = 'automatic_follow_up' AND kind = 'follow_up' "
    "AND classification_message_id IS NULL AND approval_id IS NULL "
    "AND parent_action_task_id IS NOT NULL AND due_at IS NOT NULL "
    "AND decision_record_id IS NULL "
    "AND create_request_id IS NULL AND create_request_fingerprint IS NULL) OR "
    "(source_type = 'governance_decision' "
    "AND kind IN ('check', 'measurement', 'follow_up') "
    "AND classification_message_id IS NULL AND approval_id IS NULL "
    "AND parent_action_task_id IS NULL AND due_at IS NULL "
    "AND decision_record_id IS NOT NULL "
    "AND create_request_id IS NOT NULL "
    "AND create_request_fingerprint IS NOT NULL))"
)
_TASK_SOURCE_MATRIX_OLD = (
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
    "AND create_request_id IS NULL AND create_request_fingerprint IS NULL))"
)


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("decision_record_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_tasks_decision_record",
        "tasks",
        "decision_records",
        ["decision_record_id"],
        ["decision_record_id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_tasks_decision_record",
        "tasks",
        ["decision_record_id"],
    )
    op.drop_constraint("ck_tasks_source_type", "tasks", type_="check")
    op.drop_constraint("ck_tasks_source_matrix", "tasks", type_="check")
    op.create_check_constraint(
        "ck_tasks_source_type",
        "tasks",
        "source_type IN ('safe_task_request', 'approved_action', "
        "'automatic_follow_up', 'governance_decision')",
    )
    op.create_check_constraint(
        "ck_tasks_source_matrix",
        "tasks",
        _TASK_SOURCE_MATRIX,
    )

    op.drop_constraint(
        "ck_agent_bus_events_authorization_scope_object",
        "agent_bus_events",
        type_="check",
    )
    op.alter_column(
        "agent_bus_events",
        "authorization_scope",
        existing_type=sa.JSON(),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_agent_bus_events_authorization_scope_object",
        "agent_bus_events",
        "jsonb_typeof(authorization_scope) = 'object' "
        "OR authorization_scope IS NULL",
    )
    op.create_check_constraint(
        "ck_agent_bus_events_authority_matrix",
        "agent_bus_events",
        "((source_type = 'domain_record' AND actor_ref IS NULL "
        "AND authorization_scope IS NULL) OR "
        "(source_type = 'message_envelope' AND actor_ref IS NOT NULL "
        "AND authorization_scope IS NOT NULL))",
    )


def downgrade() -> None:
    connection = op.get_bind()
    populated = connection.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM tasks WHERE decision_record_id IS NOT NULL"
            ") OR EXISTS ("
            "SELECT 1 FROM agent_bus_events "
            "WHERE authorization_scope IS NULL"
            ")"
        )
    ).scalar_one()
    if populated:
        raise RuntimeError(
            "FT-013 decision-effect downgrade refused while governance "
            "Task or backend domain-adapter Bus authority exists."
        )
    op.drop_constraint(
        "ck_agent_bus_events_authority_matrix",
        "agent_bus_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_agent_bus_events_authorization_scope_object",
        "agent_bus_events",
        type_="check",
    )
    op.alter_column(
        "agent_bus_events",
        "authorization_scope",
        existing_type=sa.JSON(),
        nullable=False,
    )
    op.create_check_constraint(
        "ck_agent_bus_events_authorization_scope_object",
        "agent_bus_events",
        "jsonb_typeof(authorization_scope) = 'object'",
    )

    op.drop_constraint("ck_tasks_source_matrix", "tasks", type_="check")
    op.drop_constraint("ck_tasks_source_type", "tasks", type_="check")
    op.create_check_constraint(
        "ck_tasks_source_type",
        "tasks",
        "source_type IN ('safe_task_request', 'approved_action', "
        "'automatic_follow_up')",
    )
    op.create_check_constraint(
        "ck_tasks_source_matrix",
        "tasks",
        _TASK_SOURCE_MATRIX_OLD,
    )
    op.drop_constraint("uq_tasks_decision_record", "tasks", type_="unique")
    op.drop_constraint("fk_tasks_decision_record", "tasks", type_="foreignkey")
    op.drop_column("tasks", "decision_record_id")
