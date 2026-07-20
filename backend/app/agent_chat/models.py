from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import (
    Boolean,
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


class AgentIntroductionBatch(Base):
    __tablename__ = "agent_introduction_batches"
    __table_args__ = (
        CheckConstraint(
            "roster_version > 0",
            name="ck_agent_introduction_batches_roster_version_positive",
        ),
        CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_agent_introduction_batches_content_sha256_lower_hex",
        ).ddl_if(dialect="postgresql"),
        UniqueConstraint(
            "plant_id",
            "roster_version",
            name="uq_agent_introduction_batches_plant_roster",
        ),
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
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
    roster_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UIFeedEvent(Base):
    __tablename__ = "ui_feed_events"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('system', 'agent_message', 'safety')",
            name="ck_ui_feed_events_source_type",
        ),
        CheckConstraint(
            "display_kind IN "
            "('agent_introduction', 'agent_message', 'block_notice', 'safety_status')",
            name="ck_ui_feed_events_display_kind",
        ),
        CheckConstraint(
            "((source_type = 'system' AND display_kind = 'agent_introduction') OR "
            "(source_type = 'agent_message' AND display_kind = 'agent_message') OR "
            "(source_type = 'safety' "
            "AND display_kind IN ('block_notice', 'safety_status')))",
            name="ck_ui_feed_events_source_display",
        ),
        CheckConstraint(
            "visible_to_agents IS FALSE",
            name="ck_ui_feed_events_visible_to_agents_false",
        ),
        CheckConstraint(
            "consumable_by_agents IS FALSE",
            name="ck_ui_feed_events_consumable_by_agents_false",
        ),
        CheckConstraint(
            "((display_kind = 'agent_introduction' AND agent_id IS NOT NULL "
            "AND roster_version IS NOT NULL AND roster_version > 0) OR "
            "(display_kind <> 'agent_introduction' AND agent_id IS NULL "
            "AND roster_version IS NULL))",
            name="ck_ui_feed_events_introduction_shape",
        ),
        CheckConstraint(
            "jsonb_typeof(source_refs) = 'array'",
            name="ck_ui_feed_events_source_refs_array",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(display_payload) = 'object'",
            name="ck_ui_feed_events_display_payload_object",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(visible_to_roles) = 'array'",
            name="ck_ui_feed_events_visible_to_roles_array",
        ).ddl_if(dialect="postgresql"),
        UniqueConstraint(
            "plant_id",
            "agent_id",
            "roster_version",
            name="uq_ui_feed_events_plant_agent_roster",
        ),
        Index("ix_ui_feed_events_plant_created", "plant_id", "created_at", "ui_event_id"),
    )

    ui_event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[list[str]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=list, server_default=text("'[]'")
    )
    display_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    display_payload: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict, server_default=text("'{}'")
    )
    visible_to_roles: Mapped[list[str]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=list, server_default=text("'[]'")
    )
    visible_to_agents: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    consumable_by_agents: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    roster_version: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AgentBusEvent(Base):
    __tablename__ = "agent_bus_events"
    __table_args__ = (
        CheckConstraint(
            "consumable_by_agents IS TRUE",
            name="ck_agent_bus_events_consumable_by_agents_true",
        ),
        CheckConstraint(
            "jsonb_typeof(actor_ref) = 'object' OR actor_ref IS NULL",
            name="ck_agent_bus_events_actor_ref_object",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_agent_bus_events_payload_object",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(source_refs) = 'array'",
            name="ck_agent_bus_events_source_refs_array",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(authorization_scope) = 'object'",
            name="ck_agent_bus_events_authorization_scope_object",
        ).ddl_if(dialect="postgresql"),
        UniqueConstraint(
            "plant_id",
            "source_type",
            "source_id",
            "event_type",
            name="uq_agent_bus_events_source_event",
        ),
        Index("ix_agent_bus_events_plant_created", "plant_id", "created_at", "event_id"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    actor_ref: Mapped[dict[str, object] | None] = mapped_column(
        JSON_DOCUMENT, nullable=True
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    source_refs: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False)
    authorization_scope: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    consumable_by_agents: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )


__all__ = ["AgentBusEvent", "AgentIntroductionBatch", "UIFeedEvent"]
