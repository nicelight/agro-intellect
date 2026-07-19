from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..access_admin.models import Base, JSON_DOCUMENT


class PlantStateRecord(Base):
    __tablename__ = "plant_state_records"
    __table_args__ = (
        CheckConstraint(
            "record_kind IN ('vision_observation', 'plant_state_assessment')",
            name="ck_plant_state_records_record_kind",
        ),
        CheckConstraint(
            "((record_kind = 'vision_observation' AND agent_id = 'vision_observation' "
            "AND polarity IS NOT NULL AND severity IS NOT NULL "
            "AND assessment_kind IS NULL AND direction IS NULL) OR "
            "(record_kind = 'plant_state_assessment' AND agent_id = 'plant_state' "
            "AND polarity IS NULL AND severity IS NULL "
            "AND assessment_kind IS NOT NULL AND direction IS NOT NULL))",
            name="ck_plant_state_records_kind_fields",
        ),
        CheckConstraint(
            "polarity IS NULL OR polarity IN "
            "('present', 'absent', 'uncertain', 'not_assessable')",
            name="ck_plant_state_records_polarity",
        ),
        CheckConstraint(
            "severity IS NULL OR severity IN "
            "('none', 'mild', 'moderate', 'strong', 'unknown')",
            name="ck_plant_state_records_severity",
        ),
        CheckConstraint(
            "((polarity = 'absent' AND severity = 'none') OR "
            "(polarity = 'present' AND severity IN ('mild', 'moderate', 'strong')) OR "
            "(polarity IN ('uncertain', 'not_assessable') AND severity = 'unknown') OR "
            "polarity IS NULL)",
            name="ck_plant_state_records_vision_shape",
        ),
        CheckConstraint(
            "assessment_kind IS NULL OR assessment_kind IN ('trend', 'conflict', 'unknown')",
            name="ck_plant_state_records_assessment_kind",
        ),
        CheckConstraint(
            "direction IS NULL OR direction IN "
            "('increasing', 'decreasing', 'stable', 'mixed', 'not_applicable')",
            name="ck_plant_state_records_direction",
        ),
        CheckConstraint(
            "((assessment_kind = 'trend' AND direction <> 'not_applicable') OR "
            "(assessment_kind IN ('conflict', 'unknown') AND direction = 'not_applicable') OR "
            "assessment_kind IS NULL)",
            name="ck_plant_state_records_assessment_shape",
        ),
        CheckConstraint(
            "trust_status IN "
            "('unknown', 'observed', 'hypothesis', 'conflicting', 'confirmed', 'rejected')",
            name="ck_plant_state_records_trust_status",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_plant_state_records_confidence",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_plant_state_records_version",
        ),
        CheckConstraint(
            "btrim(summary) <> '' AND char_length(summary) <= 1000",
            name="ck_plant_state_records_summary",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(source_refs) = 'array' AND jsonb_array_length(source_refs) "
            "BETWEEN 1 AND 4",
            name="ck_plant_state_records_source_refs",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "((trust_status = 'confirmed' AND confirmation_source IS NOT NULL "
            "AND confirmed_by_account_id IS NOT NULL "
            "AND confirmed_by_membership_id IS NOT NULL AND confirmed_at IS NOT NULL) OR "
            "(trust_status <> 'confirmed' AND confirmation_source IS NULL "
            "AND confirmed_by_account_id IS NULL "
            "AND confirmed_by_membership_id IS NULL AND confirmed_at IS NULL))",
            name="ck_plant_state_records_confirmation_shape",
        ),
        CheckConstraint(
            "confirmation_source IS NULL OR confirmation_source IN "
            "('human_review', 'manual_measurement', 'follow_up')",
            name="ck_plant_state_records_confirmation_source",
        ),
        UniqueConstraint("message_id", name="uq_plant_state_records_message_id"),
        Index(
            "ix_plant_state_records_plant_recorded_desc",
            "plant_id",
            "recorded_at",
            "state_record_id",
        ),
        Index(
            "ix_plant_state_records_plant_key_recorded_desc",
            "plant_id",
            "observation_key",
            "recorded_at",
        ),
    )

    state_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
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
    record_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    message_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    observation_key: Mapped[str] = mapped_column(String(64), nullable=False)
    polarity: Mapped[str | None] = mapped_column(String(24), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    assessment_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(24), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    trust_status: Mapped[str] = mapped_column(String(16), nullable=False)
    source_refs: Mapped[list[str]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=list, server_default=text("'[]'")
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmation_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confirmed_by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.account_id", ondelete="RESTRICT"),
        nullable=True,
    )
    confirmed_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farm_memberships.membership_id", ondelete="RESTRICT"),
        nullable=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["PlantStateRecord"]
