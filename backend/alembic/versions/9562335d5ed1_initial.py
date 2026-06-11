"""initial

Revision ID: 9562335d5ed1
Revises:
Create Date: 2026-06-06 23:50:07.142061

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9562335d5ed1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("login_identifier", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_by_account_id", sa.Text(), nullable=True,
        ),
        sa.Column(
            "updated_by_account_id", sa.Text(), nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'invited', 'disabled')",
            name="ck_accounts_status",
        ),
        sa.PrimaryKeyConstraint("account_id"),
        sa.UniqueConstraint("login_identifier"),
        sa.ForeignKeyConstraint(
            ["created_by_account_id"], ["accounts.account_id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_account_id"], ["accounts.account_id"],
        ),
    )
    op.create_table(
        "farms",
        sa.Column("farm_id", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column(
            "sync_status", sa.Text(), nullable=False, server_default="local_only",
        ),
        sa.Column(
            "one_farm_guard", sa.Boolean(), nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("status = 'active'", name="ck_farms_status"),
        sa.CheckConstraint(
            "sync_status = 'local_only'", name="ck_farms_sync_status",
        ),
        sa.CheckConstraint(
            "one_farm_guard IS TRUE", name="ck_farms_one_farm_guard",
        ),
        sa.PrimaryKeyConstraint("farm_id"),
        sa.UniqueConstraint("one_farm_guard"),
    )
    op.create_table(
        "farm_memberships",
        sa.Column("membership_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("farm_id", sa.Text(), nullable=False),
        sa.Column("role_preset", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "changed_by_account_id", sa.Text(), nullable=True,
        ),
        sa.CheckConstraint(
            "role_preset IN ('boss', 'engineer', 'consultant')",
            name="ck_farm_memberships_role_preset",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'invited', 'disabled', 'removed')",
            name="ck_farm_memberships_status",
        ),
        sa.PrimaryKeyConstraint("membership_id"),
        sa.UniqueConstraint("account_id", name="uq_farm_memberships_account"),
        sa.UniqueConstraint(
            "account_id", "farm_id", name="uq_farm_memberships_account_farm",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.account_id"],
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"], ["farms.farm_id"],
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_account_id"], ["accounts.account_id"],
        ),
    )
    op.create_index(
        "idx_farm_memberships_account_status",
        "farm_memberships",
        ["account_id", "status"],
    )
    op.create_table(
        "local_sessions",
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("farm_id", sa.Text(), nullable=False),
        sa.Column("membership_id", sa.Text(), nullable=False),
        sa.Column("session_hash", sa.CHAR(64), nullable=False),
        sa.Column("session_ref", sa.Text(), nullable=False),
        sa.Column("auth_provenance_ref", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=False,
        ),
        sa.Column(
            "revoked_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column("created_request_ref", sa.Text(), nullable=True),
        sa.Column("revoked_request_ref", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'revoked')",
            name="ck_local_sessions_status",
        ),
        sa.CheckConstraint(
            "session_hash ~ '^[a-f0-9]{64}$'",
            name="ck_local_sessions_session_hash",
        ),
        sa.CheckConstraint(
            "session_ref LIKE 'sess_ref_%'",
            name="ck_local_sessions_session_ref",
        ),
        sa.CheckConstraint(
            "auth_provenance_ref LIKE 'auth_ref_%'",
            name="ck_local_sessions_auth_provenance_ref",
        ),
        sa.PrimaryKeyConstraint("session_id"),
        sa.UniqueConstraint("session_hash"),
        sa.UniqueConstraint("session_ref"),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.account_id"],
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"], ["farms.farm_id"],
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"], ["farm_memberships.membership_id"],
        ),
    )
    op.create_index(
        "idx_local_sessions_account_status",
        "local_sessions",
        ["account_id", "status"],
    )
    op.create_index(
        "idx_local_sessions_expires_at",
        "local_sessions",
        ["expires_at"],
    )
    op.create_table(
        "plants",
        sa.Column("plant_id", sa.Text(), nullable=False),
        sa.Column("farm_id", sa.Text(), nullable=False),
        sa.Column("canonical_label", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="active"),
        sa.Column(
            "created_by_actor_ref", sa.Text(), nullable=False, server_default="",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "archived_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column("archived_by_actor_ref", sa.Text(), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
        sa.Column(
            "restored_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column("restored_by_actor_ref", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "state IN ('active', 'archived')",
            name="ck_plants_state",
        ),
        sa.PrimaryKeyConstraint("plant_id"),
        sa.ForeignKeyConstraint(
            ["farm_id"], ["farms.farm_id"],
        ),
    )
    op.create_index(
        "idx_plants_farm_state",
        "plants",
        ["farm_id", "state"],
    )
    op.create_table(
        "plant_access_grants",
        sa.Column("grant_id", sa.Text(), nullable=False),
        sa.Column("farm_id", sa.Text(), nullable=False),
        sa.Column("plant_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("membership_id", sa.Text(), nullable=False),
        sa.Column(
            "state", sa.Text(), nullable=False, server_default="granted",
        ),
        sa.Column(
            "can_view", sa.Boolean(), nullable=False, server_default=sa.text("true"),
        ),
        sa.Column(
            "can_work", sa.Boolean(), nullable=False, server_default=sa.text("true"),
        ),
        sa.Column(
            "plant_approve_actions",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_by_actor_ref", sa.Text(), nullable=False, server_default="",
        ),
        sa.Column(
            "updated_by_actor_ref", sa.Text(), nullable=False, server_default="",
        ),
        sa.Column(
            "revoked_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.CheckConstraint(
            "state IN ('granted', 'revoked')",
            name="ck_plant_access_grants_state",
        ),
        sa.PrimaryKeyConstraint("grant_id"),
        sa.ForeignKeyConstraint(
            ["farm_id"], ["farms.farm_id"],
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"], ["plants.plant_id"],
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.account_id"],
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"], ["farm_memberships.membership_id"],
        ),
    )
    op.create_index(
        "idx_plant_access_grants_plant",
        "plant_access_grants",
        ["plant_id"],
    )
    op.create_index(
        "idx_plant_access_grants_account",
        "plant_access_grants",
        ["account_id"],
    )
    op.create_table(
        "admin_audit_records",
        sa.Column("audit_id", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("actor_account_id", sa.Text(), nullable=False),
        sa.Column("target_account_id", sa.Text(), nullable=True),
        sa.Column("farm_id", sa.Text(), nullable=True),
        sa.Column("membership_id", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("auth_provenance_ref", sa.Text(), nullable=True),
        sa.Column("request_ref", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("audit_id"),
    )


def downgrade() -> None:
    op.drop_table("admin_audit_records")
    op.drop_table("plant_access_grants")
    op.drop_table("plants")
    op.drop_table("local_sessions")
    op.drop_table("farm_memberships")
    op.drop_table("farms")
    op.drop_table("accounts")
