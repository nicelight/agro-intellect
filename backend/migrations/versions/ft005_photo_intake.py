"""Add FT-005 photo catalog items."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ft005_photo_intake"
down_revision: str | None = "ft004_plant_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "photo_catalog_items",
        sa.Column("photo_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("check_in_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("uploaded_by_account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_membership_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("photo_type", sa.String(length=32), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("original_file_ref", sa.Text(), nullable=False),
        sa.Column("manifest_ref", sa.Text(), nullable=False),
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
            "local_only",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "can_train_on",
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
            "photo_type IN ('whole_plant', 'leaf_closeup', 'roots', "
            "'problem_area', 'other')",
            name="ck_photo_catalog_items_photo_type",
        ),
        sa.CheckConstraint(
            "content_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_photo_catalog_items_content_type",
        ),
        sa.CheckConstraint(
            "size_bytes >= 0 AND size_bytes <= 20971520",
            name="ck_photo_catalog_items_size_bytes_range",
        ),
        sa.CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_photo_catalog_items_sha256_lower_hex",
        ),
        sa.CheckConstraint(
            "original_file_ref ~ "
            "'^plants/[0-9a-f-]{36}/photos/[0-9a-f-]{36}/original\\."
            "(jpg|png|webp)$'",
            name="ck_photo_catalog_items_original_file_ref_shape",
        ),
        sa.CheckConstraint(
            "manifest_ref ~ "
            "'^plants/[0-9a-f-]{36}/photos/[0-9a-f-]{36}/"
            "manifest\\.initial_capture\\.json$'",
            name="ck_photo_catalog_items_manifest_ref_shape",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_refs) = 'object'",
            name="ck_photo_catalog_items_source_refs_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(event_refs) = 'object'",
            name="ck_photo_catalog_items_event_refs_object",
        ),
        sa.CheckConstraint(
            "local_only IS TRUE",
            name="ck_photo_catalog_items_local_only_true",
        ),
        sa.CheckConstraint(
            "can_train_on IS FALSE",
            name="ck_photo_catalog_items_can_train_on_false",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_photo_catalog_items_farm_id_farms",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_photo_catalog_items_plant_id_plants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["check_in_id"],
            ["daily_checkins.check_in_id"],
            name="fk_photo_catalog_items_check_in_id_daily_checkins",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_account_id"],
            ["accounts.account_id"],
            name="fk_photo_catalog_items_uploaded_by_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_membership_id"],
            ["farm_memberships.membership_id"],
            name="fk_photo_catalog_items_uploaded_by_membership_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("photo_id", name="pk_photo_catalog_items"),
    )
    op.create_index(
        "ix_photo_catalog_items_plant_uploaded_desc",
        "photo_catalog_items",
        [
            "plant_id",
            sa.text("uploaded_at DESC"),
            sa.text("photo_id DESC"),
        ],
        unique=False,
    )
    op.create_index(
        "ix_photo_catalog_items_check_in_id",
        "photo_catalog_items",
        ["check_in_id"],
        unique=False,
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_photos = connection.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM photo_catalog_items LIMIT 1)")
    ).scalar_one()
    if has_photos:
        raise RuntimeError(
            "FT-005 downgrade refused because photo catalog authority data "
            "exists; remove it only through an explicit reviewed recovery "
            "procedure."
        )
    op.drop_index(
        "ix_photo_catalog_items_check_in_id",
        table_name="photo_catalog_items",
    )
    op.drop_index(
        "ix_photo_catalog_items_plant_uploaded_desc",
        table_name="photo_catalog_items",
    )
    op.drop_table("photo_catalog_items")
