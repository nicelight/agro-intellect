"""Remove the pre-classification Task Follow-Up replay authority."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ft012_simplify_follow_up_runtime"
down_revision: str | None = "ft013_governance_aggregate"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB = postgresql.JSONB(astext_type=sa.Text())

_COMMITMENT_FUNCTION = "ft012_enforce_ordinary_dispatch_commitment_write_once"
_COMMITMENT_TRIGGER = "trg_ordinary_task_dispatch_commitment_write_once"
_COMMITMENT_CHECK = (
    "ck_ordinary_task_dispatch_dispositions_commitment_matrix"
)
_RUNTIME_TABLE = "task_follow_up_runtime_dispositions"
_DISPATCH_TABLE = "ordinary_task_dispatch_dispositions"


def upgrade() -> None:
    connection = op.get_bind()
    populated = connection.execute(
        sa.text(
            "SELECT EXISTS ("
            f"SELECT 1 FROM {_RUNTIME_TABLE} LIMIT 1"
            ")"
        )
    ).scalar_one()
    if populated:
        raise RuntimeError(
            "FT-012 simplification refused because "
            "task_follow_up_runtime_dispositions contains historical authority; "
            "preserve the schema and route the rows through an explicit reviewed "
            "data-maintenance procedure."
        )

    op.execute(
        sa.text(
            f"DROP TRIGGER {_COMMITMENT_TRIGGER} ON {_DISPATCH_TABLE}"
        )
    )
    op.execute(sa.text(f"DROP FUNCTION {_COMMITMENT_FUNCTION}()"))
    op.drop_constraint(
        _COMMITMENT_CHECK,
        _DISPATCH_TABLE,
        type_="check",
    )
    op.drop_column(_DISPATCH_TABLE, "expected_task_create_fingerprint")
    op.drop_table(_RUNTIME_TABLE)


def downgrade() -> None:
    op.add_column(
        _DISPATCH_TABLE,
        sa.Column(
            "expected_task_create_fingerprint",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE ordinary_task_dispatch_dispositions AS disposition "
            "SET expected_task_create_fingerprint = task.create_request_fingerprint "
            "FROM tasks AS task "
            "WHERE disposition.outcome = 'consumed' "
            "AND task.classification_message_id = "
            "disposition.classification_message_id"
        )
    )
    missing_commitment = op.get_bind().execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM ordinary_task_dispatch_dispositions "
            "WHERE outcome = 'consumed' "
            "AND expected_task_create_fingerprint IS NULL LIMIT 1"
            ")"
        )
    ).scalar_one()
    if missing_commitment:
        raise RuntimeError(
            "FT-012 simplification downgrade cannot reconstruct the historical "
            "Task-create commitment for every consumed disposition."
        )

    op.create_check_constraint(
        _COMMITMENT_CHECK,
        _DISPATCH_TABLE,
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
ON {_DISPATCH_TABLE}
FOR EACH ROW
EXECUTE FUNCTION {_COMMITMENT_FUNCTION}()
"""
        )
    )
    op.create_table(
        _RUNTIME_TABLE,
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
