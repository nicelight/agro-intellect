from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..access_admin.models import Base, JSON_DOCUMENT


class DailyCheckIn(Base):
    __tablename__ = "daily_checkins"
    __table_args__ = (
        CheckConstraint(
            "check_in_state IN ('completed')",
            name="ck_daily_checkins_check_in_state",
        ),
        CheckConstraint(
            "observation_state IN ('observed', 'no_observation_provided')",
            name="ck_daily_checkins_observation_state",
        ),
        CheckConstraint(
            "((observation_state = 'observed' AND observation_text IS NOT NULL "
            "AND btrim(observation_text) <> '') OR "
            "(observation_state = 'no_observation_provided' "
            "AND observation_text IS NULL))",
            name="ck_daily_checkins_observation_text_shape",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(source_refs) = 'object'",
            name="ck_daily_checkins_source_refs_object",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(event_refs) = 'object'",
            name="ck_daily_checkins_event_refs_object",
        ).ddl_if(dialect="postgresql"),
        Index(
            "ix_daily_checkins_plant_recorded_desc",
            "plant_id",
            "recorded_at",
            "check_in_id",
        ),
    )

    check_in_id: Mapped[uuid.UUID] = mapped_column(
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
    check_in_state: Mapped[str] = mapped_column(String(16), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observation_state: Mapped[str] = mapped_column(String(32), nullable=False)
    observation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_refs: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict, server_default=text("'{}'")
    )
    event_refs: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ManualMeasurement(Base):
    __tablename__ = "manual_measurements"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('manual_user')",
            name="ck_manual_measurements_source_type",
        ),
        CheckConstraint(
            "trust_status IN ('confirmed')",
            name="ck_manual_measurements_trust_status",
        ),
        CheckConstraint(
            "ph IS NOT NULL OR ec_ms_cm IS NOT NULL",
            name="ck_manual_measurements_value_required",
        ),
        CheckConstraint(
            "ph IS NULL OR (ph >= 0 AND ph <= 14)",
            name="ck_manual_measurements_ph_range",
        ),
        CheckConstraint(
            "ec_ms_cm IS NULL OR ec_ms_cm >= 0",
            name="ck_manual_measurements_ec_non_negative",
        ),
        CheckConstraint(
            "jsonb_typeof(source_refs) = 'object'",
            name="ck_manual_measurements_source_refs_object",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(event_refs) = 'object'",
            name="ck_manual_measurements_event_refs_object",
        ).ddl_if(dialect="postgresql"),
        Index(
            "ix_manual_measurements_plant_measured_desc",
            "plant_id",
            "measured_at",
            "recorded_at",
            "measurement_id",
        ),
        Index("ix_manual_measurements_check_in_id", "check_in_id"),
    )

    measurement_id: Mapped[uuid.UUID] = mapped_column(
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
    check_in_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("daily_checkins.check_in_id", ondelete="RESTRICT"),
        nullable=True,
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
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ph: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    ec_ms_cm: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    provenance_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_refs: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict, server_default=text("'{}'")
    )
    trust_status: Mapped[str] = mapped_column(String(32), nullable=False)
    event_refs: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["DailyCheckIn", "ManualMeasurement"]
