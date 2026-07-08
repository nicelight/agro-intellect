"""Add FT-002 Farm, Plant, access-grant, and admin-audit authority."""

from __future__ import annotations

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ft002_farm_plant_access"
down_revision: str | None = "ft001_access_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _legacy_farm_ids(connection: sa.Connection) -> list[uuid.UUID]:
    return list(
        connection.execute(
            sa.text(
                "SELECT DISTINCT farm_id FROM farm_memberships "
                "WHERE farm_id IS NOT NULL ORDER BY farm_id"
            )
        ).scalars()
    )


def upgrade() -> None:
    connection = op.get_bind()
    legacy_farm_ids = _legacy_farm_ids(connection)
    if len(legacy_farm_ids) > 1:
        raise RuntimeError(
            "FT-002 migration found multiple legacy Farm identities; "
            "repair them manually before retrying."
        )

    op.create_table(
        "farms",
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_key", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
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
        sa.CheckConstraint("farm_key = 'local_farm'", name="ck_farms_farm_key"),
        sa.CheckConstraint(
            "btrim(display_name) <> ''", name="ck_farms_display_name"
        ),
        sa.PrimaryKeyConstraint("farm_id", name="pk_farms"),
        sa.UniqueConstraint("farm_key", name="uq_farms_farm_key"),
    )

    legacy_farm_id = legacy_farm_ids[0] if legacy_farm_ids else None
    if legacy_farm_id is not None:
        connection.execute(
            sa.text(
                "INSERT INTO farms (farm_id, farm_key, display_name) "
                "VALUES (:farm_id, 'local_farm', 'Local Farm')"
            ),
            {"farm_id": legacy_farm_id},
        )

    op.create_table(
        "plants",
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_key", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
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
            "plant_key ~ '^[a-z0-9]+(_[a-z0-9]+)*$'",
            name="ck_plants_plant_key",
        ),
        sa.CheckConstraint(
            "btrim(display_name) <> ''", name="ck_plants_display_name"
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')", name="ck_plants_status"
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_plants_farm_id_farms",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("plant_id", name="pk_plants"),
        sa.UniqueConstraint(
            "farm_id", "plant_key", name="uq_plants_farm_plant_key"
        ),
    )
    op.create_index(
        "ix_plants_farm_status", "plants", ["farm_id", "status"], unique=False
    )

    op.create_table(
        "plant_access_grants",
        sa.Column("grant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("membership_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "plant_approve_actions",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
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
            "status IN ('active', 'revoked')",
            name="ck_plant_access_grants_status",
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["farm_memberships.membership_id"],
            name="fk_plant_access_grants_membership_id_farm_memberships",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_plant_access_grants_plant_id_plants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("grant_id", name="pk_plant_access_grants"),
        sa.UniqueConstraint(
            "membership_id",
            "plant_id",
            name="uq_plant_access_grants_membership_plant",
        ),
    )
    op.create_index(
        "ix_plant_access_grants_plant_status",
        "plant_access_grants",
        ["plant_id", "status"],
        unique=False,
    )

    op.create_table(
        "admin_audit_records",
        sa.Column("admin_audit_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_kind", sa.String(length=32), nullable=False),
        sa.Column("actor_account_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("actor_membership_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("actor_role_preset", sa.String(length=16), nullable=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column(
            "before_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "after_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "actor_kind IN ('account', 'system_bootstrap')",
            name="ck_admin_audit_records_actor_kind",
        ),
        sa.CheckConstraint(
            "((actor_kind = 'account' AND actor_account_id IS NOT NULL "
            "AND actor_membership_id IS NOT NULL AND actor_role_preset IS NOT NULL) "
            "OR (actor_kind = 'system_bootstrap' AND actor_account_id IS NULL "
            "AND actor_membership_id IS NULL AND actor_role_preset IS NULL))",
            name="ck_admin_audit_records_actor_shape",
        ),
        sa.CheckConstraint(
            "actor_role_preset IS NULL OR actor_role_preset IN "
            "('boss', 'engineer', 'consultant')",
            name="ck_admin_audit_records_actor_role",
        ),
        sa.CheckConstraint(
            "action_type IN ('farm_created', 'farm_display_name_changed', "
            "'account_created', 'account_disabled', 'membership_role_changed', "
            "'membership_disabled', 'plant_created', "
            "'plant_display_name_changed', 'plant_archived', 'plant_restored', "
            "'plant_access_granted', 'plant_access_updated', "
            "'plant_access_revoked', 'plant_approve_actions_changed')",
            name="ck_admin_audit_records_action_type",
        ),
        sa.CheckConstraint(
            "target_type IN ('farm', 'account', 'membership', 'plant', "
            "'plant_access_grant')",
            name="ck_admin_audit_records_target_type",
        ),
        sa.CheckConstraint(
            "btrim(request_id) <> ''", name="ck_admin_audit_records_request_id"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(before_summary) = 'object'",
            name="ck_admin_audit_records_before_summary_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(after_summary) = 'object'",
            name="ck_admin_audit_records_after_summary_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_refs) = 'array'",
            name="ck_admin_audit_records_source_refs_array",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_admin_audit_records_farm_id_farms",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_account_id"],
            ["accounts.account_id"],
            name="fk_admin_audit_records_actor_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_membership_id"],
            ["farm_memberships.membership_id"],
            name="fk_admin_audit_records_actor_membership_id_farm_memberships",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_admin_audit_records_plant_id_plants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("admin_audit_id", name="pk_admin_audit_records"),
    )
    op.create_index(
        "ix_admin_audit_records_farm_created_desc",
        "admin_audit_records",
        ["farm_id", sa.text("created_at DESC"), sa.text("admin_audit_id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_records_plant_created_desc",
        "admin_audit_records",
        ["plant_id", sa.text("created_at DESC"), sa.text("admin_audit_id DESC")],
        unique=False,
        postgresql_where=sa.text("plant_id IS NOT NULL"),
    )

    op.create_foreign_key(
        "fk_farm_memberships_farm_id_farms",
        "farm_memberships",
        "farms",
        ["farm_id"],
        ["farm_id"],
        ondelete="RESTRICT",
    )

    if legacy_farm_id is not None:
        connection.execute(
            sa.text(
                "INSERT INTO admin_audit_records "
                "(admin_audit_id, farm_id, actor_kind, action_type, target_type, "
                "target_id, request_id, before_summary, after_summary, source_refs) "
                "VALUES (:audit_id, :farm_id, 'system_bootstrap', 'farm_created', "
                "'farm', :farm_id, 'migration-ft002', '{}'::jsonb, "
                "jsonb_build_object('farm_id', CAST(:farm_id AS text), "
                "'farm_key', 'local_farm', 'display_name', 'Local Farm'), '[]'::jsonb)"
            ),
            {"audit_id": uuid.uuid4(), "farm_id": legacy_farm_id},
        )


def downgrade() -> None:
    connection = op.get_bind()
    protected_tables = (
        "admin_audit_records",
        "plant_access_grants",
        "plants",
        "farms",
        "farm_memberships",
    )
    has_authority_data = any(
        connection.execute(
            sa.text(f'SELECT EXISTS (SELECT 1 FROM "{table_name}" LIMIT 1)')
        ).scalar_one()
        for table_name in protected_tables
    )
    if has_authority_data:
        raise RuntimeError(
            "FT-002 downgrade refused because Farm authority data exists; "
            "remove it only through an explicit reviewed recovery procedure."
        )

    op.drop_constraint(
        "fk_farm_memberships_farm_id_farms",
        "farm_memberships",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_admin_audit_records_plant_created_desc",
        table_name="admin_audit_records",
    )
    op.drop_index(
        "ix_admin_audit_records_farm_created_desc",
        table_name="admin_audit_records",
    )
    op.drop_table("admin_audit_records")
    op.drop_index(
        "ix_plant_access_grants_plant_status", table_name="plant_access_grants"
    )
    op.drop_table("plant_access_grants")
    op.drop_index("ix_plants_farm_status", table_name="plants")
    op.drop_table("plants")
    op.drop_table("farms")
