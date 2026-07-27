"""Remove the redundant Companion attention-to-current-proposal pointer."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "ft013_simplify_companion"
down_revision: str | None = "ft012_simplify_follow_up_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ATTENTION_TABLE = "companion_human_attention"
_CURRENT_PROPOSAL_FK = "fk_companion_attention_current_proposal"


def upgrade() -> None:
    op.drop_constraint(
        _CURRENT_PROPOSAL_FK,
        _ATTENTION_TABLE,
        type_="foreignkey",
    )
    op.drop_column(_ATTENTION_TABLE, "current_proposal_id")


def downgrade() -> None:
    op.add_column(
        _ATTENTION_TABLE,
        sa.Column("current_proposal_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.execute(
        sa.text(
            """
UPDATE companion_human_attention AS attention
SET current_proposal_id = COALESCE(
    (
        SELECT proposal.proposal_id
        FROM companion_proposals AS proposal
        WHERE proposal.attention_id = attention.attention_id
          AND proposal.issue_id = attention.issue_id
          AND proposal.state = 'pending'
    ),
    (
        SELECT decision.proposal_id
        FROM decision_records AS decision
        WHERE decision.decision_record_id =
              attention.satisfied_by_decision_record_id
          AND decision.attention_id = attention.attention_id
          AND decision.issue_id = attention.issue_id
    )
)
"""
        )
    )
    missing = op.get_bind().execute(
        sa.text(
            """
SELECT EXISTS (
    SELECT 1
    FROM companion_human_attention
    WHERE current_proposal_id IS NULL
    LIMIT 1
)
"""
        )
    ).scalar_one()
    if missing:
        raise RuntimeError(
            "FT-013 simplification downgrade cannot derive a proposal for "
            "every retained attention row."
        )
    op.alter_column(
        _ATTENTION_TABLE,
        "current_proposal_id",
        existing_type=sa.Uuid(as_uuid=True),
        nullable=False,
    )
    op.create_foreign_key(
        _CURRENT_PROPOSAL_FK,
        _ATTENTION_TABLE,
        "companion_proposals",
        ["current_proposal_id"],
        ["proposal_id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )
