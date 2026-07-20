"""PostgreSQL authority model for immutable Safety classifications."""

from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
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


class SafetyActionDecision(Base):
    __tablename__ = "safety_action_decisions"
    __table_args__ = (
        UniqueConstraint(
            "classification_message_id",
            name="uq_safety_action_decisions_classification",
        ),
        CheckConstraint(
            "actor_role_preset IN ('boss', 'engineer', 'consultant')",
            name="ck_safety_action_decisions_actor_role",
        ),
        CheckConstraint(
            "permission_source IN ('boss_role', 'plant_access_grant')",
            name="ck_safety_action_decisions_permission_source",
        ),
        CheckConstraint(
            "((permission_source = 'boss_role' AND actor_role_preset = 'boss' "
            "AND grant_id IS NULL) OR "
            "(permission_source = 'plant_access_grant' "
            "AND actor_role_preset IN ('engineer', 'consultant') "
            "AND grant_id IS NOT NULL))",
            name="ck_safety_action_decisions_permission_shape",
        ),
        CheckConstraint(
            "action_kind IN "
            "('ph_adjustment', 'ec_adjustment', 'solution_change', "
            "'pump_command', 'light_command', 'dosing_command', 'pruning', "
            "'transplanting', 'root_trimming', 'other_physical_action')",
            name="ck_safety_action_decisions_action_kind",
        ),
        CheckConstraint(
            "safety_status IN "
            "('safety_blocked', 'needs_fresh_evidence', "
            "'pending_human_approval')",
            name="ck_safety_action_decisions_safety_status",
        ),
        CheckConstraint(
            "reason_code IN "
            "('unsupported_action', 'approval_authority_missing', "
            "'approval_input_missing_or_stale', 'ready_for_human_approval')",
            name="ck_safety_action_decisions_reason_code",
        ),
        CheckConstraint(
            "((action_kind IN "
            "('pump_command', 'light_command', 'dosing_command', 'pruning', "
            "'transplanting', 'root_trimming', 'other_physical_action') "
            "AND safety_status = 'safety_blocked' "
            "AND reason_code = 'unsupported_action') OR "
            "(action_kind IN ('ph_adjustment', 'ec_adjustment', 'solution_change') "
            "AND ((safety_status = 'safety_blocked' "
            "AND reason_code = 'approval_authority_missing') OR "
            "(safety_status = 'needs_fresh_evidence' "
            "AND reason_code = 'approval_input_missing_or_stale') OR "
            "(safety_status = 'pending_human_approval' "
            "AND reason_code = 'ready_for_human_approval'))))",
            name="ck_safety_action_decisions_route_matrix",
        ),
        CheckConstraint(
            "ph_status IS NULL OR ph_status IN ('fresh', 'stale', 'missing')",
            name="ck_safety_action_decisions_ph_status",
        ),
        CheckConstraint(
            "ec_status IS NULL OR ec_status IN ('fresh', 'stale', 'missing')",
            name="ck_safety_action_decisions_ec_status",
        ),
        CheckConstraint(
            "((ph_status = 'missing' AND ph_measurement_id IS NULL "
            "AND ph_measured_at IS NULL) OR "
            "(ph_status IN ('fresh', 'stale') AND ph_measurement_id IS NOT NULL "
            "AND ph_measured_at IS NOT NULL) OR ph_status IS NULL)",
            name="ck_safety_action_decisions_ph_evidence_shape",
        ),
        CheckConstraint(
            "((ec_status = 'missing' AND ec_measurement_id IS NULL "
            "AND ec_measured_at IS NULL) OR "
            "(ec_status IN ('fresh', 'stale') AND ec_measurement_id IS NOT NULL "
            "AND ec_measured_at IS NOT NULL) OR ec_status IS NULL)",
            name="ck_safety_action_decisions_ec_evidence_shape",
        ),
        CheckConstraint(
            "((reason_code IN ('unsupported_action', 'approval_authority_missing') "
            "AND ph_status IS NULL AND ec_status IS NULL "
            "AND ph_measurement_id IS NULL AND ec_measurement_id IS NULL "
            "AND ph_measured_at IS NULL AND ec_measured_at IS NULL "
            "AND expires_at IS NULL) OR "
            "(reason_code = 'approval_input_missing_or_stale' "
            "AND ph_status IS NOT NULL AND ec_status IS NOT NULL "
            "AND (ph_status <> 'fresh' OR ec_status <> 'fresh') "
            "AND expires_at IS NULL) OR "
            "(reason_code = 'ready_for_human_approval' "
            "AND ph_status = 'fresh' AND ec_status = 'fresh' "
            "AND ph_measurement_id IS NOT NULL AND ec_measurement_id IS NOT NULL "
            "AND ph_measured_at IS NOT NULL AND ec_measured_at IS NOT NULL "
            "AND expires_at IS NOT NULL))",
            name="ck_safety_action_decisions_evidence_matrix",
        ),
        CheckConstraint(
            "created_at = evaluated_at",
            name="ck_safety_action_decisions_evaluation_timestamp",
        ),
        CheckConstraint(
            "((reason_code = 'unsupported_action' "
            "AND summary_text = "
            "'Действие не поддерживается безопасным процессом MVP.') OR "
            "(reason_code = 'approval_authority_missing' "
            "AND summary_text = "
            "'Действие заблокировано: у текущего пользователя нет права подтверждения.') OR "
            "(reason_code = 'approval_input_missing_or_stale' "
            "AND summary_text = "
            "'Перед предложением действия нужны свежие измерения pH и EC.') OR "
            "(reason_code = 'ready_for_human_approval' AND "
            "((action_kind = 'ph_adjustment' AND summary_text = "
            "'Предложена ручная корректировка pH. Требуется решение уполномоченного пользователя.') OR "
            "(action_kind = 'ec_adjustment' AND summary_text = "
            "'Предложена ручная корректировка EC питательного раствора. Требуется решение уполномоченного пользователя.') OR "
            "(action_kind = 'solution_change' AND summary_text = "
            "'Предложена ручная замена питательного раствора. Требуется решение уполномоченного пользователя.'))))",
            name="ck_safety_action_decisions_summary",
        ),
    )

    decision_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    classification_message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("safety_classifications.message_id", ondelete="RESTRICT"),
        nullable=False,
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
    actor_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.account_id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farm_memberships.membership_id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_role_preset: Mapped[str] = mapped_column(String(16), nullable=False)
    permission_source: Mapped[str] = mapped_column(String(32), nullable=False)
    grant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plant_access_grants.grant_id", ondelete="RESTRICT"),
        nullable=True,
    )
    action_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    safety_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    ph_measurement_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("manual_measurements.measurement_id", ondelete="RESTRICT"),
        nullable=True,
    )
    ec_measurement_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("manual_measurements.measurement_id", ondelete="RESTRICT"),
        nullable=True,
    )
    ph_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ec_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ph_measured_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ec_measured_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)


__all__ = ["SafetyActionDecision", "SafetyClassification"]
