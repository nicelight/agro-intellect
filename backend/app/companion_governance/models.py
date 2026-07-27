"""PostgreSQL authority models for the FT-013 governance aggregate."""

from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
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


class CompanionIssue(Base):
    __tablename__ = "companion_issues"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'resolved', 'closed')",
            name="ck_companion_issues_status",
        ),
        CheckConstraint(
            "btrim(summary_text) <> '' AND char_length(summary_text) <= 500",
            name="ck_companion_issues_summary",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "record_version > 0",
            name="ck_companion_issues_record_version",
        ),
        CheckConstraint(
            "close_request_fingerprint IS NULL OR "
            "close_request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_companion_issues_close_fingerprint",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(opened_event_ref) = 'object' AND "
            "(resolved_event_ref IS NULL OR "
            "jsonb_typeof(resolved_event_ref) = 'object') AND "
            "(closed_event_ref IS NULL OR "
            "jsonb_typeof(closed_event_ref) = 'object')",
            name="ck_companion_issues_event_refs",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "((status = 'open' AND resolved_at IS NULL AND closed_at IS NULL "
            "AND close_request_id IS NULL AND close_request_fingerprint IS NULL "
            "AND resolved_event_ref IS NULL AND closed_event_ref IS NULL) OR "
            "(status = 'resolved' AND is_focused IS FALSE "
            "AND resolved_at IS NOT NULL AND closed_at IS NULL "
            "AND close_request_id IS NULL AND close_request_fingerprint IS NULL "
            "AND resolved_event_ref IS NOT NULL AND closed_event_ref IS NULL) OR "
            "(status = 'closed' AND is_focused IS FALSE "
            "AND resolved_at IS NOT NULL AND closed_at IS NOT NULL "
            "AND close_request_id IS NOT NULL "
            "AND close_request_fingerprint IS NOT NULL "
            "AND resolved_event_ref IS NOT NULL AND closed_event_ref IS NOT NULL))",
            name="ck_companion_issues_state_matrix",
        ),
        UniqueConstraint(
            "created_by_run_id",
            name="uq_companion_issues_created_by_run",
        ),
        Index(
            "uq_companion_issues_one_focused_per_plant",
            "plant_id",
            unique=True,
            postgresql_where=text("is_focused IS TRUE"),
        ),
        Index(
            "ix_companion_issues_plant_order",
            "plant_id",
            "status",
            "created_at",
            "issue_id",
        ),
    )

    issue_id: Mapped[uuid.UUID] = mapped_column(
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
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    is_focused: Mapped[bool] = mapped_column(nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    record_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    close_request_fingerprint: Mapped[str | None] = mapped_column(String(64))
    opened_event_ref: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    resolved_event_ref: Mapped[dict[str, object] | None] = mapped_column(JSON_DOCUMENT)
    closed_event_ref: Mapped[dict[str, object] | None] = mapped_column(JSON_DOCUMENT)


class CompanionHumanAttention(Base):
    __tablename__ = "companion_human_attention"
    __table_args__ = (
        CheckConstraint(
            "attention_sequence > 0",
            name="ck_companion_attention_sequence",
        ),
        CheckConstraint(
            "status IN ('active', 'satisfied')",
            name="ck_companion_attention_status",
        ),
        CheckConstraint(
            "btrim(summary_text) <> '' AND char_length(summary_text) <= 500",
            name="ck_companion_attention_summary",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "record_version > 0",
            name="ck_companion_attention_record_version",
        ),
        CheckConstraint(
            "((status = 'active' AND satisfied_at IS NULL "
            "AND satisfied_by_decision_record_id IS NULL) OR "
            "(status = 'satisfied' AND satisfied_at IS NOT NULL "
            "AND satisfied_by_decision_record_id IS NOT NULL))",
            name="ck_companion_attention_state_matrix",
        ),
        UniqueConstraint(
            "issue_id",
            "attention_sequence",
            name="uq_companion_attention_issue_sequence",
        ),
        Index(
            "uq_companion_attention_one_active_per_issue",
            "issue_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    attention_id: Mapped[uuid.UUID] = mapped_column(
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
    issue_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companion_issues.issue_id", ondelete="RESTRICT"),
        nullable=False,
    )
    attention_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    record_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    satisfied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    satisfied_by_decision_record_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "decision_records.decision_record_id",
            name="fk_companion_attention_satisfied_decision",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
    )


class CompanionProposal(Base):
    __tablename__ = "companion_proposals"
    __table_args__ = (
        CheckConstraint(
            "proposal_sequence > 0",
            name="ck_companion_proposals_sequence",
        ),
        CheckConstraint(
            "state IN ('pending', 'approved', 'rejected', 'superseded')",
            name="ck_companion_proposals_state",
        ),
        CheckConstraint(
            "record_version IN (1, 2)",
            name="ck_companion_proposals_record_version",
        ),
        CheckConstraint(
            "btrim(proposal_summary) <> '' "
            "AND char_length(proposal_summary) <= 500 "
            "AND btrim(proposal_text) <> '' "
            "AND char_length(proposal_text) <= 2000 "
            "AND (rationale_text IS NULL OR "
            "(btrim(rationale_text) <> '' "
            "AND char_length(rationale_text) <= 2000))",
            name="ck_companion_proposals_text",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "proposed_effect IN "
            "('discussion_only', 'check', 'measurement', 'follow_up', 'none')",
            name="ck_companion_proposals_effect",
        ),
        CheckConstraint(
            "((proposed_effect IN ('check', 'measurement', 'follow_up') "
            "AND task_display_text IS NOT NULL "
            "AND btrim(task_display_text) <> '' "
            "AND char_length(task_display_text) <= 2000) OR "
            "(proposed_effect IN ('discussion_only', 'none') "
            "AND task_display_text IS NULL))",
            name="ck_companion_proposals_task_text",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "suggested_resolution IN ('keep_open', 'resolved')",
            name="ck_companion_proposals_resolution",
        ),
        CheckConstraint(
            "source_message_id = source_classification_message_id",
            name="ck_companion_proposals_message_classification_identity",
        ),
        CheckConstraint(
            "jsonb_typeof(source_refs) = 'array' "
            "AND jsonb_array_length(source_refs) BETWEEN 3 AND 6",
            name="ck_companion_proposals_source_refs",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "run_request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_companion_proposals_run_fingerprint",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(created_event_ref) = 'object' AND "
            "(superseded_event_ref IS NULL OR "
            "jsonb_typeof(superseded_event_ref) = 'object')",
            name="ck_companion_proposals_event_refs",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "((state = 'pending' AND record_version = 1 "
            "AND terminal_at IS NULL AND decision_record_id IS NULL "
            "AND superseded_event_ref IS NULL) OR "
            "(state IN ('approved', 'rejected') AND record_version = 2 "
            "AND terminal_at IS NOT NULL AND decision_record_id IS NOT NULL "
            "AND superseded_event_ref IS NULL) OR "
            "(state = 'superseded' AND record_version = 2 "
            "AND terminal_at IS NOT NULL AND decision_record_id IS NULL "
            "AND superseded_event_ref IS NOT NULL))",
            name="ck_companion_proposals_state_matrix",
        ),
        UniqueConstraint(
            "issue_id",
            "proposal_sequence",
            name="uq_companion_proposals_issue_sequence",
        ),
        UniqueConstraint(
            "source_run_id",
            name="uq_companion_proposals_source_run",
        ),
        UniqueConstraint(
            "source_message_id",
            name="uq_companion_proposals_source_message",
        ),
        UniqueConstraint(
            "source_classification_message_id",
            name="uq_companion_proposals_source_classification",
        ),
        Index(
            "uq_companion_proposals_one_pending_per_issue",
            "issue_id",
            unique=True,
            postgresql_where=text("state = 'pending'"),
        ),
    )

    proposal_id: Mapped[uuid.UUID] = mapped_column(
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
    issue_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companion_issues.issue_id", ondelete="RESTRICT"),
        nullable=False,
    )
    attention_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "companion_human_attention.attention_id",
            name="fk_companion_proposals_attention",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    proposal_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    record_version: Mapped[int] = mapped_column(Integer, nullable=False)
    proposal_summary: Mapped[str] = mapped_column(Text, nullable=False)
    proposal_text: Mapped[str] = mapped_column(Text, nullable=False)
    rationale_text: Mapped[str | None] = mapped_column(Text)
    proposed_effect: Mapped[str] = mapped_column(String(24), nullable=False)
    task_display_text: Mapped[str | None] = mapped_column(Text)
    suggested_resolution: Mapped[str] = mapped_column(String(16), nullable=False)
    source_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    source_message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    source_classification_message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("safety_classifications.message_id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_refs: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False)
    run_request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    terminal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_record_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "decision_records.decision_record_id",
            name="fk_companion_proposals_decision",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
    )
    created_event_ref: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    superseded_event_ref: Mapped[dict[str, object] | None] = mapped_column(
        JSON_DOCUMENT
    )


class DecisionRecord(Base):
    __tablename__ = "decision_records"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_decision_records_decision",
        ),
        CheckConstraint(
            "btrim(decision_summary) <> '' "
            "AND char_length(decision_summary) <= 500",
            name="ck_decision_records_summary",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "allowed_workflow_effect IN "
            "('discussion_only', 'check', 'measurement', 'follow_up', 'none')",
            name="ck_decision_records_effect",
        ),
        CheckConstraint(
            "issue_resolution IN ('keep_open', 'resolved')",
            name="ck_decision_records_resolution",
        ),
        CheckConstraint(
            "workflow_effect_ref IS NULL OR workflow_effect_ref ~ "
            "'^task:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
            "[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="ck_decision_records_workflow_effect_ref",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "((decision = 'approved' "
            "AND ((allowed_workflow_effect IN "
            "('check', 'measurement', 'follow_up') "
            "AND workflow_effect_ref IS NOT NULL) OR "
            "(allowed_workflow_effect IN ('discussion_only', 'none') "
            "AND workflow_effect_ref IS NULL))) OR "
            "(decision = 'rejected' AND allowed_workflow_effect = 'none' "
            "AND workflow_effect_ref IS NULL))",
            name="ck_decision_records_effect_matrix",
        ),
        CheckConstraint(
            "decider_role_preset IN ('boss', 'engineer')",
            name="ck_decision_records_role",
        ),
        CheckConstraint(
            "decider_permission_source IN "
            "('boss_role', 'plant_access_grant')",
            name="ck_decision_records_permission_source",
        ),
        CheckConstraint(
            "((decider_permission_source = 'boss_role' "
            "AND decider_role_preset = 'boss' AND decider_grant_id IS NULL) OR "
            "(decider_permission_source = 'plant_access_grant' "
            "AND decider_role_preset = 'engineer' "
            "AND decider_grant_id IS NOT NULL))",
            name="ck_decision_records_permission_matrix",
        ),
        CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_decision_records_request_fingerprint",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(source_refs) = 'array' "
            "AND jsonb_array_length(source_refs) BETWEEN 5 AND 7",
            name="ck_decision_records_source_refs",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(decision_event_ref) = 'object'",
            name="ck_decision_records_event_ref",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "safety_gate_authority = 'not_granted'",
            name="ck_decision_records_no_safety_authority",
        ),
        UniqueConstraint(
            "proposal_id",
            name="uq_decision_records_proposal",
        ),
        UniqueConstraint(
            "request_id",
            name="uq_decision_records_request",
        ),
    )

    decision_record_id: Mapped[uuid.UUID] = mapped_column(
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
    issue_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companion_issues.issue_id", ondelete="RESTRICT"),
        nullable=False,
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companion_proposals.proposal_id", ondelete="RESTRICT"),
        nullable=False,
    )
    attention_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companion_human_attention.attention_id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    decision_summary: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_workflow_effect: Mapped[str] = mapped_column(String(24), nullable=False)
    issue_resolution: Mapped[str] = mapped_column(String(16), nullable=False)
    workflow_effect_ref: Mapped[str | None] = mapped_column(Text)
    decider_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.account_id", ondelete="RESTRICT"),
        nullable=False,
    )
    decider_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farm_memberships.membership_id", ondelete="RESTRICT"),
        nullable=False,
    )
    decider_role_preset: Mapped[str] = mapped_column(String(16), nullable=False)
    decider_permission_source: Mapped[str] = mapped_column(String(32), nullable=False)
    decider_grant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plant_access_grants.grant_id", ondelete="RESTRICT"),
    )
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_refs: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False)
    decision_event_ref: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    safety_gate_authority: Mapped[str] = mapped_column(
        String(16), nullable=False, default="not_granted"
    )


__all__ = [
    "CompanionHumanAttention",
    "CompanionIssue",
    "CompanionProposal",
    "DecisionRecord",
]
