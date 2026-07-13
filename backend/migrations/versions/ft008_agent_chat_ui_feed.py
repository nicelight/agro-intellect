"""Add FT-008 Agent Chat Bus and UI Feed persistence."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ft008_agent_chat_ui_feed"
down_revision: str | None = "ft005_photo_intake"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_introduction_batches",
        sa.Column("batch_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("roster_version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "roster_version > 0",
            name="ck_agent_introduction_batches_roster_version_positive",
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_agent_introduction_batches_content_sha256_lower_hex",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_agent_introduction_batches_farm_id_farms",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_agent_introduction_batches_plant_id_plants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("batch_id", name="pk_agent_introduction_batches"),
        sa.UniqueConstraint(
            "plant_id",
            "roster_version",
            name="uq_agent_introduction_batches_plant_roster",
        ),
    )

    op.create_table(
        "ui_feed_events",
        sa.Column("ui_event_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column(
            "source_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("display_kind", sa.String(length=32), nullable=False),
        sa.Column(
            "display_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "visible_to_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "visible_to_agents",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "consumable_by_agents",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("roster_version", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "source_type IN ('system', 'agent_message', 'safety')",
            name="ck_ui_feed_events_source_type",
        ),
        sa.CheckConstraint(
            "display_kind IN ('agent_introduction', 'agent_message', 'block_notice')",
            name="ck_ui_feed_events_display_kind",
        ),
        sa.CheckConstraint(
            "visible_to_agents IS FALSE",
            name="ck_ui_feed_events_visible_to_agents_false",
        ),
        sa.CheckConstraint(
            "consumable_by_agents IS FALSE",
            name="ck_ui_feed_events_consumable_by_agents_false",
        ),
        sa.CheckConstraint(
            "((display_kind = 'agent_introduction' AND agent_id IS NOT NULL "
            "AND roster_version IS NOT NULL AND roster_version > 0) OR "
            "(display_kind <> 'agent_introduction' AND agent_id IS NULL "
            "AND roster_version IS NULL))",
            name="ck_ui_feed_events_introduction_shape",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_refs) = 'array'",
            name="ck_ui_feed_events_source_refs_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(display_payload) = 'object'",
            name="ck_ui_feed_events_display_payload_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(visible_to_roles) = 'array'",
            name="ck_ui_feed_events_visible_to_roles_array",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_ui_feed_events_farm_id_farms",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_ui_feed_events_plant_id_plants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("ui_event_id", name="pk_ui_feed_events"),
        sa.UniqueConstraint(
            "plant_id",
            "agent_id",
            "roster_version",
            name="uq_ui_feed_events_plant_agent_roster",
        ),
    )
    op.create_index(
        "ix_ui_feed_events_plant_created",
        "ui_feed_events",
        ["plant_id", sa.text("created_at DESC"), sa.text("ui_event_id DESC")],
        unique=False,
    )

    op.create_table(
        "agent_bus_events",
        sa.Column("event_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("actor_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "authorization_scope",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "consumable_by_agents",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "consumable_by_agents IS TRUE",
            name="ck_agent_bus_events_consumable_by_agents_true",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(actor_ref) = 'object' OR actor_ref IS NULL",
            name="ck_agent_bus_events_actor_ref_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_agent_bus_events_payload_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_refs) = 'array'",
            name="ck_agent_bus_events_source_refs_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(authorization_scope) = 'object'",
            name="ck_agent_bus_events_authorization_scope_object",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_agent_bus_events_farm_id_farms",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_agent_bus_events_plant_id_plants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("event_id", name="pk_agent_bus_events"),
        sa.UniqueConstraint(
            "plant_id",
            "source_type",
            "source_id",
            "event_type",
            name="uq_agent_bus_events_source_event",
        ),
    )
    op.create_index(
        "ix_agent_bus_events_plant_created",
        "agent_bus_events",
        ["plant_id", sa.text("created_at DESC"), sa.text("event_id DESC")],
        unique=False,
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_data = connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM agent_introduction_batches LIMIT 1) "
            "OR EXISTS (SELECT 1 FROM ui_feed_events LIMIT 1) "
            "OR EXISTS (SELECT 1 FROM agent_bus_events LIMIT 1)"
        )
    ).scalar_one()
    if has_data:
        raise RuntimeError(
            "FT-008 downgrade refused because Agent Chat/UI Feed authority data "
            "exists; remove it only through an explicit reviewed recovery procedure."
        )
    op.drop_index("ix_agent_bus_events_plant_created", table_name="agent_bus_events")
    op.drop_table("agent_bus_events")
    op.drop_index("ix_ui_feed_events_plant_created", table_name="ui_feed_events")
    op.drop_table("ui_feed_events")
    op.drop_table("agent_introduction_batches")
