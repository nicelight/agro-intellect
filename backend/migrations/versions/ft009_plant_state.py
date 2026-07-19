"""Add FT-009 authoritative Plant state trust records."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ft009_plant_state"
down_revision: str | None = "ft008_agent_chat_ui_feed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plant_state_records",
        sa.Column("state_record_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("record_kind", sa.String(length=32), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("message_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("observation_key", sa.String(length=64), nullable=False),
        sa.Column("polarity", sa.String(length=24), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=True),
        sa.Column("assessment_kind", sa.String(length=16), nullable=True),
        sa.Column("direction", sa.String(length=24), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column("trust_status", sa.String(length=16), nullable=False),
        sa.Column(
            "source_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmation_source", sa.String(length=32), nullable=True),
        sa.Column("confirmed_by_account_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("confirmed_by_membership_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "record_kind IN ('vision_observation', 'plant_state_assessment')",
            name="ck_plant_state_records_record_kind",
        ),
        sa.CheckConstraint(
            "((record_kind = 'vision_observation' AND agent_id = 'vision_observation' "
            "AND polarity IS NOT NULL AND severity IS NOT NULL "
            "AND assessment_kind IS NULL AND direction IS NULL) OR "
            "(record_kind = 'plant_state_assessment' AND agent_id = 'plant_state' "
            "AND polarity IS NULL AND severity IS NULL "
            "AND assessment_kind IS NOT NULL AND direction IS NOT NULL))",
            name="ck_plant_state_records_kind_fields",
        ),
        sa.CheckConstraint(
            "polarity IS NULL OR polarity IN "
            "('present', 'absent', 'uncertain', 'not_assessable')",
            name="ck_plant_state_records_polarity",
        ),
        sa.CheckConstraint(
            "severity IS NULL OR severity IN "
            "('none', 'mild', 'moderate', 'strong', 'unknown')",
            name="ck_plant_state_records_severity",
        ),
        sa.CheckConstraint(
            "((polarity = 'absent' AND severity = 'none') OR "
            "(polarity = 'present' AND severity IN ('mild', 'moderate', 'strong')) OR "
            "(polarity IN ('uncertain', 'not_assessable') AND severity = 'unknown') OR "
            "polarity IS NULL)",
            name="ck_plant_state_records_vision_shape",
        ),
        sa.CheckConstraint(
            "assessment_kind IS NULL OR assessment_kind IN ('trend', 'conflict', 'unknown')",
            name="ck_plant_state_records_assessment_kind",
        ),
        sa.CheckConstraint(
            "direction IS NULL OR direction IN "
            "('increasing', 'decreasing', 'stable', 'mixed', 'not_applicable')",
            name="ck_plant_state_records_direction",
        ),
        sa.CheckConstraint(
            "((assessment_kind = 'trend' AND direction <> 'not_applicable') OR "
            "(assessment_kind IN ('conflict', 'unknown') AND direction = 'not_applicable') OR "
            "assessment_kind IS NULL)",
            name="ck_plant_state_records_assessment_shape",
        ),
        sa.CheckConstraint(
            "trust_status IN "
            "('unknown', 'observed', 'hypothesis', 'conflicting', 'confirmed', 'rejected')",
            name="ck_plant_state_records_trust_status",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_plant_state_records_confidence",
        ),
        sa.CheckConstraint("version >= 1", name="ck_plant_state_records_version"),
        sa.CheckConstraint(
            "btrim(summary) <> '' AND char_length(summary) <= 1000",
            name="ck_plant_state_records_summary",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_refs) = 'array' AND jsonb_array_length(source_refs) "
            "BETWEEN 1 AND 4",
            name="ck_plant_state_records_source_refs",
        ),
        sa.CheckConstraint(
            "((trust_status = 'confirmed' AND confirmation_source IS NOT NULL "
            "AND confirmed_by_account_id IS NOT NULL "
            "AND confirmed_by_membership_id IS NOT NULL AND confirmed_at IS NOT NULL) OR "
            "(trust_status <> 'confirmed' AND confirmation_source IS NULL "
            "AND confirmed_by_account_id IS NULL "
            "AND confirmed_by_membership_id IS NULL AND confirmed_at IS NULL))",
            name="ck_plant_state_records_confirmation_shape",
        ),
        sa.CheckConstraint(
            "confirmation_source IS NULL OR confirmation_source IN "
            "('human_review', 'manual_measurement', 'follow_up')",
            name="ck_plant_state_records_confirmation_source",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_plant_state_records_farm_id_farms",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_plant_state_records_plant_id_plants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by_account_id"],
            ["accounts.account_id"],
            name="fk_plant_state_records_confirmed_account",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by_membership_id"],
            ["farm_memberships.membership_id"],
            name="fk_plant_state_records_confirmed_membership",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("state_record_id", name="pk_plant_state_records"),
        sa.UniqueConstraint("message_id", name="uq_plant_state_records_message_id"),
    )
    op.create_index(
        "ix_plant_state_records_plant_recorded_desc",
        "plant_state_records",
        ["plant_id", sa.text("recorded_at DESC"), sa.text("state_record_id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_plant_state_records_plant_key_recorded_desc",
        "plant_state_records",
        ["plant_id", "observation_key", sa.text("recorded_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM plant_state_records LIMIT 1)")
    ).scalar_one():
        raise RuntimeError(
            "FT-009 downgrade refused because Plant state trust authority data "
            "exists; remove it only through an explicit reviewed recovery procedure."
        )
    op.drop_index(
        "ix_plant_state_records_plant_key_recorded_desc",
        table_name="plant_state_records",
    )
    op.drop_index(
        "ix_plant_state_records_plant_recorded_desc",
        table_name="plant_state_records",
    )
    op.drop_table("plant_state_records")
