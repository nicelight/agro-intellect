"""Add the retained FT-013 Companion governance aggregate."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ft013_governance_aggregate"
down_revision: str | None = "ft012_runtime_dispositions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "companion_issues",
        sa.Column("issue_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("is_focused", sa.Boolean(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("created_by_run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_request_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "close_request_fingerprint",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column("opened_event_ref", JSONB, nullable=False),
        sa.Column("resolved_event_ref", JSONB, nullable=True),
        sa.Column("closed_event_ref", JSONB, nullable=True),
        sa.CheckConstraint(
            "status IN ('open', 'resolved', 'closed')",
            name="ck_companion_issues_status",
        ),
        sa.CheckConstraint(
            "btrim(summary_text) <> '' AND char_length(summary_text) <= 500",
            name="ck_companion_issues_summary",
        ),
        sa.CheckConstraint(
            "record_version > 0",
            name="ck_companion_issues_record_version",
        ),
        sa.CheckConstraint(
            "close_request_fingerprint IS NULL OR "
            "close_request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_companion_issues_close_fingerprint",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(opened_event_ref) = 'object' AND "
            "(resolved_event_ref IS NULL OR "
            "jsonb_typeof(resolved_event_ref) = 'object') AND "
            "(closed_event_ref IS NULL OR "
            "jsonb_typeof(closed_event_ref) = 'object')",
            name="ck_companion_issues_event_refs",
        ),
        sa.CheckConstraint(
            "((status = 'open' AND resolved_at IS NULL AND closed_at IS NULL "
            "AND close_request_id IS NULL "
            "AND close_request_fingerprint IS NULL "
            "AND resolved_event_ref IS NULL AND closed_event_ref IS NULL) OR "
            "(status = 'resolved' AND is_focused IS FALSE "
            "AND resolved_at IS NOT NULL AND closed_at IS NULL "
            "AND close_request_id IS NULL "
            "AND close_request_fingerprint IS NULL "
            "AND resolved_event_ref IS NOT NULL "
            "AND closed_event_ref IS NULL) OR "
            "(status = 'closed' AND is_focused IS FALSE "
            "AND resolved_at IS NOT NULL AND closed_at IS NOT NULL "
            "AND close_request_id IS NOT NULL "
            "AND close_request_fingerprint IS NOT NULL "
            "AND resolved_event_ref IS NOT NULL "
            "AND closed_event_ref IS NOT NULL))",
            name="ck_companion_issues_state_matrix",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_companion_issues_farm",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_companion_issues_plant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("issue_id", name="pk_companion_issues"),
        sa.UniqueConstraint(
            "created_by_run_id",
            name="uq_companion_issues_created_by_run",
        ),
    )
    op.create_index(
        "uq_companion_issues_one_focused_per_plant",
        "companion_issues",
        ["plant_id"],
        unique=True,
        postgresql_where=sa.text("is_focused IS TRUE"),
    )
    op.create_index(
        "ix_companion_issues_plant_order",
        "companion_issues",
        ["plant_id", "status", "created_at", "issue_id"],
        unique=False,
    )

    op.create_table(
        "companion_human_attention",
        sa.Column("attention_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("issue_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("attention_sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("current_proposal_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("satisfied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "satisfied_by_decision_record_id",
            sa.Uuid(as_uuid=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "attention_sequence > 0",
            name="ck_companion_attention_sequence",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'satisfied')",
            name="ck_companion_attention_status",
        ),
        sa.CheckConstraint(
            "btrim(summary_text) <> '' AND char_length(summary_text) <= 500",
            name="ck_companion_attention_summary",
        ),
        sa.CheckConstraint(
            "record_version > 0",
            name="ck_companion_attention_record_version",
        ),
        sa.CheckConstraint(
            "((status = 'active' AND satisfied_at IS NULL "
            "AND satisfied_by_decision_record_id IS NULL) OR "
            "(status = 'satisfied' AND satisfied_at IS NOT NULL "
            "AND satisfied_by_decision_record_id IS NOT NULL))",
            name="ck_companion_attention_state_matrix",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_companion_attention_farm",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_companion_attention_plant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["companion_issues.issue_id"],
            name="fk_companion_attention_issue",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "attention_id",
            name="pk_companion_human_attention",
        ),
        sa.UniqueConstraint(
            "issue_id",
            "attention_sequence",
            name="uq_companion_attention_issue_sequence",
        ),
    )
    op.create_index(
        "uq_companion_attention_one_active_per_issue",
        "companion_human_attention",
        ["issue_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "companion_proposals",
        sa.Column("proposal_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("issue_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("attention_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("proposal_sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("proposal_summary", sa.Text(), nullable=False),
        sa.Column("proposal_text", sa.Text(), nullable=False),
        sa.Column("rationale_text", sa.Text(), nullable=True),
        sa.Column("proposed_effect", sa.String(length=24), nullable=False),
        sa.Column("task_display_text", sa.Text(), nullable=True),
        sa.Column("suggested_resolution", sa.String(length=16), nullable=False),
        sa.Column("source_run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_message_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "source_classification_message_id",
            sa.Uuid(as_uuid=True),
            nullable=False,
        ),
        sa.Column("source_refs", JSONB, nullable=False),
        sa.Column(
            "run_request_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_record_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("created_event_ref", JSONB, nullable=False),
        sa.Column("superseded_event_ref", JSONB, nullable=True),
        sa.CheckConstraint(
            "proposal_sequence > 0",
            name="ck_companion_proposals_sequence",
        ),
        sa.CheckConstraint(
            "state IN ('pending', 'approved', 'rejected', 'superseded')",
            name="ck_companion_proposals_state",
        ),
        sa.CheckConstraint(
            "record_version IN (1, 2)",
            name="ck_companion_proposals_record_version",
        ),
        sa.CheckConstraint(
            "btrim(proposal_summary) <> '' "
            "AND char_length(proposal_summary) <= 500 "
            "AND btrim(proposal_text) <> '' "
            "AND char_length(proposal_text) <= 2000 "
            "AND (rationale_text IS NULL OR "
            "(btrim(rationale_text) <> '' "
            "AND char_length(rationale_text) <= 2000))",
            name="ck_companion_proposals_text",
        ),
        sa.CheckConstraint(
            "proposed_effect IN "
            "('discussion_only', 'check', 'measurement', 'follow_up', 'none')",
            name="ck_companion_proposals_effect",
        ),
        sa.CheckConstraint(
            "((proposed_effect IN ('check', 'measurement', 'follow_up') "
            "AND task_display_text IS NOT NULL "
            "AND btrim(task_display_text) <> '' "
            "AND char_length(task_display_text) <= 2000) OR "
            "(proposed_effect IN ('discussion_only', 'none') "
            "AND task_display_text IS NULL))",
            name="ck_companion_proposals_task_text",
        ),
        sa.CheckConstraint(
            "suggested_resolution IN ('keep_open', 'resolved')",
            name="ck_companion_proposals_resolution",
        ),
        sa.CheckConstraint(
            "source_message_id = source_classification_message_id",
            name="ck_companion_proposals_message_classification_identity",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_refs) = 'array' "
            "AND jsonb_array_length(source_refs) BETWEEN 3 AND 6",
            name="ck_companion_proposals_source_refs",
        ),
        sa.CheckConstraint(
            "run_request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_companion_proposals_run_fingerprint",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(created_event_ref) = 'object' AND "
            "(superseded_event_ref IS NULL OR "
            "jsonb_typeof(superseded_event_ref) = 'object')",
            name="ck_companion_proposals_event_refs",
        ),
        sa.CheckConstraint(
            "((state = 'pending' AND record_version = 1 "
            "AND terminal_at IS NULL AND decision_record_id IS NULL "
            "AND superseded_event_ref IS NULL) OR "
            "(state IN ('approved', 'rejected') AND record_version = 2 "
            "AND terminal_at IS NOT NULL AND decision_record_id IS NOT NULL "
            "AND superseded_event_ref IS NULL) OR "
            "(state = 'superseded' AND record_version = 2 "
            "AND terminal_at IS NOT NULL AND decision_record_id IS NULL "
            "AND superseded_event_ref IS NOT NULL))",
            name="ck_companion_proposals_state_matrix",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_companion_proposals_farm",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_companion_proposals_plant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["companion_issues.issue_id"],
            name="fk_companion_proposals_issue",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["attention_id"],
            ["companion_human_attention.attention_id"],
            name="fk_companion_proposals_attention",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["source_classification_message_id"],
            ["safety_classifications.message_id"],
            name="fk_companion_proposals_source_classification",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("proposal_id", name="pk_companion_proposals"),
        sa.UniqueConstraint(
            "issue_id",
            "proposal_sequence",
            name="uq_companion_proposals_issue_sequence",
        ),
        sa.UniqueConstraint(
            "source_run_id",
            name="uq_companion_proposals_source_run",
        ),
        sa.UniqueConstraint(
            "source_message_id",
            name="uq_companion_proposals_source_message",
        ),
        sa.UniqueConstraint(
            "source_classification_message_id",
            name="uq_companion_proposals_source_classification",
        ),
    )
    op.create_index(
        "uq_companion_proposals_one_pending_per_issue",
        "companion_proposals",
        ["issue_id"],
        unique=True,
        postgresql_where=sa.text("state = 'pending'"),
    )

    op.create_table(
        "decision_records",
        sa.Column("decision_record_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("issue_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("proposal_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("attention_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("decision_summary", sa.Text(), nullable=False),
        sa.Column(
            "allowed_workflow_effect",
            sa.String(length=24),
            nullable=False,
        ),
        sa.Column("issue_resolution", sa.String(length=16), nullable=False),
        sa.Column("workflow_effect_ref", sa.Text(), nullable=True),
        sa.Column("decider_account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "decider_membership_id",
            sa.Uuid(as_uuid=True),
            nullable=False,
        ),
        sa.Column("decider_role_preset", sa.String(length=16), nullable=False),
        sa.Column(
            "decider_permission_source",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column("decider_grant_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_refs", JSONB, nullable=False),
        sa.Column("decision_event_ref", JSONB, nullable=False),
        sa.Column(
            "safety_gate_authority",
            sa.String(length=16),
            nullable=False,
            server_default="not_granted",
        ),
        sa.CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_decision_records_decision",
        ),
        sa.CheckConstraint(
            "btrim(decision_summary) <> '' "
            "AND char_length(decision_summary) <= 500",
            name="ck_decision_records_summary",
        ),
        sa.CheckConstraint(
            "allowed_workflow_effect IN "
            "('discussion_only', 'check', 'measurement', 'follow_up', 'none')",
            name="ck_decision_records_effect",
        ),
        sa.CheckConstraint(
            "issue_resolution IN ('keep_open', 'resolved')",
            name="ck_decision_records_resolution",
        ),
        sa.CheckConstraint(
            "workflow_effect_ref IS NULL OR workflow_effect_ref ~ "
            "'^task:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
            "[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="ck_decision_records_workflow_effect_ref",
        ),
        sa.CheckConstraint(
            "((decision = 'approved' "
            "AND ((allowed_workflow_effect IN "
            "('check', 'measurement', 'follow_up') "
            "AND workflow_effect_ref IS NOT NULL) OR "
            "(allowed_workflow_effect IN ('discussion_only', 'none') "
            "AND workflow_effect_ref IS NULL))) OR "
            "(decision = 'rejected' AND allowed_workflow_effect = 'none' "
            "AND workflow_effect_ref IS NULL))",
            name="ck_decision_records_effect_matrix",
        ),
        sa.CheckConstraint(
            "decider_role_preset IN ('boss', 'engineer')",
            name="ck_decision_records_role",
        ),
        sa.CheckConstraint(
            "decider_permission_source IN "
            "('boss_role', 'plant_access_grant')",
            name="ck_decision_records_permission_source",
        ),
        sa.CheckConstraint(
            "((decider_permission_source = 'boss_role' "
            "AND decider_role_preset = 'boss' "
            "AND decider_grant_id IS NULL) OR "
            "(decider_permission_source = 'plant_access_grant' "
            "AND decider_role_preset = 'engineer' "
            "AND decider_grant_id IS NOT NULL))",
            name="ck_decision_records_permission_matrix",
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_decision_records_request_fingerprint",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_refs) = 'array' "
            "AND jsonb_array_length(source_refs) BETWEEN 5 AND 7",
            name="ck_decision_records_source_refs",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(decision_event_ref) = 'object'",
            name="ck_decision_records_event_ref",
        ),
        sa.CheckConstraint(
            "safety_gate_authority = 'not_granted'",
            name="ck_decision_records_no_safety_authority",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_decision_records_farm",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_decision_records_plant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["companion_issues.issue_id"],
            name="fk_decision_records_issue",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["companion_proposals.proposal_id"],
            name="fk_decision_records_proposal",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["attention_id"],
            ["companion_human_attention.attention_id"],
            name="fk_decision_records_attention",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["decider_account_id"],
            ["accounts.account_id"],
            name="fk_decision_records_account",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["decider_membership_id"],
            ["farm_memberships.membership_id"],
            name="fk_decision_records_membership",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["decider_grant_id"],
            ["plant_access_grants.grant_id"],
            name="fk_decision_records_grant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "decision_record_id",
            name="pk_decision_records",
        ),
        sa.UniqueConstraint(
            "proposal_id",
            name="uq_decision_records_proposal",
        ),
        sa.UniqueConstraint(
            "request_id",
            name="uq_decision_records_request",
        ),
    )

    op.create_foreign_key(
        "fk_companion_attention_current_proposal",
        "companion_human_attention",
        "companion_proposals",
        ["current_proposal_id"],
        ["proposal_id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_foreign_key(
        "fk_companion_attention_satisfied_decision",
        "companion_human_attention",
        "decision_records",
        ["satisfied_by_decision_record_id"],
        ["decision_record_id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_foreign_key(
        "fk_companion_proposals_decision",
        "companion_proposals",
        "decision_records",
        ["decision_record_id"],
        ["decision_record_id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )

    op.drop_constraint(
        "ck_ui_feed_events_source_display",
        "ui_feed_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_ui_feed_events_display_kind",
        "ui_feed_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_ui_feed_events_source_type",
        "ui_feed_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_ui_feed_events_source_type",
        "ui_feed_events",
        "source_type IN "
        "('system', 'agent_message', 'safety', 'companion_governance')",
    )
    op.create_check_constraint(
        "ck_ui_feed_events_display_kind",
        "ui_feed_events",
        "display_kind IN "
        "('agent_introduction', 'agent_message', 'block_notice', "
        "'safety_status', 'companion_governance')",
    )
    op.create_check_constraint(
        "ck_ui_feed_events_source_display",
        "ui_feed_events",
        "((source_type = 'system' "
        "AND display_kind = 'agent_introduction') OR "
        "(source_type = 'agent_message' "
        "AND display_kind = 'agent_message') OR "
        "(source_type = 'safety' "
        "AND display_kind IN ('block_notice', 'safety_status')) OR "
        "(source_type = 'companion_governance' "
        "AND display_kind = 'companion_governance'))",
    )


def downgrade() -> None:
    connection = op.get_bind()
    populated = connection.execute(
        sa.text(
            "SELECT "
            "EXISTS (SELECT 1 FROM companion_issues LIMIT 1) OR "
            "EXISTS (SELECT 1 FROM companion_human_attention LIMIT 1) OR "
            "EXISTS (SELECT 1 FROM companion_proposals LIMIT 1) OR "
            "EXISTS (SELECT 1 FROM decision_records LIMIT 1) OR "
            "EXISTS (SELECT 1 FROM ui_feed_events "
            "WHERE source_type = 'companion_governance' "
            "OR display_kind = 'companion_governance' LIMIT 1)"
        )
    ).scalar_one()
    if populated:
        raise RuntimeError(
            "FT-013 downgrade refused because Companion governance authority "
            "or projections exist; remove them only through an explicit "
            "reviewed recovery procedure."
        )

    op.drop_constraint(
        "ck_ui_feed_events_source_display",
        "ui_feed_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_ui_feed_events_display_kind",
        "ui_feed_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_ui_feed_events_source_type",
        "ui_feed_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_ui_feed_events_source_type",
        "ui_feed_events",
        "source_type IN ('system', 'agent_message', 'safety')",
    )
    op.create_check_constraint(
        "ck_ui_feed_events_display_kind",
        "ui_feed_events",
        "display_kind IN ('agent_introduction', 'agent_message', "
        "'block_notice', 'safety_status')",
    )
    op.create_check_constraint(
        "ck_ui_feed_events_source_display",
        "ui_feed_events",
        "((source_type = 'system' "
        "AND display_kind = 'agent_introduction') OR "
        "(source_type = 'agent_message' "
        "AND display_kind = 'agent_message') OR "
        "(source_type = 'safety' "
        "AND display_kind IN ('block_notice', 'safety_status')))",
    )

    op.drop_constraint(
        "fk_companion_proposals_decision",
        "companion_proposals",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_companion_attention_satisfied_decision",
        "companion_human_attention",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_companion_attention_current_proposal",
        "companion_human_attention",
        type_="foreignkey",
    )
    op.drop_table("decision_records")
    op.drop_table("companion_proposals")
    op.drop_table("companion_human_attention")
    op.drop_table("companion_issues")
