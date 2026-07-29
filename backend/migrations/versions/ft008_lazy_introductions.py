"""Remove presentation-only roster-introduction batch state."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "ft008_lazy_introductions"
down_revision: str | None = "ft013_simplify_companion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_BATCH_TABLE = "agent_introduction_batches"


def upgrade() -> None:
    op.drop_table(_BATCH_TABLE)


def downgrade() -> None:
    op.create_table(
        _BATCH_TABLE,
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
        sa.PrimaryKeyConstraint(
            "batch_id",
            name="pk_agent_introduction_batches",
        ),
        sa.UniqueConstraint(
            "plant_id",
            "roster_version",
            name="uq_agent_introduction_batches_plant_roster",
        ),
    )
