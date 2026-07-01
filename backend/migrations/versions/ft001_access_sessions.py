"""Add the FT-001 account, membership, and local-session persistence baseline."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "ft001_access_sessions"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("login_name", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("account_status", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
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
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "account_status IN ('active', 'disabled')",
            name="ck_accounts_account_status",
        ),
        sa.CheckConstraint(
            "login_name = lower(btrim(login_name)) AND btrim(login_name) <> ''",
            name="ck_accounts_login_name_canonical",
        ),
        sa.PrimaryKeyConstraint("account_id", name="pk_accounts"),
    )
    op.create_index(
        "uq_accounts_login_name",
        "accounts",
        ["login_name"],
        unique=True,
    )

    op.create_table(
        "farm_memberships",
        sa.Column("membership_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role_preset", sa.String(length=16), nullable=False),
        sa.Column("membership_status", sa.String(length=16), nullable=False),
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
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "role_preset IN ('boss', 'engineer', 'consultant')",
            name="ck_farm_memberships_role_preset",
        ),
        sa.CheckConstraint(
            "membership_status IN ('active', 'disabled')",
            name="ck_farm_memberships_membership_status",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.account_id"],
            name="fk_farm_memberships_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("membership_id", name="pk_farm_memberships"),
    )
    op.create_index(
        "uq_farm_memberships_account_farm",
        "farm_memberships",
        ["account_id", "farm_id"],
        unique=True,
    )

    op.create_table(
        "local_sessions",
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auth_method", sa.String(length=32), nullable=False),
        sa.Column("client_label", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "auth_method IN ('local_password')",
            name="ck_local_sessions_auth_method",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.account_id"],
            name="fk_local_sessions_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("session_id", name="pk_local_sessions"),
    )
    op.create_index(
        "uq_local_sessions_token_hash",
        "local_sessions",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_local_sessions_account_id",
        "local_sessions",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "ix_local_sessions_expires_at",
        "local_sessions",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_local_sessions_expires_at", table_name="local_sessions")
    op.drop_index("ix_local_sessions_account_id", table_name="local_sessions")
    op.drop_index("uq_local_sessions_token_hash", table_name="local_sessions")
    op.drop_table("local_sessions")

    op.drop_index(
        "uq_farm_memberships_account_farm",
        table_name="farm_memberships",
    )
    op.drop_table("farm_memberships")

    op.drop_index("uq_accounts_login_name", table_name="accounts")
    op.drop_table("accounts")
