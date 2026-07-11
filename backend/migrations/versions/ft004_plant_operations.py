"""Add FT-004 Plant operations check-ins and measurements."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ft004_plant_operations"
down_revision: str | None = "ft002_farm_plant_access"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_checkins",
        sa.Column("check_in_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_membership_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("check_in_state", sa.String(length=16), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation_state", sa.String(length=32), nullable=False),
        sa.Column("observation_text", sa.Text(), nullable=True),
        sa.Column(
            "source_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "event_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "check_in_state IN ('completed')",
            name="ck_daily_checkins_check_in_state",
        ),
        sa.CheckConstraint(
            "observation_state IN ('observed', 'no_observation_provided')",
            name="ck_daily_checkins_observation_state",
        ),
        sa.CheckConstraint(
            "((observation_state = 'observed' AND observation_text IS NOT NULL "
            "AND btrim(observation_text) <> '') OR "
            "(observation_state = 'no_observation_provided' "
            "AND observation_text IS NULL))",
            name="ck_daily_checkins_observation_text_shape",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_refs) = 'object'",
            name="ck_daily_checkins_source_refs_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(event_refs) = 'object'",
            name="ck_daily_checkins_event_refs_object",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_daily_checkins_farm_id_farms",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_daily_checkins_plant_id_plants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_account_id"],
            ["accounts.account_id"],
            name="fk_daily_checkins_actor_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_membership_id"],
            ["farm_memberships.membership_id"],
            name="fk_daily_checkins_actor_membership_id_farm_memberships",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("check_in_id", name="pk_daily_checkins"),
    )
    op.create_index(
        "ix_daily_checkins_plant_recorded_desc",
        "daily_checkins",
        ["plant_id", sa.text("recorded_at DESC"), sa.text("check_in_id DESC")],
        unique=False,
    )

    op.create_table(
        "manual_measurements",
        sa.Column("measurement_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("check_in_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("actor_account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_membership_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ph", sa.Numeric(4, 2), nullable=True),
        sa.Column("ec_ms_cm", sa.Numeric(10, 3), nullable=True),
        sa.Column("provenance_note", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column(
            "source_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("trust_status", sa.String(length=32), nullable=False),
        sa.Column(
            "event_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_type IN ('manual_user')",
            name="ck_manual_measurements_source_type",
        ),
        sa.CheckConstraint(
            "trust_status IN ('confirmed')",
            name="ck_manual_measurements_trust_status",
        ),
        sa.CheckConstraint(
            "ph IS NOT NULL OR ec_ms_cm IS NOT NULL",
            name="ck_manual_measurements_value_required",
        ),
        sa.CheckConstraint(
            "ph IS NULL OR (ph >= 0 AND ph <= 14)",
            name="ck_manual_measurements_ph_range",
        ),
        sa.CheckConstraint(
            "ec_ms_cm IS NULL OR ec_ms_cm >= 0",
            name="ck_manual_measurements_ec_non_negative",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_refs) = 'object'",
            name="ck_manual_measurements_source_refs_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(event_refs) = 'object'",
            name="ck_manual_measurements_event_refs_object",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_manual_measurements_farm_id_farms",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_manual_measurements_plant_id_plants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["check_in_id"],
            ["daily_checkins.check_in_id"],
            name="fk_manual_measurements_check_in_id_daily_checkins",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_account_id"],
            ["accounts.account_id"],
            name="fk_manual_measurements_actor_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_membership_id"],
            ["farm_memberships.membership_id"],
            name="fk_manual_measurements_actor_membership_id_farm_memberships",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("measurement_id", name="pk_manual_measurements"),
    )
    op.create_index(
        "ix_manual_measurements_plant_measured_desc",
        "manual_measurements",
        [
            "plant_id",
            sa.text("measured_at DESC"),
            sa.text("recorded_at DESC"),
            sa.text("measurement_id DESC"),
        ],
        unique=False,
    )
    op.create_index(
        "ix_manual_measurements_check_in_id",
        "manual_measurements",
        ["check_in_id"],
        unique=False,
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_check_ins = connection.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM daily_checkins LIMIT 1)")
    ).scalar_one()
    has_measurements = connection.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM manual_measurements LIMIT 1)")
    ).scalar_one()
    if has_check_ins or has_measurements:
        raise RuntimeError(
            "FT-004 downgrade refused because Plant operations authority data "
            "exists; remove it only through an explicit reviewed recovery "
            "procedure."
        )
    op.drop_index(
        "ix_manual_measurements_check_in_id", table_name="manual_measurements"
    )
    op.drop_index(
        "ix_manual_measurements_plant_measured_desc",
        table_name="manual_measurements",
    )
    op.drop_table("manual_measurements")
    op.drop_index(
        "ix_daily_checkins_plant_recorded_desc", table_name="daily_checkins"
    )
    op.drop_table("daily_checkins")
