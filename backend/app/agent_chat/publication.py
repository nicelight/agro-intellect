from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ..access_admin.actor_context import ActorContext
from ..agent_runtime.contracts import MessageEnvelopeV1, SafetyClassificationResultV1
from ..database import DatabaseHandle
from .authorization import lock_current_plant_authorization
from .contracts import BusEventEnvelopeV1, UIFeedEventV1
from .models import AgentBusEvent, UIFeedEvent


@dataclass(frozen=True, slots=True)
class PublicationResult:
    status: str
    reason_code: str | None = None
    bus_event_id: uuid.UUID | None = None
    ui_event_id: uuid.UUID | None = None


class GuardedAgentPublicationService:
    def __init__(self, database: DatabaseHandle) -> None:
        self._database = database

    def publish(self, actor: ActorContext, envelope: MessageEnvelopeV1, classification: SafetyClassificationResultV1) -> PublicationResult:
        if not isinstance(envelope, MessageEnvelopeV1) or not isinstance(classification, SafetyClassificationResultV1) or classification.message_id != envelope.message_id or envelope.farm_id != actor.farm_id:
            return PublicationResult("rejected", "handoff_invalid")
        if classification.classification in {"safe_task_request", "physical_action"}:
            return PublicationResult("no_effect")
        bus_id = uuid.uuid4() if classification.classification == "safe_information" else None
        ui_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        try:
            with self._database.session() as session:
                with session.begin():
                    auth = lock_current_plant_authorization(session, actor, envelope.plant_id, allow_archived=False)
                    if auth is None:
                        return PublicationResult("rejected", "plant_not_publishable")
                    existing_ui = session.scalar(select(UIFeedEvent).where(UIFeedEvent.plant_id == envelope.plant_id, UIFeedEvent.source_id == str(envelope.message_id), UIFeedEvent.display_kind == ("agent_message" if bus_id else "block_notice")).with_for_update())
                    existing_bus = session.scalar(select(AgentBusEvent).where(AgentBusEvent.plant_id == envelope.plant_id, AgentBusEvent.source_type == "message_envelope", AgentBusEvent.source_id == str(envelope.message_id), AgentBusEvent.event_type == "agent_safe_information").with_for_update()) if bus_id else None
                    expected_ui = _ui_value(ui_id, now, envelope, classification)
                    expected_bus = _bus_value(bus_id, now, actor, auth.scope_value(), envelope, classification) if bus_id else None
                    if existing_ui is not None or existing_bus is not None:
                        if _stored_ui_matches(existing_ui, expected_ui) and (expected_bus is None or _stored_bus_matches(existing_bus, expected_bus)):
                            return PublicationResult("duplicate", bus_event_id=existing_bus.event_id if existing_bus else None, ui_event_id=existing_ui.ui_event_id)
                        return PublicationResult("rejected", "content_conflict")
                    ui = UIFeedEventV1.from_untrusted(expected_ui)
                    session.add(UIFeedEvent(ui_event_id=ui.ui_event_id, farm_id=ui.farm_id, plant_id=ui.plant_id, created_at=ui.created_at, source_type=ui.source_type, source_id=ui.source_id, source_refs=list(ui.source_refs), display_kind=ui.display_kind, display_payload=dict(ui.display_payload), visible_to_roles=list(ui.visible_to_roles), visible_to_agents=False, consumable_by_agents=False, agent_id=None, roster_version=None))
                    if expected_bus is not None:
                        bus = BusEventEnvelopeV1.from_untrusted(expected_bus)
                        session.add(AgentBusEvent(event_id=bus.event_id, farm_id=bus.farm_id, plant_id=bus.plant_id, created_at=bus.created_at, event_type=bus.event_type, source_type=bus.source_type, source_id=bus.source_id, actor_ref=dict(bus.actor_ref) if bus.actor_ref else None, payload=dict(bus.payload), source_refs=list(bus.source_refs), authorization_scope=dict(bus.authorization_scope), consumable_by_agents=True))
                    session.flush()
            return PublicationResult("accepted", bus_event_id=bus_id, ui_event_id=ui_id)
        except (SQLAlchemyError, ValueError, TypeError):
            return PublicationResult("failed", "persistence_failed")


def _ui_value(event_id, now, envelope, classification):
    blocked = classification.classification == "blocked_uncertain"
    return {"schema_version": 1, "ui_event_id": str(event_id), "created_at": now.isoformat().replace("+00:00", "Z"), "farm_id": str(envelope.farm_id), "plant_id": str(envelope.plant_id), "source_type": "safety" if blocked else "agent_message", "source_id": str(envelope.message_id), "source_refs": [f"message_envelope:{envelope.message_id}", f"safety_classification:{classification.message_id}"], "display_kind": "block_notice" if blocked else "agent_message", "display_payload": {"payload_kind": "block_notice", "notice_code": "classification_uncertain", "text": "Сообщение заблокировано до уточнения безопасности."} if blocked else {"payload_kind": "agent_message", "agent_id": envelope.agent_id, "candidate_claim_type": envelope.candidate_claim_type, "quoted_text": envelope.candidate_output}, "visible_to_roles": ["boss", "engineer", "consultant"], "visible_to_agents": False, "consumable_by_agents": False}


def _bus_value(event_id, now, actor, scope, envelope, classification):
    return {"schema_version": 1, "event_id": str(event_id), "event_type": "agent_safe_information", "created_at": now.isoformat().replace("+00:00", "Z"), "farm_id": str(envelope.farm_id), "plant_id": str(envelope.plant_id), "actor_ref": {"account_id": str(actor.account_id), "membership_id": str(actor.membership_id), "role_preset": actor.role_preset.value}, "source_type": "message_envelope", "source_id": str(envelope.message_id), "payload": {"payload_kind": "quoted_candidate", "message_id": str(envelope.message_id), "classification_ref": f"safety_classification:{classification.message_id}", "candidate_claim_type": envelope.candidate_claim_type, "quoted_text": envelope.candidate_output}, "source_refs": [f"message_envelope:{envelope.message_id}", f"safety_classification:{classification.message_id}"], "consumable_by_agents": True, "authorization_scope": scope}


def _stored_ui_matches(row, expected):
    return row is not None and row.farm_id == uuid.UUID(expected["farm_id"]) and row.source_refs == expected["source_refs"] and row.display_payload == expected["display_payload"] and row.visible_to_agents is False and row.consumable_by_agents is False


def _stored_bus_matches(row, expected):
    return row is not None and row.farm_id == uuid.UUID(expected["farm_id"]) and row.actor_ref == expected["actor_ref"] and row.payload == expected["payload"] and row.source_refs == expected["source_refs"] and row.authorization_scope == expected["authorization_scope"] and row.consumable_by_agents is True


__all__ = ["GuardedAgentPublicationService", "PublicationResult"]
