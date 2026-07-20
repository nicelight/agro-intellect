"""Add immutable FT-011 Safety decisions and inert UI projections."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "ft011_safety_action_decisions"
down_revision: str | None = "ft011_safety_classifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "safety_action_decisions",
        sa.Column("decision_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("classification_message_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_membership_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_role_preset", sa.String(length=16), nullable=False),
        sa.Column("permission_source", sa.String(length=32), nullable=False),
        sa.Column("grant_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("action_kind", sa.String(length=32), nullable=False),
        sa.Column("safety_status", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("ph_measurement_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("ec_measurement_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("ph_status", sa.String(length=16), nullable=True),
        sa.Column("ec_status", sa.String(length=16), nullable=True),
        sa.Column("ph_measured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ec_measured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "actor_role_preset IN ('boss', 'engineer', 'consultant')",
            name="ck_safety_action_decisions_actor_role",
        ),
        sa.CheckConstraint(
            "permission_source IN ('boss_role', 'plant_access_grant')",
            name="ck_safety_action_decisions_permission_source",
        ),
        sa.CheckConstraint(
            "((permission_source = 'boss_role' AND actor_role_preset = 'boss' "
            "AND grant_id IS NULL) OR "
            "(permission_source = 'plant_access_grant' "
            "AND actor_role_preset IN ('engineer', 'consultant') "
            "AND grant_id IS NOT NULL))",
            name="ck_safety_action_decisions_permission_shape",
        ),
        sa.CheckConstraint(
            "action_kind IN "
            "('ph_adjustment', 'ec_adjustment', 'solution_change', "
            "'pump_command', 'light_command', 'dosing_command', 'pruning', "
            "'transplanting', 'root_trimming', 'other_physical_action')",
            name="ck_safety_action_decisions_action_kind",
        ),
        sa.CheckConstraint(
            "safety_status IN ('safety_blocked', 'needs_fresh_evidence', "
            "'pending_human_approval')",
            name="ck_safety_action_decisions_safety_status",
        ),
        sa.CheckConstraint(
            "reason_code IN ('unsupported_action', 'approval_authority_missing', "
            "'approval_input_missing_or_stale', 'ready_for_human_approval')",
            name="ck_safety_action_decisions_reason_code",
        ),
        sa.CheckConstraint(
            "((action_kind IN "
            "('pump_command', 'light_command', 'dosing_command', 'pruning', "
            "'transplanting', 'root_trimming', 'other_physical_action') "
            "AND safety_status = 'safety_blocked' "
            "AND reason_code = 'unsupported_action') OR "
            "(action_kind IN ('ph_adjustment', 'ec_adjustment', 'solution_change') "
            "AND ((safety_status = 'safety_blocked' "
            "AND reason_code = 'approval_authority_missing') OR "
            "(safety_status = 'needs_fresh_evidence' "
            "AND reason_code = 'approval_input_missing_or_stale') OR "
            "(safety_status = 'pending_human_approval' "
            "AND reason_code = 'ready_for_human_approval'))))",
            name="ck_safety_action_decisions_route_matrix",
        ),
        sa.CheckConstraint(
            "ph_status IS NULL OR ph_status IN ('fresh', 'stale', 'missing')",
            name="ck_safety_action_decisions_ph_status",
        ),
        sa.CheckConstraint(
            "ec_status IS NULL OR ec_status IN ('fresh', 'stale', 'missing')",
            name="ck_safety_action_decisions_ec_status",
        ),
        sa.CheckConstraint(
            "((ph_status = 'missing' AND ph_measurement_id IS NULL "
            "AND ph_measured_at IS NULL) OR "
            "(ph_status IN ('fresh', 'stale') AND ph_measurement_id IS NOT NULL "
            "AND ph_measured_at IS NOT NULL) OR ph_status IS NULL)",
            name="ck_safety_action_decisions_ph_evidence_shape",
        ),
        sa.CheckConstraint(
            "((ec_status = 'missing' AND ec_measurement_id IS NULL "
            "AND ec_measured_at IS NULL) OR "
            "(ec_status IN ('fresh', 'stale') AND ec_measurement_id IS NOT NULL "
            "AND ec_measured_at IS NOT NULL) OR ec_status IS NULL)",
            name="ck_safety_action_decisions_ec_evidence_shape",
        ),
        sa.CheckConstraint(
            "((reason_code IN ('unsupported_action', 'approval_authority_missing') "
            "AND ph_status IS NULL AND ec_status IS NULL "
            "AND ph_measurement_id IS NULL AND ec_measurement_id IS NULL "
            "AND ph_measured_at IS NULL AND ec_measured_at IS NULL "
            "AND expires_at IS NULL) OR "
            "(reason_code = 'approval_input_missing_or_stale' "
            "AND ph_status IS NOT NULL AND ec_status IS NOT NULL "
            "AND (ph_status <> 'fresh' OR ec_status <> 'fresh') "
            "AND expires_at IS NULL) OR "
            "(reason_code = 'ready_for_human_approval' "
            "AND ph_status = 'fresh' AND ec_status = 'fresh' "
            "AND ph_measurement_id IS NOT NULL AND ec_measurement_id IS NOT NULL "
            "AND ph_measured_at IS NOT NULL AND ec_measured_at IS NOT NULL "
            "AND expires_at IS NOT NULL))",
            name="ck_safety_action_decisions_evidence_matrix",
        ),
        sa.CheckConstraint(
            "created_at = evaluated_at",
            name="ck_safety_action_decisions_evaluation_timestamp",
        ),
        sa.CheckConstraint(
            "((reason_code = 'unsupported_action' AND summary_text = "
            "'Действие не поддерживается безопасным процессом MVP.') OR "
            "(reason_code = 'approval_authority_missing' AND summary_text = "
            "'Действие заблокировано: у текущего пользователя нет права подтверждения.') OR "
            "(reason_code = 'approval_input_missing_or_stale' AND summary_text = "
            "'Перед предложением действия нужны свежие измерения pH и EC.') OR "
            "(reason_code = 'ready_for_human_approval' AND "
            "((action_kind = 'ph_adjustment' AND summary_text = "
            "'Предложена ручная корректировка pH. Требуется решение уполномоченного пользователя.') OR "
            "(action_kind = 'ec_adjustment' AND summary_text = "
            "'Предложена ручная корректировка EC питательного раствора. Требуется решение уполномоченного пользователя.') OR "
            "(action_kind = 'solution_change' AND summary_text = "
            "'Предложена ручная замена питательного раствора. Требуется решение уполномоченного пользователя.'))))",
            name="ck_safety_action_decisions_summary",
        ),
        sa.ForeignKeyConstraint(["classification_message_id"], ["safety_classifications.message_id"], name="fk_safety_action_decisions_classification", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.farm_id"], name="fk_safety_action_decisions_farm", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.plant_id"], name="fk_safety_action_decisions_plant", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_account_id"], ["accounts.account_id"], name="fk_safety_action_decisions_actor_account", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_membership_id"], ["farm_memberships.membership_id"], name="fk_safety_action_decisions_actor_membership", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["grant_id"], ["plant_access_grants.grant_id"], name="fk_safety_action_decisions_grant", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ph_measurement_id"], ["manual_measurements.measurement_id"], name="fk_safety_action_decisions_ph_measurement", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ec_measurement_id"], ["manual_measurements.measurement_id"], name="fk_safety_action_decisions_ec_measurement", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("decision_id", name="pk_safety_action_decisions"),
        sa.UniqueConstraint("classification_message_id", name="uq_safety_action_decisions_classification"),
    )
    op.drop_constraint(
        "ck_ui_feed_events_display_kind",
        "ui_feed_events",
        type_="check",
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
        "((source_type = 'system' AND display_kind = 'agent_introduction') OR "
        "(source_type = 'agent_message' AND display_kind = 'agent_message') OR "
        "(source_type = 'safety' "
        "AND display_kind IN ('block_notice', 'safety_status')))",
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_decisions = connection.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM safety_action_decisions LIMIT 1)")
    ).scalar_one()
    has_status_rows = connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM ui_feed_events "
            "WHERE display_kind = 'safety_status' LIMIT 1)"
        )
    ).scalar_one()
    if has_decisions or has_status_rows:
        raise RuntimeError(
            "FT-011 downgrade refused because Safety decision authority or "
            "projection data exists; remove it only through an explicit "
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
    op.create_check_constraint(
        "ck_ui_feed_events_display_kind",
        "ui_feed_events",
        "display_kind IN ('agent_introduction', 'agent_message', 'block_notice')",
    )
    op.drop_table("safety_action_decisions")
