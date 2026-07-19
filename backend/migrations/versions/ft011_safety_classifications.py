"""Add FT-011 authoritative Safety classification evidence."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "ft011_safety_classifications"
down_revision: str | None = "ft009_plant_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "safety_classifications",
        sa.Column("message_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("origin_agent_id", sa.String(length=64), nullable=False),
        sa.Column("classifier_version", sa.String(length=64), nullable=False),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("safe_task_kind", sa.String(length=16), nullable=True),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("physical_action_kind", sa.String(length=32), nullable=True),
        sa.Column("provider_status", sa.String(length=16), nullable=False),
        sa.Column("model_ref", sa.String(length=193), nullable=True),
        sa.Column("input_sha256", sa.String(length=64), nullable=False),
        sa.Column("result_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "origin_agent_id ~ '^[a-z][a-z0-9_]{2,63}$'",
            name="ck_safety_classifications_origin_agent_id",
        ),
        sa.CheckConstraint(
            "classifier_version = 'safety_gate_v1'",
            name="ck_safety_classifications_classifier_version",
        ),
        sa.CheckConstraint(
            "classification IN "
            "('safe_information', 'safe_task_request', 'physical_action', "
            "'blocked_uncertain')",
            name="ck_safety_classifications_classification",
        ),
        sa.CheckConstraint(
            "safe_task_kind IS NULL OR safe_task_kind IN "
            "('check', 'measurement', 'follow_up')",
            name="ck_safety_classifications_safe_task_kind",
        ),
        sa.CheckConstraint(
            "physical_action_kind IS NULL OR physical_action_kind IN "
            "('ph_adjustment', 'ec_adjustment', 'solution_change', "
            "'pump_command', 'light_command', 'dosing_command', 'pruning', "
            "'transplanting', 'root_trimming', 'other_physical_action')",
            name="ck_safety_classifications_physical_action_kind",
        ),
        sa.CheckConstraint(
            "((classification = 'safe_information' AND safe_task_kind IS NULL "
            "AND physical_action_kind IS NULL "
            "AND reason_code = 'non_physical_information') OR "
            "(classification = 'safe_task_request' "
            "AND ((safe_task_kind = 'check' AND reason_code = 'safe_check_request') "
            "OR (safe_task_kind = 'measurement' "
            "AND reason_code = 'safe_measurement_request') "
            "OR (safe_task_kind = 'follow_up' "
            "AND reason_code = 'safe_follow_up_request')) "
            "AND physical_action_kind IS NULL) OR "
            "(classification = 'physical_action' AND safe_task_kind IS NULL "
            "AND physical_action_kind IS NOT NULL "
            "AND reason_code = 'physical_action_detected') OR "
            "(classification = 'blocked_uncertain' AND safe_task_kind IS NULL "
            "AND physical_action_kind IS NULL "
            "AND reason_code = 'classification_uncertain'))",
            name="ck_safety_classifications_result_matrix",
        ),
        sa.CheckConstraint(
            "provider_status IN ('completed', 'not_configured', 'failed', 'invalid')",
            name="ck_safety_classifications_provider_status",
        ),
        sa.CheckConstraint(
            "provider_status = 'completed' OR "
            "(classification = 'blocked_uncertain' AND safe_task_kind IS NULL "
            "AND physical_action_kind IS NULL "
            "AND reason_code = 'classification_uncertain')",
            name="ck_safety_classifications_provider_failure_closed",
        ),
        sa.CheckConstraint(
            "model_ref IS NULL OR "
            "model_ref ~ '^[a-z][a-z0-9_]{0,63}:[A-Za-z0-9._-]{1,127}$'",
            name="ck_safety_classifications_model_ref",
        ),
        sa.CheckConstraint(
            "input_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_safety_classifications_input_sha256",
        ),
        sa.CheckConstraint(
            "result_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_safety_classifications_result_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_safety_classifications_farm_id_farms",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_safety_classifications_plant_id_plants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("message_id", name="pk_safety_classifications"),
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM safety_classifications LIMIT 1)")
    ).scalar_one():
        raise RuntimeError(
            "FT-011 downgrade refused because Safety classification authority "
            "data exists; remove it only through an explicit reviewed recovery "
            "procedure."
        )
    op.drop_table("safety_classifications")
