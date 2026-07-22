"""Add immutable Task Follow-Up runtime-stage dispositions."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ft012_runtime_dispositions"
down_revision: str | None = "ft012_task_approval_outcomes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB = postgresql.JSONB(astext_type=sa.Text())

_COMMITMENT_FUNCTION = "ft012_enforce_ordinary_dispatch_commitment_write_once"
_COMMITMENT_TRIGGER = "trg_ordinary_task_dispatch_commitment_write_once"


def upgrade() -> None:
    op.add_column(
        "ordinary_task_dispatch_dispositions",
        sa.Column(
            "expected_task_create_fingerprint",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_ordinary_task_dispatch_dispositions_commitment_matrix",
        "ordinary_task_dispatch_dispositions",
        "((outcome = 'consumed' "
        "AND expected_task_create_fingerprint IS NOT NULL "
        "AND expected_task_create_fingerprint ~ '^[0-9a-f]{64}$') OR "
        "(outcome = 'denied' "
        "AND expected_task_create_fingerprint IS NULL))",
        postgresql_not_valid=True,
    )
    op.execute(
        sa.text(
            f"""
CREATE FUNCTION {_COMMITMENT_FUNCTION}()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.expected_task_create_fingerprint IS DISTINCT FROM
       NEW.expected_task_create_fingerprint THEN
        RAISE EXCEPTION USING
            ERRCODE = '23514',
            MESSAGE = 'ordinary task dispatch commitment is write-once',
            CONSTRAINT = 'ck_ordinary_task_dispatch_commitment_write_once';
    END IF;
    RETURN NEW;
END;
$$
"""
        )
    )
    op.execute(
        sa.text(
            f"""
CREATE TRIGGER {_COMMITMENT_TRIGGER}
BEFORE UPDATE OF expected_task_create_fingerprint
ON ordinary_task_dispatch_dispositions
FOR EACH ROW
EXECUTE FUNCTION {_COMMITMENT_FUNCTION}()
"""
        )
    )
    op.create_table(
        "task_follow_up_runtime_dispositions",
        sa.Column("run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("farm_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("command_sha256", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("message_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("input_sha256", sa.String(length=64), nullable=True),
        sa.Column("denial_code", sa.String(length=32), nullable=True),
        sa.Column("model_ref", sa.String(length=193), nullable=False),
        sa.Column("runtime_event_ref", JSONB, nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "command_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_task_follow_up_runtime_dispositions_command_sha256",
        ),
        sa.CheckConstraint(
            "input_sha256 IS NULL OR input_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_task_follow_up_runtime_dispositions_input_sha256",
        ),
        sa.CheckConstraint(
            "outcome IN ('envelope_handed_off', 'publication_denied')",
            name="ck_task_follow_up_runtime_dispositions_outcome",
        ),
        sa.CheckConstraint(
            "denial_code IS NULL OR denial_code = 'AGENT_PUBLICATION_BLOCKED'",
            name="ck_task_follow_up_runtime_dispositions_denial_code",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(runtime_event_ref) = 'object'",
            name="ck_task_follow_up_runtime_dispositions_event_ref_object",
        ),
        sa.CheckConstraint(
            "((outcome = 'envelope_handed_off' AND message_id IS NOT NULL "
            "AND input_sha256 IS NOT NULL AND denial_code IS NULL) OR "
            "(outcome = 'publication_denied' AND message_id IS NULL "
            "AND input_sha256 IS NULL "
            "AND denial_code = 'AGENT_PUBLICATION_BLOCKED'))",
            name="ck_task_follow_up_runtime_dispositions_terminal_matrix",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_task_follow_up_runtime_dispositions_farm",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.plant_id"],
            name="fk_task_follow_up_runtime_dispositions_plant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "run_id",
            name="pk_task_follow_up_runtime_dispositions",
        ),
        sa.UniqueConstraint(
            "message_id",
            name="uq_task_follow_up_runtime_dispositions_message",
        ),
    )


def downgrade() -> None:
    connection = op.get_bind()
    populated = connection.execute(
        sa.text(
            "SELECT "
            "EXISTS (SELECT 1 "
            "FROM task_follow_up_runtime_dispositions LIMIT 1) OR "
            "EXISTS (SELECT 1 "
            "FROM ordinary_task_dispatch_dispositions "
            "WHERE expected_task_create_fingerprint IS NOT NULL LIMIT 1)"
        )
    ).scalar_one()
    if populated:
        raise RuntimeError(
            "FT-012 runtime-disposition downgrade refused because immutable "
            "runtime or Task-create commitment authority exists; remove it "
            "only through an explicit reviewed recovery procedure."
        )
    op.drop_table("task_follow_up_runtime_dispositions")
    op.execute(
        sa.text(
            f"DROP TRIGGER {_COMMITMENT_TRIGGER} "
            "ON ordinary_task_dispatch_dispositions"
        )
    )
    op.execute(sa.text(f"DROP FUNCTION {_COMMITMENT_FUNCTION}()"))
    op.drop_constraint(
        "ck_ordinary_task_dispatch_dispositions_commitment_matrix",
        "ordinary_task_dispatch_dispositions",
        type_="check",
    )
    op.drop_column(
        "ordinary_task_dispatch_dispositions",
        "expected_task_create_fingerprint",
    )
