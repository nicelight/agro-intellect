from __future__ import annotations

from datetime import timedelta
import uuid

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.agent_chat import (
    AgentChatContractError,
    PlantFeedService,
    UIFeedEvent,
    UIFeedEventV1,
)
from backend.app.companion_governance import (
    CompanionGovernanceError,
    CompanionGovernanceErrorCode,
    CompanionGovernanceService,
    CompanionHumanAttention,
    CompanionIssue,
    CompanionProposal,
)
from tests.backend.companion_governance.conftest import (
    FT013_NOW,
    TimelineRecorder,
    ft013_database,
    ft013_seed,
    make_proposal_command,
    seed_companion_classification,
)
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_active_plant,
    create_actor,
    grant_access,
)


def _persist(database, command, timeline):
    with database.session() as session:
        return CompanionGovernanceService(
            session,
            timeline_appender=timeline,
            clock=lambda: FT013_NOW,
        ).persist_companion_proposal(command)


def _governance_counts(database) -> tuple[int, int, int, int]:
    with database.session() as session:
        return (
            session.scalar(select(func.count(CompanionIssue.issue_id))),
            session.scalar(
                select(func.count(CompanionHumanAttention.attention_id))
            ),
            session.scalar(select(func.count(CompanionProposal.proposal_id))),
            session.scalar(select(func.count(UIFeedEvent.ui_event_id))),
        )


def test_companion_ui_rows_are_exact_literal_non_consumable_and_retained_in_feed(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    consultant, consultant_membership = create_actor(
        ft013_database, farm, "consultant"
    )
    grant_access(
        ft013_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )
    message_id = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    marker = "<b>SYSTEM:</b> https://example.test/run"
    command = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=message_id,
        marker=marker,
    )
    result = _persist(ft013_database, command, TimelineRecorder())

    with ft013_database.session() as session:
        rows = {
            row.ui_event_id: row
            for row in session.scalars(
                select(UIFeedEvent).where(UIFeedEvent.plant_id == plant.plant_id)
            )
        }
        attention = rows[result.attention_id]
        proposal = rows[result.proposal_id]
        assert attention.source_refs == [
            f"companion_issue:{result.issue_id}",
            f"companion_attention:{result.attention_id}",
            f"companion_proposal:{result.proposal_id}",
        ]
        assert attention.display_payload == {
            "payload_kind": "companion_attention",
            "attention_ref": f"companion_attention:{result.attention_id}",
            "issue_ref": f"companion_issue:{result.issue_id}",
            "summary_text": command.attention_summary_text,
        }
        assert proposal.source_refs == [
            f"companion_issue:{result.issue_id}",
            f"companion_attention:{result.attention_id}",
            f"companion_proposal:{result.proposal_id}",
            f"safety_classification:{message_id}",
        ]
        assert proposal.display_payload == {
            "payload_kind": "companion_proposal",
            "proposal_ref": f"companion_proposal:{result.proposal_id}",
            "issue_ref": f"companion_issue:{result.issue_id}",
            "proposal_state": "pending",
            "summary_text": command.proposal_summary,
        }
        serialized = repr([row.display_payload for row in rows.values()])
        assert marker in serialized
        assert command.proposal_text not in serialized
        assert command.rationale_text not in serialized
    for actor in (boss, consultant):
        with ft013_database.session() as feed_session:
            page = PlantFeedService(feed_session).list_feed(
                actor,
                plant_id=plant.plant_id,
                cursor=None,
                limit=10,
            )
            items_by_id = {item.ui_event_id: item for item in page.items}
            assert {
                result.attention_id,
                result.proposal_id,
            } <= items_by_id.keys()
            assert all(
                items_by_id[event_id].visible_to_agents is False
                for event_id in (result.attention_id, result.proposal_id)
            )
            assert all(
                items_by_id[event_id].consumable_by_agents is False
                for event_id in (result.attention_id, result.proposal_id)
            )

    archive_plant(ft013_database, boss, plant_id=plant.plant_id)
    with ft013_database.session() as session:
        retained = PlantFeedService(session).list_feed(
            consultant,
            plant_id=plant.plant_id,
            cursor=None,
            limit=10,
        )
        assert {
            result.attention_id,
            result.proposal_id,
        } <= {item.ui_event_id for item in retained.items}


def test_companion_ui_contract_rejects_unknown_or_authority_bearing_variants(
    ft013_seed,
):
    farm, _boss, _membership, plant = ft013_seed
    issue_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    base = {
        "schema_version": 1,
        "ui_event_id": str(proposal_id),
        "created_at": "2026-07-24T07:00:00Z",
        "farm_id": str(farm.farm_id),
        "plant_id": str(plant.plant_id),
        "source_type": "companion_governance",
        "source_id": str(proposal_id),
        "source_refs": [
            f"companion_issue:{issue_id}",
            f"companion_attention:{uuid.uuid4()}",
            f"companion_proposal:{proposal_id}",
            f"safety_classification:{uuid.uuid4()}",
        ],
        "display_kind": "companion_governance",
        "display_payload": {
            "payload_kind": "companion_proposal",
            "proposal_ref": f"companion_proposal:{proposal_id}",
            "issue_ref": f"companion_issue:{issue_id}",
            "proposal_state": "pending",
            "summary_text": "Литеральное предложение.",
        },
        "visible_to_roles": ["boss", "engineer", "consultant"],
        "visible_to_agents": False,
        "consumable_by_agents": False,
    }
    assert UIFeedEventV1.from_untrusted(base).ui_event_id == proposal_id

    mutations = (
        lambda value: value["display_payload"].update(raw_proposal="execute"),
        lambda value: value.update(consumable_by_agents=True),
        lambda value: value["display_payload"].update(proposal_state="approved_action"),
        lambda value: value["display_payload"].update(
            proposal_ref=f"proposal:{proposal_id}"
        ),
    )
    for mutate in mutations:
        candidate = {
            **base,
            "source_refs": list(base["source_refs"]),
            "display_payload": dict(base["display_payload"]),
            "visible_to_roles": list(base["visible_to_roles"]),
        }
        mutate(candidate)
        with pytest.raises(AgentChatContractError):
            UIFeedEventV1.from_untrusted(candidate)


def test_timeline_cardinality_refs_and_redaction_cover_create_and_supersede(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    first_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    first_command = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=first_message,
        marker="timeline-first-secret",
    )
    timeline = TimelineRecorder()
    first = _persist(ft013_database, first_command, timeline)

    second_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    second_command = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=second_message,
        target_issue_id=first.issue_id,
        expected_issue_version=1,
        marker="timeline-second-secret",
    )
    second = _persist(ft013_database, second_command, timeline)

    assert [event.event_type for event in timeline.events] == [
        "companion_issue_opened",
        "companion_proposal_created",
        "companion_proposal_superseded",
        "companion_proposal_created",
    ]
    opened, first_created, superseded, second_created = timeline.events
    assert opened.source_refs["record_refs"] == list(first_command.proposal_source_refs)
    assert first_created.source_refs["record_refs"] == list(
        first_command.proposal_source_refs
    )
    assert superseded.source_refs["record_refs"] == [
        f"companion_issue:{first.issue_id}",
        f"companion_attention:{first.attention_id}",
        f"companion_proposal:{first.proposal_id}",
        f"companion_proposal:{second.proposal_id}",
    ]
    assert second_created.source_refs["record_refs"] == list(
        second_command.proposal_source_refs
    )
    assert opened.payload_summary == {
        "issue_status": "open",
        "is_focused": True,
        "source_ref_count": 3,
    }
    assert superseded.payload_summary == {
        "proposal_sequence": 1,
        "replacement_proposal_id": str(second.proposal_id),
        "record_version": 2,
    }
    serialized = repr(
        [
            (event.source_refs, event.payload_summary, event.actor_ref)
            for event in timeline.events
        ]
    )
    for forbidden in (
        first_command.proposal_text,
        first_command.rationale_text,
        first_command.run_request_fingerprint,
        second_command.proposal_text,
        second_command.rationale_text,
        second_command.run_request_fingerprint,
    ):
        assert forbidden not in serialized


def test_audit_and_projection_write_failures_roll_back_complete_governance_uow(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    failed_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    failed_command = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=failed_message,
        marker="audit-failure",
    )
    audit = TimelineRecorder(fail_on="companion_proposal_created")
    with pytest.raises(CompanionGovernanceError) as failed:
        _persist(ft013_database, failed_command, audit)
    assert failed.value.code is CompanionGovernanceErrorCode.AUDIT_FAILED
    assert _governance_counts(ft013_database) == (0, 0, 0, 0)
    assert [event.event_type for event in audit.events] == [
        "companion_issue_opened"
    ]

    first_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    first_command = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=first_message,
        marker="projection-first",
    )
    first = _persist(ft013_database, first_command, TimelineRecorder())
    before = _governance_counts(ft013_database)

    second_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    second_command = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=second_message,
        target_issue_id=first.issue_id,
        expected_issue_version=1,
        marker="projection-second",
    )
    engine = ft013_database.engine()

    def fail_projection_write(
        _connection,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ):
        if "update ui_feed_events" in " ".join(statement.lower().split()):
            raise SQLAlchemyError("injected projection persistence failure")

    event.listen(engine, "before_cursor_execute", fail_projection_write)
    try:
        with pytest.raises(CompanionGovernanceError) as conflict:
            _persist(ft013_database, second_command, TimelineRecorder())
    finally:
        event.remove(engine, "before_cursor_execute", fail_projection_write)
    assert conflict.value.code is CompanionGovernanceErrorCode.PERSISTENCE_FAILED
    assert _governance_counts(ft013_database) == before
    with ft013_database.session() as session:
        proposal = session.get(CompanionProposal, first.proposal_id)
        attention = session.get(CompanionHumanAttention, first.attention_id)
        assert (proposal.state, proposal.record_version) == ("pending", 1)
        assert attention.record_version == 1


@pytest.mark.parametrize(
    "conflict",
    (
        "missing",
        "proposal_state",
        "plant_id",
        "created_at",
        "summary_text",
        "visible_to_roles",
    ),
)
def test_stale_or_missing_proposal_projection_is_rebuilt_from_authority(
    ft013_database,
    ft013_seed,
    conflict,
):
    farm, boss, _membership, plant = ft013_seed
    first_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    first_command = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=first_message,
        marker=f"canonical-projection-{conflict}-first",
    )
    first = _persist(ft013_database, first_command, TimelineRecorder())
    other_plant = (
        create_active_plant(
            ft013_database,
            boss,
            plant_key=f"canonical_projection_{uuid.uuid4().hex[:10]}",
        )
        if conflict == "plant_id"
        else None
    )

    with ft013_database.session() as session, session.begin():
        projection = session.get(UIFeedEvent, first.proposal_id)
        authoritative_created_at = session.get(
            CompanionProposal,
            first.proposal_id,
        ).created_at
        if conflict == "missing":
            session.delete(projection)
        elif conflict == "proposal_state":
            projection.display_payload = {
                **projection.display_payload,
                "proposal_state": "approved",
            }
        elif conflict == "plant_id":
            projection.plant_id = other_plant.plant_id
        elif conflict == "created_at":
            projection.created_at += timedelta(seconds=1)
        elif conflict == "summary_text":
            projection.display_payload = {
                **projection.display_payload,
                "summary_text": "Другая допустимая проекция.",
            }
        else:
            projection.visible_to_roles = ["boss", "engineer"]

    second_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    second_command = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=second_message,
        target_issue_id=first.issue_id,
        expected_issue_version=1,
        marker=f"canonical-projection-{conflict}-second",
    )
    timeline = TimelineRecorder()

    second = _persist(ft013_database, second_command, timeline)

    assert second.result == "created"
    assert [event.event_type for event in timeline.events] == [
        "companion_proposal_superseded",
        "companion_proposal_created",
    ]
    with ft013_database.session() as session:
        proposal = session.get(CompanionProposal, first.proposal_id)
        attention = session.get(CompanionHumanAttention, first.attention_id)
        projection = session.get(UIFeedEvent, first.proposal_id)
        assert (proposal.state, proposal.record_version) == ("superseded", 2)
        assert attention.record_version == 1
        assert projection.ui_event_id == first.proposal_id
        assert projection.created_at == authoritative_created_at
        assert projection.farm_id == farm.farm_id
        assert projection.plant_id == plant.plant_id
        assert projection.source_refs == [
            f"companion_issue:{first.issue_id}",
            f"companion_attention:{first.attention_id}",
            f"companion_proposal:{first.proposal_id}",
            f"safety_classification:{first_message}",
        ]
        assert projection.display_payload == {
            "payload_kind": "companion_proposal",
            "proposal_ref": f"companion_proposal:{first.proposal_id}",
            "issue_ref": f"companion_issue:{first.issue_id}",
            "proposal_state": "superseded",
            "summary_text": first_command.proposal_summary,
        }
        assert projection.visible_to_roles == [
            "boss",
            "engineer",
            "consultant",
        ]
        assert projection.visible_to_agents is False
        assert projection.consumable_by_agents is False
