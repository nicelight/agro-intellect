from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event, current_thread
import uuid

import pytest
from sqlalchemy import event, func, select

from backend.app.access_admin.models import Plant, PlantAccessGrant
from backend.app.access_admin.farm_service import FarmService
from backend.app.agent_chat import AgentBusEvent, UIFeedEvent
from backend.app.companion_governance import (
    CompanionGovernanceError,
    CompanionGovernanceErrorCode,
    CompanionGovernanceService,
    CompanionGovernanceValidationError,
    CompanionHumanAttention,
    CompanionIssue,
    CompanionProposal,
    DecisionRecord,
)
from backend.app.safety_gate import SafetyActionDecision
from backend.app.task_follow_up import Task
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
    revoke_access,
)


def _persist(database, command, timeline=None):
    timeline = timeline or TimelineRecorder()
    with database.session() as session:
        result = CompanionGovernanceService(
            session,
            timeline_appender=timeline,
            clock=lambda: FT013_NOW,
        ).persist_companion_proposal(command)
    return result, timeline


def _counts(database) -> dict[str, int]:
    with database.session() as session:
        return {
            "issues": session.scalar(select(func.count(CompanionIssue.issue_id))),
            "attentions": session.scalar(
                select(func.count(CompanionHumanAttention.attention_id))
            ),
            "proposals": session.scalar(
                select(func.count(CompanionProposal.proposal_id))
            ),
            "decisions": session.scalar(
                select(func.count(DecisionRecord.decision_record_id))
            ),
            "ui": session.scalar(select(func.count(UIFeedEvent.ui_event_id))),
            "bus": session.scalar(select(func.count(AgentBusEvent.event_id))),
            "tasks": session.scalar(select(func.count(Task.task_id))),
            "safety_actions": session.scalar(
                select(func.count(SafetyActionDecision.decision_id))
            ),
        }


def test_strict_handoff_rejects_caller_added_cross_plant_ref_before_writes(
    ft013_database,
    ft013_seed,
):
    _farm, boss, _membership, plant = ft013_seed
    other_plant = create_active_plant(
        ft013_database,
        boss,
        plant_key=f"ft013_cross_ref_{uuid.uuid4().hex[:10]}",
    )
    canonical = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=uuid.uuid4(),
        marker="cross-plant-provider-ref",
    )
    before = _counts(ft013_database)

    with pytest.raises(CompanionGovernanceValidationError):
        replace(
            canonical,
            provider_input_refs=(
                f"plant:{plant.plant_id}",
                f"plant:{other_plant.plant_id}",
            ),
        )

    assert _counts(ft013_database) == before


def test_new_issue_proposal_is_one_atomic_governance_effect_with_no_forbidden_authority(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    message_id = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    command = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=message_id,
    )
    result, timeline = _persist(ft013_database, command)

    assert result.result == "created"
    assert result.classification_message_id == message_id
    assert _counts(ft013_database) == {
        "issues": 1,
        "attentions": 1,
        "proposals": 1,
        "decisions": 0,
        "ui": 2,
        "bus": 0,
        "tasks": 0,
        "safety_actions": 0,
    }
    with ft013_database.session() as session:
        issue = session.get(CompanionIssue, result.issue_id)
        attention = session.get(CompanionHumanAttention, result.attention_id)
        proposal = session.get(CompanionProposal, result.proposal_id)
        ui_rows = list(
            session.scalars(
                select(UIFeedEvent).order_by(UIFeedEvent.created_at, UIFeedEvent.ui_event_id)
            )
        )
        assert (
            issue.status,
            issue.is_focused,
            issue.record_version,
        ) == ("open", True, 1)
        assert (
            attention.status,
            attention.attention_sequence,
            attention.current_proposal_id,
            attention.record_version,
        ) == ("active", 1, proposal.proposal_id, 1)
        assert (
            proposal.state,
            proposal.proposal_sequence,
            proposal.record_version,
        ) == ("pending", 1, 1)
        assert proposal.source_refs == [
            f"plant:{plant.plant_id}",
            f"message_envelope:{message_id}",
            f"safety_classification:{message_id}",
        ]
        assert {row.ui_event_id for row in ui_rows} == {
            attention.attention_id,
            proposal.proposal_id,
        }
        assert all(row.visible_to_agents is False for row in ui_rows)
        assert all(row.consumable_by_agents is False for row in ui_rows)
        assert all(
            row.visible_to_roles == ["boss", "engineer", "consultant"]
            for row in ui_rows
        )

    assert [event.event_type for event in timeline.events] == [
        "companion_issue_opened",
        "companion_proposal_created",
    ]
    assert all(event.actor_ref["account_id"] == str(boss.account_id) for event in timeline.events)
    serialized_events = repr(
        [
            {
                "source_refs": event.source_refs,
                "payload_summary": event.payload_summary,
            }
            for event in timeline.events
        ]
    )
    for forbidden in (
        command.issue_summary_text,
        command.attention_summary_text,
        command.proposal_summary,
        command.proposal_text,
        command.rationale_text,
        command.run_request_fingerprint,
    ):
        assert forbidden not in serialized_events


def test_existing_issue_reuses_attention_supersedes_once_and_retries_idempotently(
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
        marker="first",
    )
    first, _timeline = _persist(ft013_database, first_command)
    with ft013_database.session() as session:
        first_ui_created_at = session.get(UIFeedEvent, first.proposal_id).created_at

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
        marker="second",
    )
    timeline = TimelineRecorder()
    second, _timeline = _persist(ft013_database, second_command, timeline)
    duplicate, _timeline = _persist(ft013_database, second_command, timeline)

    assert second.result == "created"
    assert duplicate.result == "duplicate"
    assert duplicate.as_value() | {"result": "created"} == second.as_value()
    assert second.issue_id == first.issue_id
    assert second.attention_id == first.attention_id
    with ft013_database.session() as session:
        proposals = list(
            session.scalars(
                select(CompanionProposal).order_by(
                    CompanionProposal.proposal_sequence
                )
            )
        )
        attention = session.get(CompanionHumanAttention, first.attention_id)
        first_ui = session.get(UIFeedEvent, first.proposal_id)
        attention_ui = session.get(UIFeedEvent, first.attention_id)
        assert [item.state for item in proposals] == ["superseded", "pending"]
        assert [item.record_version for item in proposals] == [2, 1]
        assert attention.current_proposal_id == second.proposal_id
        assert attention.record_version == 2
        assert first_ui.created_at == first_ui_created_at
        assert first_ui.display_payload["proposal_state"] == "superseded"
        assert attention_ui.source_refs[-1] == f"companion_proposal:{first.proposal_id}"

    assert [event.event_type for event in timeline.events] == [
        "companion_proposal_superseded",
        "companion_proposal_created",
    ]
    conflict = replace(second_command, proposal_text="Конфликтующее предложение.")
    with pytest.raises(CompanionGovernanceError) as caught:
        _persist(ft013_database, conflict)
    assert caught.value.code is CompanionGovernanceErrorCode.VERSION_CONFLICT
    assert _counts(ft013_database)["proposals"] == 2

    new_as_existing = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=first_message,
        run_id=first_command.run_id,
        target_issue_id=first.issue_id,
        expected_issue_version=1,
        marker="first",
        fingerprint=first_command.run_request_fingerprint,
    )
    with pytest.raises(CompanionGovernanceError) as target_changed:
        _persist(ft013_database, new_as_existing)
    assert target_changed.value.code is CompanionGovernanceErrorCode.VERSION_CONFLICT

    existing_as_new = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=second_message,
        run_id=second_command.run_id,
        marker="second",
        fingerprint=second_command.run_request_fingerprint,
    )
    with pytest.raises(CompanionGovernanceError) as target_removed:
        _persist(ft013_database, existing_as_new)
    assert target_removed.value.code is CompanionGovernanceErrorCode.VERSION_CONFLICT
    assert _counts(ft013_database)["proposals"] == 2


def test_write_authority_classification_version_archive_and_restore_fail_closed(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    engineer, engineer_membership = create_actor(ft013_database, farm, "engineer")
    consultant, consultant_membership = create_actor(
        ft013_database, farm, "consultant"
    )
    ungranted, _ungranted_membership = create_actor(
        ft013_database, farm, "engineer"
    )
    grant_access(
        ft013_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    grant_access(
        ft013_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )

    engineer_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    created, _timeline = _persist(
        ft013_database,
        make_proposal_command(
            engineer,
            plant_id=plant.plant_id,
            message_id=engineer_message,
            marker="engineer",
        ),
    )
    baseline = _counts(ft013_database)

    for actor, code in (
        (consultant, CompanionGovernanceErrorCode.COMMAND_FORBIDDEN),
        (ungranted, CompanionGovernanceErrorCode.COMMAND_FORBIDDEN),
    ):
        message_id = seed_companion_classification(
            ft013_database,
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
        )
        with pytest.raises(CompanionGovernanceError) as caught:
            _persist(
                ft013_database,
                make_proposal_command(
                    actor,
                    plant_id=plant.plant_id,
                    message_id=message_id,
                ),
            )
        assert caught.value.code is code
        assert _counts(ft013_database) == baseline

    wrong_farm = copy.copy(boss)
    object.__setattr__(wrong_farm, "farm_id", uuid.uuid4())
    wrong_farm_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    with pytest.raises(CompanionGovernanceError) as wrong_scope:
        _persist(
            ft013_database,
            make_proposal_command(
                wrong_farm,
                plant_id=plant.plant_id,
                message_id=wrong_farm_message,
            ),
        )
    assert wrong_scope.value.code is CompanionGovernanceErrorCode.COMMAND_FORBIDDEN
    assert _counts(ft013_database) == baseline

    mismatched_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        effect="check",
    )
    with pytest.raises(CompanionGovernanceError) as mismatch:
        _persist(
            ft013_database,
            make_proposal_command(
                boss,
                plant_id=plant.plant_id,
                message_id=mismatched_message,
                effect="discussion_only",
            ),
        )
    assert mismatch.value.code is CompanionGovernanceErrorCode.EFFECT_INVALID
    assert _counts(ft013_database) == baseline

    stale_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    with pytest.raises(CompanionGovernanceError) as stale:
        _persist(
            ft013_database,
            make_proposal_command(
                boss,
                plant_id=plant.plant_id,
                message_id=stale_message,
                target_issue_id=created.issue_id,
                expected_issue_version=99,
            ),
        )
    assert stale.value.code is CompanionGovernanceErrorCode.VERSION_CONFLICT
    assert _counts(ft013_database) == baseline

    revoke_access(
        ft013_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    revoked_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    with pytest.raises(CompanionGovernanceError) as revoked:
        _persist(
            ft013_database,
            make_proposal_command(
                engineer,
                plant_id=plant.plant_id,
                message_id=revoked_message,
            ),
        )
    assert revoked.value.code is CompanionGovernanceErrorCode.COMMAND_FORBIDDEN
    assert _counts(ft013_database) == baseline

    archive_plant(ft013_database, boss, plant_id=plant.plant_id)
    archived_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    with pytest.raises(CompanionGovernanceError) as archived:
        _persist(
            ft013_database,
            make_proposal_command(
                boss,
                plant_id=plant.plant_id,
                message_id=archived_message,
            ),
        )
    assert archived.value.code is CompanionGovernanceErrorCode.PLANT_NOT_ACTIVE
    assert _counts(ft013_database) == baseline

    with ft013_database.session() as session:
        FarmService(session).restore_plant(boss, plant_id=plant.plant_id)
    assert _counts(ft013_database) == baseline


def test_concurrent_same_run_commits_one_effect_and_returns_canonical_duplicate(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    message_id = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    command = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=message_id,
    )
    timeline = TimelineRecorder()

    def worker():
        return _persist(ft013_database, command, timeline)[0]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: worker(), range(2)))

    assert sorted(item.result for item in results) == ["created", "duplicate"]
    assert len({item.proposal_id for item in results}) == 1
    assert _counts(ft013_database)["proposals"] == 1
    assert [event.event_type for event in timeline.events] == [
        "companion_issue_opened",
        "companion_proposal_created",
    ]


def test_concurrent_distinct_runs_serialize_new_issue_focus_and_existing_supersede(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    new_commands = []
    for marker in ("new-a", "new-b"):
        message_id = seed_companion_classification(
            ft013_database,
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
        )
        new_commands.append(
            make_proposal_command(
                boss,
                plant_id=plant.plant_id,
                message_id=message_id,
                marker=marker,
            )
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        new_results = list(
            pool.map(lambda command: _persist(ft013_database, command)[0], new_commands)
        )
    assert all(item.result == "created" for item in new_results)
    with ft013_database.session() as session:
        issues = list(session.scalars(select(CompanionIssue)))
        assert len(issues) == 2
        assert sum(item.is_focused for item in issues) == 1

    focused_result = next(
        result
        for result in new_results
        if result.issue_id
        == next(item.issue_id for item in issues if item.is_focused)
    )
    with ft013_database.session() as session:
        focused_issue = session.get(CompanionIssue, focused_result.issue_id)
        expected_version = focused_issue.record_version

    existing_commands = []
    for marker in ("existing-a", "existing-b"):
        message_id = seed_companion_classification(
            ft013_database,
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
        )
        existing_commands.append(
            make_proposal_command(
                boss,
                plant_id=plant.plant_id,
                message_id=message_id,
                target_issue_id=focused_result.issue_id,
                expected_issue_version=expected_version,
                marker=marker,
            )
        )
    with ThreadPoolExecutor(max_workers=2) as pool:
        existing_results = list(
            pool.map(
                lambda command: _persist(ft013_database, command)[0],
                existing_commands,
            )
        )
    assert all(item.result == "created" for item in existing_results)
    with ft013_database.session() as session:
        proposals = list(
            session.scalars(
                select(CompanionProposal)
                .where(CompanionProposal.issue_id == focused_result.issue_id)
                .order_by(CompanionProposal.proposal_sequence)
            )
        )
        attention = session.get(
            CompanionHumanAttention, focused_result.attention_id
        )
        assert [item.proposal_sequence for item in proposals] == [1, 2, 3]
        assert [item.state for item in proposals] == [
            "superseded",
            "superseded",
            "pending",
        ]
        assert attention.current_proposal_id == proposals[-1].proposal_id
        assert attention.record_version == 3


def test_archive_race_rechecks_locked_plant_and_writes_nothing_on_denial(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    message_id = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    command = make_proposal_command(
        boss,
        plant_id=plant.plant_id,
        message_id=message_id,
        marker="archive-race",
    )
    writer_waiting = Event()
    engine = ft013_database.engine()

    def observe_plant_lock(
        _connection,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ):
        normalized = " ".join(statement.lower().split())
        if (
            current_thread().name.startswith("ft013-archive-writer")
            and "from plants" in normalized
            and "for update" in normalized
        ):
            writer_waiting.set()

    event.listen(engine, "before_cursor_execute", observe_plant_lock)
    try:
        with ft013_database.session() as blocker:
            transaction = blocker.begin()
            locked = blocker.scalar(
                select(Plant)
                .where(Plant.plant_id == plant.plant_id)
                .with_for_update()
            )
            locked.status = "archived"
            with ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="ft013-archive-writer"
            ) as pool:
                future = pool.submit(_persist, ft013_database, command)
                observed = writer_waiting.wait(5)
                transaction.commit()
                assert observed
                with pytest.raises(CompanionGovernanceError) as denied:
                    future.result(timeout=5)
    finally:
        event.remove(engine, "before_cursor_execute", observe_plant_lock)

    assert denied.value.code is CompanionGovernanceErrorCode.PLANT_NOT_ACTIVE
    assert _counts(ft013_database)["proposals"] == 0
    assert _counts(ft013_database)["ui"] == 0


def test_grant_race_rechecks_locked_grant_and_writes_nothing_on_denial(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    engineer, engineer_membership = create_actor(ft013_database, farm, "engineer")
    grant = grant_access(
        ft013_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    message_id = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    command = make_proposal_command(
        engineer,
        plant_id=plant.plant_id,
        message_id=message_id,
        marker="grant-race",
    )
    writer_waiting = Event()
    engine = ft013_database.engine()

    def observe_grant_lock(
        _connection,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ):
        normalized = " ".join(statement.lower().split())
        if (
            current_thread().name.startswith("ft013-grant-writer")
            and "from plant_access_grants" in normalized
            and "for update" in normalized
        ):
            writer_waiting.set()

    event.listen(engine, "before_cursor_execute", observe_grant_lock)
    try:
        with ft013_database.session() as blocker:
            transaction = blocker.begin()
            locked = blocker.scalar(
                select(PlantAccessGrant)
                .where(PlantAccessGrant.grant_id == grant.grant_id)
                .with_for_update()
            )
            locked.status = "revoked"
            with ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="ft013-grant-writer"
            ) as pool:
                future = pool.submit(_persist, ft013_database, command)
                observed = writer_waiting.wait(5)
                transaction.commit()
                assert observed
                with pytest.raises(CompanionGovernanceError) as denied:
                    future.result(timeout=5)
    finally:
        event.remove(engine, "before_cursor_execute", observe_grant_lock)

    assert denied.value.code is CompanionGovernanceErrorCode.COMMAND_FORBIDDEN
    assert _counts(ft013_database)["proposals"] == 0
    assert _counts(ft013_database)["ui"] == 0
