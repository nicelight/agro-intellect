"""Add the FT-014 Dataset Candidate aggregate and creation-seam schema."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ft014_dataset_candidates"
down_revision: str | None = "ft013_decision_effects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "dataset_candidates",
        sa.Column("candidate_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "candidate_status",
            sa.Enum(
                "candidate",
                "needs_review",
                "confirmed",
                "rejected",
                "excluded",
                name="dataset_candidate_status",
            ),
            nullable=False,
            server_default=sa.text("'candidate'"),
        ),
        sa.Column(
            "candidate_origin",
            sa.Enum("raw", "agent_labeled", name="dataset_candidate_origin"),
            nullable=False,
            server_default=sa.text("'raw'"),
        ),
        sa.Column(
            "quality_tier",
            sa.Enum("standard", "gold", name="dataset_quality_tier"),
            nullable=False,
            server_default=sa.text("'standard'"),
        ),
        sa.Column(
            "split",
            sa.Enum("train", "eval", "holdout", name="dataset_split"),
            nullable=True,
        ),
        sa.Column(
            "confirmation_source",
            sa.Enum(
                "curator_auto",
                "human_review",
                "expert_review",
                "batch_review",
                name="dataset_confirmation_source",
            ),
            nullable=True,
        ),
        sa.Column("evidence_refs", JSONB, nullable=False),
        sa.Column(
            "source_kind",
            sa.Enum(
                "photo_catalog_item",
                "daily_check_in",
                "manual_measurement",
                "follow_up_outcome",
                name="dataset_source_kind",
            ),
            nullable=False,
        ),
        sa.Column("source_ref", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "curator_decision",
            sa.Enum("selected", "deferred", "rejected", name="dataset_curator_decision"),
            nullable=True,
        ),
        sa.Column("curator_notes_ref", sa.Text(), nullable=True),
        sa.Column("curator_run_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "curator_command_sha256",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "curator_recorded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "corrected",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "follow_up_seen",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "can_train_on",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "record_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "event_refs",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence_refs) = 'array' "
            "AND jsonb_array_length(evidence_refs) >= 1",
            name="ck_dataset_candidates_evidence_refs",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(event_refs) = 'array'",
            name="ck_dataset_candidates_event_refs",
        ),
        sa.CheckConstraint(
            "((curator_run_id IS NULL AND curator_command_sha256 IS NULL "
            "AND curator_recorded_at IS NULL) OR "
            "(curator_run_id IS NOT NULL AND curator_command_sha256 IS NOT NULL "
            "AND curator_recorded_at IS NOT NULL)) AND "
            "(curator_command_sha256 IS NULL OR "
            "curator_command_sha256 ~ '^[0-9a-f]{64}$')",
            name="ck_dataset_candidates_curator_identity",
        ),
        sa.CheckConstraint(
            "quality_tier <> 'gold' OR "
            "(candidate_status = 'confirmed' AND confirmation_source IN "
            "('human_review', 'expert_review', 'batch_review'))",
            name="ck_dataset_candidates_gold_guard",
        ),
        sa.CheckConstraint(
            "can_train_on IS FALSE OR "
            "(candidate_status = 'confirmed' AND confirmation_source IS NOT NULL)",
            name="ck_dataset_candidates_trainability_guard",
        ),
        sa.CheckConstraint(
            "record_version > 0",
            name="ck_dataset_candidates_record_version",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_dataset_candidates_farm",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_dataset_candidates_plant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("candidate_id", name="pk_dataset_candidates"),
        sa.UniqueConstraint(
            "plant_id",
            "source_kind",
            "source_ref",
            name="uq_dataset_candidates_source_identity",
        ),
        sa.UniqueConstraint(
            "curator_run_id",
            name="uq_dataset_candidates_curator_run",
        ),
    )


def downgrade() -> None:
    op.drop_table("dataset_candidates")
    op.execute(sa.text("DROP TYPE IF EXISTS dataset_curator_decision"))
    op.execute(sa.text("DROP TYPE IF EXISTS dataset_source_kind"))
    op.execute(sa.text("DROP TYPE IF EXISTS dataset_confirmation_source"))
    op.execute(sa.text("DROP TYPE IF EXISTS dataset_split"))
    op.execute(sa.text("DROP TYPE IF EXISTS dataset_quality_tier"))
    op.execute(sa.text("DROP TYPE IF EXISTS dataset_candidate_origin"))
    op.execute(sa.text("DROP TYPE IF EXISTS dataset_candidate_status"))
