"""PostgreSQL authority model for immutable Safety classifications."""

from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..access_admin.models import Base


class SafetyClassification(Base):
    __tablename__ = "safety_classifications"
    __table_args__ = (
        CheckConstraint(
            "origin_agent_id ~ '^[a-z][a-z0-9_]{2,63}$'",
            name="ck_safety_classifications_origin_agent_id",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "classifier_version = 'safety_gate_v1'",
            name="ck_safety_classifications_classifier_version",
        ),
        CheckConstraint(
            "classification IN "
            "('safe_information', 'safe_task_request', 'physical_action', "
            "'blocked_uncertain')",
            name="ck_safety_classifications_classification",
        ),
        CheckConstraint(
            "safe_task_kind IS NULL OR safe_task_kind IN "
            "('check', 'measurement', 'follow_up')",
            name="ck_safety_classifications_safe_task_kind",
        ),
        CheckConstraint(
            "physical_action_kind IS NULL OR physical_action_kind IN "
            "('ph_adjustment', 'ec_adjustment', 'solution_change', "
            "'pump_command', 'light_command', 'dosing_command', 'pruning', "
            "'transplanting', 'root_trimming', 'other_physical_action')",
            name="ck_safety_classifications_physical_action_kind",
        ),
        CheckConstraint(
            "((classification = 'safe_information' AND safe_task_kind IS NULL "
            "AND physical_action_kind IS NULL "
            "AND reason_code = 'non_physical_information') OR "
            "(classification = 'safe_task_request' "
            "AND ((safe_task_kind = 'check' AND reason_code = 'safe_check_request') "
            "OR (safe_task_kind = 'measurement' "
            "AND reason_code = 'safe_measurement_request') "
            "OR (safe_task_kind = 'follow_up' "
            "AND reason_code = 'safe_follow_up_request')) "
            "AND physical_action_kind IS NULL) OR "
            "(classification = 'physical_action' AND safe_task_kind IS NULL "
            "AND physical_action_kind IS NOT NULL "
            "AND reason_code = 'physical_action_detected') OR "
            "(classification = 'blocked_uncertain' AND safe_task_kind IS NULL "
            "AND physical_action_kind IS NULL "
            "AND reason_code = 'classification_uncertain'))",
            name="ck_safety_classifications_result_matrix",
        ),
        CheckConstraint(
            "provider_status IN ('completed', 'not_configured', 'failed', 'invalid')",
            name="ck_safety_classifications_provider_status",
        ),
        CheckConstraint(
            "provider_status = 'completed' OR "
            "(classification = 'blocked_uncertain' AND safe_task_kind IS NULL "
            "AND physical_action_kind IS NULL "
            "AND reason_code = 'classification_uncertain')",
            name="ck_safety_classifications_provider_failure_closed",
        ),
        CheckConstraint(
            "model_ref IS NULL OR "
            "model_ref ~ '^[a-z][a-z0-9_]{0,63}:[A-Za-z0-9._-]{1,127}$'",
            name="ck_safety_classifications_model_ref",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "input_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_safety_classifications_input_sha256",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "result_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_safety_classifications_result_sha256",
        ).ddl_if(dialect="postgresql"),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farms.farm_id", ondelete="RESTRICT"),
        nullable=False,
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plants.plant_id", ondelete="RESTRICT"),
        nullable=False,
    )
    origin_agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    classifier_version: Mapped[str] = mapped_column(String(64), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    safe_task_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    physical_action_kind: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    provider_status: Mapped[str] = mapped_column(String(16), nullable=False)
    model_ref: Mapped[str | None] = mapped_column(String(193), nullable=True)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    result_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["SafetyClassification"]
