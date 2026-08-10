"""PostgreSQL authority model for the FT-014 Dataset Candidate aggregate."""

from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..access_admin.models import Base, JSON_DOCUMENT


CANDIDATE_STATUS = Enum(
    "candidate",
    "needs_review",
    "confirmed",
    "rejected",
    "excluded",
    name="dataset_candidate_status",
)
CANDIDATE_ORIGIN = Enum("raw", "agent_labeled", name="dataset_candidate_origin")
QUALITY_TIER = Enum("standard", "gold", name="dataset_quality_tier")
DATASET_SPLIT = Enum("train", "eval", "holdout", name="dataset_split")
CONFIRMATION_SOURCE = Enum(
    "curator_auto",
    "human_review",
    "expert_review",
    "batch_review",
    name="dataset_confirmation_source",
)
SOURCE_KIND = Enum(
    "photo_catalog_item",
    "daily_check_in",
    "manual_measurement",
    "follow_up_outcome",
    name="dataset_source_kind",
)
CURATOR_DECISION = Enum(
    "selected",
    "deferred",
    "rejected",
    name="dataset_curator_decision",
)


class DatasetCandidate(Base):
    __tablename__ = "dataset_candidates"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(evidence_refs) = 'array' "
            "AND jsonb_array_length(evidence_refs) >= 1",
            name="ck_dataset_candidates_evidence_refs",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(event_refs) = 'array'",
            name="ck_dataset_candidates_event_refs",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "((curator_run_id IS NULL AND curator_command_sha256 IS NULL "
            "AND curator_recorded_at IS NULL) OR "
            "(curator_run_id IS NOT NULL AND curator_command_sha256 IS NOT NULL "
            "AND curator_recorded_at IS NOT NULL)) AND "
            "(curator_command_sha256 IS NULL OR "
            "curator_command_sha256 ~ '^[0-9a-f]{64}$')",
            name="ck_dataset_candidates_curator_identity",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "quality_tier <> 'gold' OR "
            "(candidate_status = 'confirmed' AND confirmation_source IN "
            "('human_review', 'expert_review', 'batch_review'))",
            name="ck_dataset_candidates_gold_guard",
        ),
        CheckConstraint(
            "can_train_on IS FALSE OR "
            "(candidate_status = 'confirmed' AND confirmation_source IS NOT NULL)",
            name="ck_dataset_candidates_trainability_guard",
        ),
        CheckConstraint(
            "record_version > 0",
            name="ck_dataset_candidates_record_version",
        ),
        UniqueConstraint(
            "plant_id",
            "source_kind",
            "source_ref",
            name="uq_dataset_candidates_source_identity",
        ),
        UniqueConstraint(
            "curator_run_id",
            name="uq_dataset_candidates_curator_run",
        ),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
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
    candidate_status: Mapped[str] = mapped_column(
        CANDIDATE_STATUS,
        nullable=False,
        default="candidate",
        server_default="candidate",
    )
    candidate_origin: Mapped[str] = mapped_column(
        CANDIDATE_ORIGIN,
        nullable=False,
        default="raw",
        server_default="raw",
    )
    quality_tier: Mapped[str] = mapped_column(
        QUALITY_TIER,
        nullable=False,
        default="standard",
        server_default="standard",
    )
    split: Mapped[str | None] = mapped_column(DATASET_SPLIT)
    confirmation_source: Mapped[str | None] = mapped_column(CONFIRMATION_SOURCE)
    evidence_refs: Mapped[list[dict[str, object]]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    source_kind: Mapped[str] = mapped_column(SOURCE_KIND, nullable=False)
    source_ref: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    curator_decision: Mapped[str | None] = mapped_column(CURATOR_DECISION)
    curator_notes_ref: Mapped[str | None] = mapped_column(Text)
    curator_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    curator_command_sha256: Mapped[str | None] = mapped_column(String(64))
    curator_recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    corrected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    follow_up_seen: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    can_train_on: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    record_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    event_refs: Mapped[list[dict[str, object]]] = mapped_column(
        JSON_DOCUMENT,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


__all__ = ["DatasetCandidate"]
