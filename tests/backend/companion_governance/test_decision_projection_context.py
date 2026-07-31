from __future__ import annotations

import uuid

from sqlalchemy import select

from backend.app.access_admin.context_builders import build_current_agent_bus_context
from backend.app.agent_chat import AgentBusEvent, UIFeedEvent
from backend.app.companion_governance import (
    CompanionGovernanceService,
    DecideCompanionProposalCommandV1,
)
from tests.backend.companion_governance.conftest import (
    FT013_NOW,
    TimelineRecorder,
    ft013_database,
    ft013_seed,
    make_proposal_command,
    seed_companion_classification,
)
from tests.backend.plant_operations.conftest import archive_plant


def _decide(database, farm, boss, plant, *, decision="approved"):
    message_id = seed_companion_classification(
        database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        effect="discussion_only",
    )
    with database.session() as session:
        service = CompanionGovernanceService(
            session,
            timeline_appender=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        )
        persisted = service.persist_companion_proposal(
            make_proposal_command(
                boss,
                plant_id=plant.plant_id,
                message_id=message_id,
                effect="discussion_only",
            )
        )
        result = service.decide_companion_proposal(
            DecideCompanionProposalCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                proposal_id=persisted.proposal_id,
                request_id=uuid.uuid4(),
                expected_version=1,
                decision=decision,
                decision_summary="Подтверждено человеком.",
                issue_resolution="keep_open",
            )
        )
    return persisted, result


def test_approved_decision_bus_resolves_exact_summary_and_detail_conclusion(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    persisted, decided = _decide(ft013_database, farm, boss, plant)
    with ft013_database.session() as session:
        context = build_current_agent_bus_context(
            session,
            boss,
            plant_id=plant.plant_id,
        )
        detail = CompanionGovernanceService(session).get_issue_detail(
            boss,
            plant_id=plant.plant_id,
            issue_id=persisted.issue_id,
        )
        bus = session.scalar(select(AgentBusEvent))
        decision_ui = session.get(
            UIFeedEvent,
            uuid.UUID(str(decided.decision_record["decision_record_id"])),
        )

    assert context is not None and len(context.records) == 1
    summary = context.records[0].payload
    assert list(summary) == [
        "schema_version",
        "decision_record_id",
        "decision_record_ref",
        "plant_id",
        "plant_ref",
        "issue_id",
        "issue_ref",
        "proposal_id",
        "proposal_ref",
        "proposal_version",
        "decision",
        "decision_summary",
        "allowed_workflow_effect",
        "decider_role_preset",
        "decided_at",
        "source_refs",
        "safety_gate_authority",
    ]
    assert summary["decision"] == "approved"
    assert summary["safety_gate_authority"] == "not_granted"
    assert "proposal_text" not in summary
    assert bus is not None
    assert bus.actor_ref is None and bus.authorization_scope is None
    assert decision_ui is not None
    assert decision_ui.display_payload["payload_kind"] == "companion_decision"
    value = detail.as_value()
    assert value["attention"]["status"] == "satisfied"
    assert value["attention"]["current_proposal_ref"] == (
        f"companion_proposal:{persisted.proposal_id}"
    )
    assert len(value["decision_records"]) == 1
    assert value["conclusion"]["conclusion_status"] == "decided"
    assert value["conclusion"]["latest_decision_record_ref"] == (
        decided.decision_record["decision_record_ref"]
    )


def test_rejected_decision_has_ui_history_but_no_bus_or_agent_context(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    _persisted, decided = _decide(
        ft013_database,
        farm,
        boss,
        plant,
        decision="rejected",
    )
    with ft013_database.session() as session:
        context = build_current_agent_bus_context(
            session,
            boss,
            plant_id=plant.plant_id,
        )
        buses = list(session.scalars(select(AgentBusEvent)))
        ui = session.get(
            UIFeedEvent,
            uuid.UUID(str(decided.decision_record["decision_record_id"])),
        )
    assert context is not None and context.records == ()
    assert buses == []
    assert ui is not None


def test_archived_plant_omits_previously_approved_decision_context(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    _decide(ft013_database, farm, boss, plant)
    archive_plant(ft013_database, boss, plant_id=plant.plant_id)
    with ft013_database.session() as session:
        assert (
            build_current_agent_bus_context(
                session,
                boss,
                plant_id=plant.plant_id,
            )
            is None
        )
