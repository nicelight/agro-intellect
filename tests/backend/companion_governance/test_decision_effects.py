from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
import threading
import uuid

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.agent_chat import AgentBusEvent, UIFeedEvent
from backend.app.access_admin.farm_service import FarmService
from backend.app.companion_governance import (
    CloseCompanionIssueCommandV1,
    CompanionGovernanceError,
    CompanionGovernanceErrorCode,
    CompanionGovernanceService,
    CompanionGovernanceValidationError,
    CompanionHumanAttention,
    CompanionIssue,
    CompanionProposal,
    DecideCompanionProposalCommandV1,
    DecisionRecord,
)
from backend.app.companion_governance import service as companion_service_module
from backend.app.safety_gate import SafetyClassification
from backend.app.task_follow_up import (
    Task,
    TaskFollowUpError,
    TaskFollowUpErrorCode,
    TaskFollowUpService,
)
from backend.app.task_follow_up.contracts import canonical_fingerprint
from backend.app.task_follow_up.repository import TaskFollowUpRepository
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
    create_actor,
    grant_access,
    revoke_access,
)


def _proposal(database, farm, boss, plant, *, effect: str):
    message_id = seed_companion_classification(
        database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        effect=effect,
    )
    with database.session() as session:
        result = CompanionGovernanceService(
            session,
            timeline_appender=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).persist_companion_proposal(
            make_proposal_command(
                boss,
                plant_id=plant.plant_id,
                message_id=message_id,
                effect=effect,
            )
        )
    return result


def _decision_command(
    actor,
    *,
    plant_id,
    proposal_id,
    request_id=None,
    decision="approved",
    resolution="keep_open",
    expected_version=1,
):
    return DecideCompanionProposalCommandV1(
        actor_context=actor,
        plant_id=plant_id,
        proposal_id=proposal_id,
        request_id=request_id or uuid.uuid4(),
        expected_version=expected_version,
        decision=decision,
        decision_summary="Решение оператора принято.",
        issue_resolution=resolution,
    )


class _ControlledUuid:
    UUID = uuid.UUID

    def __init__(self, *values: int) -> None:
        self._values = iter(
            uuid.UUID(f"00000000-0000-4000-8000-{value:012x}")
            for value in values
        )

    def uuid4(self) -> uuid.UUID:
        return next(self._values)


def _controlled_proposal(
    database,
    farm,
    boss,
    plant,
    monkeypatch,
    *,
    ids: tuple[int, int, int],
    marker: str,
):
    message_id = seed_companion_classification(
        database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        effect="none",
    )
    with monkeypatch.context() as controlled:
        controlled.setattr(
            companion_service_module,
            "uuid",
            _ControlledUuid(*ids),
        )
        with database.session() as session:
            return CompanionGovernanceService(
                session,
                timeline_appender=TimelineRecorder(),
                clock=lambda: FT013_NOW,
            ).persist_companion_proposal(
                make_proposal_command(
                    boss,
                    plant_id=plant.plant_id,
                    message_id=message_id,
                    effect="none",
                    marker=marker,
                )
            )


@pytest.mark.parametrize(
    ("first_ids", "second_ids"),
    [
        ((101, 10, 201), (102, 20, 202)),
        ((101, 20, 201), (102, 10, 202)),
    ],
    ids=["target_uuid_lower", "target_uuid_higher"],
)
def test_unfocused_pending_keep_open_transfers_focus_for_any_uuid_order(
    ft013_database,
    ft013_seed,
    monkeypatch,
    first_ids,
    second_ids,
):
    farm, boss, _membership, plant = ft013_seed
    target = _controlled_proposal(
        ft013_database,
        farm,
        boss,
        plant,
        monkeypatch,
        ids=first_ids,
        marker="decision-target",
    )
    current_focus = _controlled_proposal(
        ft013_database,
        farm,
        boss,
        plant,
        monkeypatch,
        ids=second_ids,
        marker="current-focus",
    )

    with ft013_database.session() as session:
        created = CompanionGovernanceService(
            session,
            timeline_appender=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).decide_companion_proposal(
            _decision_command(
                boss,
                plant_id=plant.plant_id,
                proposal_id=target.proposal_id,
            )
        )

    assert created.result == "created"
    assert created.issue["is_focused"] is True
    with ft013_database.session() as session:
        target_issue = session.get(CompanionIssue, target.issue_id)
        previous_focus = session.get(CompanionIssue, current_focus.issue_id)
        proposal = session.get(CompanionProposal, target.proposal_id)
        attention = session.get(
            CompanionHumanAttention,
            target.attention_id,
        )
        assert target_issue is not None
        assert (target_issue.status, target_issue.is_focused) == ("open", True)
        assert previous_focus is not None
        assert (previous_focus.status, previous_focus.is_focused) == (
            "open",
            False,
        )
        assert proposal is not None
        assert (proposal.state, proposal.record_version) == ("approved", 2)
        assert attention is not None
        assert (attention.status, attention.record_version) == ("satisfied", 2)
        assert session.scalar(
            select(func.count(DecisionRecord.decision_record_id))
        ) == 1


def test_unfocused_keep_open_failure_rolls_back_intermediate_focus_release(
    ft013_database,
    ft013_seed,
    monkeypatch,
):
    farm, boss, _membership, plant = ft013_seed
    target = _controlled_proposal(
        ft013_database,
        farm,
        boss,
        plant,
        monkeypatch,
        ids=(101, 10, 201),
        marker="rollback-target",
    )
    current_focus = _controlled_proposal(
        ft013_database,
        farm,
        boss,
        plant,
        monkeypatch,
        ids=(102, 20, 202),
        marker="rollback-current-focus",
    )

    def fail_projection(_event):
        raise SQLAlchemyError("projection failure after focus release")

    monkeypatch.setattr(companion_service_module, "new_ui_model", fail_projection)
    with pytest.raises(CompanionGovernanceError) as raised:
        with ft013_database.session() as session:
            CompanionGovernanceService(
                session,
                timeline_appender=TimelineRecorder(),
                clock=lambda: FT013_NOW,
            ).decide_companion_proposal(
                _decision_command(
                    boss,
                    plant_id=plant.plant_id,
                    proposal_id=target.proposal_id,
                )
            )
    assert raised.value.code is CompanionGovernanceErrorCode.PERSISTENCE_FAILED

    with ft013_database.session() as session:
        target_issue = session.get(CompanionIssue, target.issue_id)
        original_focus = session.get(CompanionIssue, current_focus.issue_id)
        proposal = session.get(CompanionProposal, target.proposal_id)
        attention = session.get(
            CompanionHumanAttention,
            target.attention_id,
        )
        assert target_issue is not None and target_issue.is_focused is False
        assert original_focus is not None and original_focus.is_focused is True
        assert proposal is not None
        assert (proposal.state, proposal.record_version) == ("pending", 1)
        assert attention is not None
        assert (attention.status, attention.record_version) == ("active", 1)
        assert session.scalar(
            select(func.count(DecisionRecord.decision_record_id))
        ) == 0


def test_approved_check_creates_one_atomic_governance_task_and_duplicate(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    persisted = _proposal(ft013_database, farm, boss, plant, effect="check")
    command = _decision_command(
        boss,
        plant_id=plant.plant_id,
        proposal_id=persisted.proposal_id,
    )
    timeline = TimelineRecorder()
    with ft013_database.session() as session:
        service = CompanionGovernanceService(
            session,
            timeline_appender=timeline,
            clock=lambda: FT013_NOW,
        )
        created = service.decide_companion_proposal(command)
        duplicate = service.decide_companion_proposal(command)

    assert created.result == "created"
    assert duplicate.result == "duplicate"
    with pytest.raises(CompanionGovernanceError) as conflict:
        with ft013_database.session() as session:
            CompanionGovernanceService(
                session,
                timeline_appender=TimelineRecorder(),
                clock=lambda: FT013_NOW,
            ).decide_companion_proposal(
                DecideCompanionProposalCommandV1(
                    actor_context=boss,
                    plant_id=plant.plant_id,
                    proposal_id=persisted.proposal_id,
                    request_id=command.request_id,
                    expected_version=1,
                    decision="approved",
                    decision_summary="Конфликтующее решение.",
                    issue_resolution="keep_open",
                )
            )
    assert conflict.value.code is CompanionGovernanceErrorCode.VERSION_CONFLICT
    assert created.workflow_task_ref == created.decision_record["workflow_effect_ref"]
    with ft013_database.session() as session:
        decision = session.scalar(select(DecisionRecord))
        task = session.scalar(select(Task))
        proposal = session.get(CompanionProposal, persisted.proposal_id)
        attention = session.get(CompanionHumanAttention, persisted.attention_id)
        assert decision is not None and task is not None
        assert proposal.state == "approved"
        assert proposal.record_version == 2
        assert proposal.decision_record_id == decision.decision_record_id
        assert attention.status == "satisfied"
        assert task.source_type == "governance_decision"
        assert task.kind == "check"
        assert task.decision_record_id == decision.decision_record_id
        assert task.classification_message_id is None
        assert task.create_request_fingerprint == canonical_fingerprint(
            {
                "schema_version": 1,
                "source_branch": "governance_decision",
                "request_id": str(decision.request_id),
                "request_fingerprint": decision.request_fingerprint,
                "decision_record_id": str(decision.decision_record_id),
                "proposal_id": str(proposal.proposal_id),
                "task_kind": proposal.proposed_effect,
                "task_display_text": proposal.task_display_text,
                "source_refs": task.source_refs,
            }
        )
        assert decision.workflow_effect_ref == f"task:{task.task_id}"
        assert session.scalar(select(func.count(AgentBusEvent.event_id))) == 1
        assert session.scalar(select(func.count(UIFeedEvent.ui_event_id))) == 3
    assert [event.event_type for event in timeline.events] == [
        "companion_decision_recorded",
        "task_created",
    ]
    assert timeline.events[0].payload_summary == {
        "decision": "approved",
        "allowed_workflow_effect": "check",
        "issue_resolution": "keep_open",
        "workflow_effect_ref": created.workflow_task_ref,
        "safety_gate_authority": "not_granted",
    }


@pytest.mark.parametrize(
    ("effect", "expected_task_kind"),
    [
        ("discussion_only", None),
        ("none", None),
        ("check", "check"),
        ("measurement", "measurement"),
        ("follow_up", "follow_up"),
    ],
)
def test_approval_copies_each_closed_effect_exactly(
    ft013_database,
    ft013_seed,
    effect,
    expected_task_kind,
):
    farm, boss, _membership, plant = ft013_seed
    persisted = _proposal(ft013_database, farm, boss, plant, effect=effect)
    with ft013_database.session() as session:
        result = CompanionGovernanceService(
            session,
            timeline_appender=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).decide_companion_proposal(
            _decision_command(
                boss,
                plant_id=plant.plant_id,
                proposal_id=persisted.proposal_id,
            )
        )
    assert result.decision_record["allowed_workflow_effect"] == effect
    with ft013_database.session() as session:
        tasks = list(session.scalars(select(Task)))
    if expected_task_kind is None:
        assert result.workflow_task_ref is None
        assert tasks == []
    else:
        assert result.workflow_task_ref == f"task:{tasks[0].task_id}"
        assert [task.kind for task in tasks] == [expected_task_kind]


def test_rejection_resolves_without_task_or_bus_then_close_is_idempotent(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    persisted = _proposal(
        ft013_database,
        farm,
        boss,
        plant,
        effect="discussion_only",
    )
    decision_timeline = TimelineRecorder()
    with ft013_database.session() as session:
        decision = CompanionGovernanceService(
            session,
            timeline_appender=decision_timeline,
            clock=lambda: FT013_NOW,
        ).decide_companion_proposal(
            _decision_command(
                boss,
                plant_id=plant.plant_id,
                proposal_id=persisted.proposal_id,
                decision="rejected",
                resolution="resolved",
            )
        )
    assert decision.workflow_task_ref is None
    assert decision.decision_record["allowed_workflow_effect"] == "none"
    assert decision_timeline.events[0].payload_summary == {
        "decision": "rejected",
        "allowed_workflow_effect": "none",
        "issue_resolution": "resolved",
        "workflow_effect_ref": None,
        "safety_gate_authority": "not_granted",
    }
    assert decision_timeline.events[1].payload_summary == {
        "issue_status": "resolved",
        "decision_record_id": decision.decision_record["decision_record_id"],
    }
    close_request = uuid.uuid4()
    with ft013_database.session() as session:
        service = CompanionGovernanceService(
            session,
            timeline_appender=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        )
        issue = session.get(CompanionIssue, persisted.issue_id)
        assert issue is not None
        command = CloseCompanionIssueCommandV1(
            actor_context=boss,
            plant_id=plant.plant_id,
            issue_id=issue.issue_id,
            request_id=close_request,
            expected_version=issue.record_version,
        )
        closed = service.close_companion_issue(command)
        duplicate = service.close_companion_issue(command)
    assert closed.result == "closed"
    assert duplicate.result == "duplicate"
    assert closed.issue["status"] == "closed"
    with ft013_database.session() as session:
        assert session.scalar(select(func.count(Task.task_id))) == 0
        assert session.scalar(select(func.count(AgentBusEvent.event_id))) == 0


def test_task_audit_failure_rolls_back_complete_decision_uow(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    persisted = _proposal(ft013_database, farm, boss, plant, effect="measurement")
    with pytest.raises(CompanionGovernanceError) as raised:
        with ft013_database.session() as session:
            CompanionGovernanceService(
                session,
                timeline_appender=TimelineRecorder(fail_on="task_created"),
                clock=lambda: FT013_NOW,
            ).decide_companion_proposal(
                _decision_command(
                    boss,
                    plant_id=plant.plant_id,
                    proposal_id=persisted.proposal_id,
                )
            )
    assert raised.value.code is CompanionGovernanceErrorCode.AUDIT_FAILED
    with ft013_database.session() as session:
        proposal = session.get(CompanionProposal, persisted.proposal_id)
        attention = session.get(CompanionHumanAttention, persisted.attention_id)
        assert proposal.state == "pending"
        assert proposal.record_version == 1
        assert attention.status == "active"
        assert session.scalar(select(func.count(DecisionRecord.decision_record_id))) == 0
        assert session.scalar(select(func.count(Task.task_id))) == 0


def test_consultant_cannot_decide_even_with_current_read_grant(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    persisted = _proposal(ft013_database, farm, boss, plant, effect="none")
    consultant, consultant_membership = create_actor(
        ft013_database,
        farm,
        "consultant",
    )
    grant_access(
        ft013_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )
    with pytest.raises(CompanionGovernanceError) as raised:
        with ft013_database.session() as session:
            CompanionGovernanceService(
                session,
                timeline_appender=TimelineRecorder(),
                clock=lambda: FT013_NOW,
            ).decide_companion_proposal(
                _decision_command(
                    consultant,
                    plant_id=plant.plant_id,
                    proposal_id=persisted.proposal_id,
                )
            )
    assert raised.value.code is CompanionGovernanceErrorCode.COMMAND_FORBIDDEN


def test_granted_engineer_can_decide_but_revoked_grant_cannot(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    engineer, engineer_membership = create_actor(
        ft013_database,
        farm,
        "engineer",
    )
    grant_access(
        ft013_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    approved = _proposal(ft013_database, farm, boss, plant, effect="check")
    with ft013_database.session() as session:
        result = CompanionGovernanceService(
            session,
            timeline_appender=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).decide_companion_proposal(
            _decision_command(
                engineer,
                plant_id=plant.plant_id,
                proposal_id=approved.proposal_id,
            )
        )
    assert result.decision_record["decider_role_preset"] == "engineer"

    pending = _proposal(ft013_database, farm, boss, plant, effect="none")
    revoke_access(
        ft013_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    with pytest.raises(CompanionGovernanceError) as raised:
        with ft013_database.session() as session:
            CompanionGovernanceService(
                session,
                timeline_appender=TimelineRecorder(),
                clock=lambda: FT013_NOW,
            ).decide_companion_proposal(
                _decision_command(
                    engineer,
                    plant_id=plant.plant_id,
                    proposal_id=pending.proposal_id,
                )
            )
    assert raised.value.code is CompanionGovernanceErrorCode.COMMAND_FORBIDDEN
    with ft013_database.session() as session:
        proposal = session.get(CompanionProposal, pending.proposal_id)
        assert proposal is not None and proposal.state == "pending"


def test_wrong_farm_and_archive_fail_closed_without_restore_replay(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    persisted = _proposal(ft013_database, farm, boss, plant, effect="check")
    other_boss = copy.copy(boss)
    object.__setattr__(other_boss, "farm_id", uuid.uuid4())
    with pytest.raises(CompanionGovernanceError) as wrong_farm:
        with ft013_database.session() as session:
            CompanionGovernanceService(
                session,
                timeline_appender=TimelineRecorder(),
                clock=lambda: FT013_NOW,
            ).decide_companion_proposal(
                _decision_command(
                    other_boss,
                    plant_id=plant.plant_id,
                    proposal_id=persisted.proposal_id,
                )
            )
    assert wrong_farm.value.code is CompanionGovernanceErrorCode.COMMAND_FORBIDDEN

    archive_plant(ft013_database, boss, plant_id=plant.plant_id)
    command = _decision_command(
        boss,
        plant_id=plant.plant_id,
        proposal_id=persisted.proposal_id,
    )
    with pytest.raises(CompanionGovernanceError) as archived:
        with ft013_database.session() as session:
            CompanionGovernanceService(
                session,
                timeline_appender=TimelineRecorder(),
                clock=lambda: FT013_NOW,
            ).decide_companion_proposal(command)
    assert archived.value.code is CompanionGovernanceErrorCode.PLANT_NOT_ACTIVE
    with ft013_database.session() as session:
        assert session.scalar(select(func.count(DecisionRecord.decision_record_id))) == 0
        assert session.scalar(select(func.count(Task.task_id))) == 0

    with ft013_database.session() as session:
        FarmService(session).restore_plant(boss, plant_id=plant.plant_id)
    with ft013_database.session() as session:
        assert session.scalar(select(func.count(DecisionRecord.decision_record_id))) == 0
        assert session.scalar(select(func.count(Task.task_id))) == 0
    with ft013_database.session() as session:
        result = CompanionGovernanceService(
            session,
            timeline_appender=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).decide_companion_proposal(command)
    assert result.result == "created"


@pytest.mark.parametrize("effect", ["action", "unknown"])
def test_forbidden_effects_reject_at_strict_handoff(effect, ft013_seed):
    _farm, boss, _membership, plant = ft013_seed
    with pytest.raises(CompanionGovernanceValidationError):
        make_proposal_command(
            boss,
            plant_id=plant.plant_id,
            message_id=uuid.uuid4(),
            effect=effect,
        )


def test_stale_version_and_classification_mismatch_leave_decision_pending(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    persisted = _proposal(ft013_database, farm, boss, plant, effect="check")

    with pytest.raises(CompanionGovernanceValidationError):
        with ft013_database.session() as session:
            CompanionGovernanceService(
                session,
                timeline_appender=TimelineRecorder(),
                clock=lambda: FT013_NOW,
            ).decide_companion_proposal(
                _decision_command(
                    boss,
                    plant_id=plant.plant_id,
                    proposal_id=persisted.proposal_id,
                    expected_version=2,
                    )
                )

    with ft013_database.session() as session, session.begin():
        proposal = session.get(CompanionProposal, persisted.proposal_id)
        assert proposal is not None
        classification = session.get(
            SafetyClassification,
            proposal.source_classification_message_id,
        )
        assert classification is not None
        classification.safe_task_kind = "measurement"
        classification.reason_code = "safe_measurement_request"

    with pytest.raises(CompanionGovernanceError) as mismatch:
        with ft013_database.session() as session:
            CompanionGovernanceService(
                session,
                timeline_appender=TimelineRecorder(),
                clock=lambda: FT013_NOW,
            ).decide_companion_proposal(
                _decision_command(
                    boss,
                    plant_id=plant.plant_id,
                    proposal_id=persisted.proposal_id,
                )
            )
    assert mismatch.value.code is CompanionGovernanceErrorCode.EFFECT_INVALID
    with ft013_database.session() as session:
        proposal = session.get(CompanionProposal, persisted.proposal_id)
        attention = session.get(
            CompanionHumanAttention,
            persisted.attention_id,
        )
        assert proposal is not None and proposal.state == "pending"
        assert attention is not None and attention.status == "active"
        assert session.scalar(
            select(func.count(DecisionRecord.decision_record_id))
        ) == 0
        assert session.scalar(select(func.count(Task.task_id))) == 0


def test_superseded_and_concurrent_decisions_commit_at_most_one_effect(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    superseded = _proposal(ft013_database, farm, boss, plant, effect="check")
    with ft013_database.session() as session:
        issue = session.get(CompanionIssue, superseded.issue_id)
        assert issue is not None
        expected_issue_version = issue.record_version
    replacement_message = seed_companion_classification(
        ft013_database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        effect="measurement",
    )
    with ft013_database.session() as session:
        replacement = CompanionGovernanceService(
            session,
            timeline_appender=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).persist_companion_proposal(
            make_proposal_command(
                boss,
                plant_id=plant.plant_id,
                message_id=replacement_message,
                target_issue_id=superseded.issue_id,
                expected_issue_version=expected_issue_version,
                effect="measurement",
                marker="replacement",
            )
        )
    with pytest.raises(CompanionGovernanceError) as stale:
        with ft013_database.session() as session:
            CompanionGovernanceService(
                session,
                timeline_appender=TimelineRecorder(),
                clock=lambda: FT013_NOW,
            ).decide_companion_proposal(
                _decision_command(
                    boss,
                    plant_id=plant.plant_id,
                    proposal_id=superseded.proposal_id,
                )
            )
    assert stale.value.code is CompanionGovernanceErrorCode.PROPOSAL_NOT_CURRENT

    barrier = threading.Barrier(2)

    def decide_once():
        barrier.wait(timeout=10)
        try:
            with ft013_database.session() as session:
                return CompanionGovernanceService(
                    session,
                    timeline_appender=TimelineRecorder(),
                    clock=lambda: FT013_NOW,
                ).decide_companion_proposal(
                    _decision_command(
                        boss,
                        plant_id=plant.plant_id,
                        proposal_id=replacement.proposal_id,
                    )
                ).result
        except CompanionGovernanceError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _index: decide_once(), range(2)))
    assert sorted(
        item.value if isinstance(item, CompanionGovernanceErrorCode) else item
        for item in outcomes
    ) == sorted(
        ["created", CompanionGovernanceErrorCode.VERSION_CONFLICT.value]
    )
    with ft013_database.session() as session:
        assert session.scalar(select(func.count(DecisionRecord.decision_record_id))) == 1
        assert session.scalar(select(func.count(Task.task_id))) == 1


def test_projection_and_database_failures_roll_back_flushed_decision_graph(
    ft013_database,
    ft013_seed,
    monkeypatch,
):
    farm, boss, _membership, plant = ft013_seed
    persisted = _proposal(ft013_database, farm, boss, plant, effect="check")

    def fail_projection(_event):
        raise SQLAlchemyError("projection failure")

    monkeypatch.setattr(companion_service_module, "new_ui_model", fail_projection)
    with pytest.raises(CompanionGovernanceError) as projection:
        with ft013_database.session() as session:
            CompanionGovernanceService(
                session,
                timeline_appender=TimelineRecorder(),
                clock=lambda: FT013_NOW,
            ).decide_companion_proposal(
                _decision_command(
                    boss,
                    plant_id=plant.plant_id,
                    proposal_id=persisted.proposal_id,
                )
            )
    assert projection.value.code is CompanionGovernanceErrorCode.PERSISTENCE_FAILED
    monkeypatch.undo()

    def fail_commit(_session):
        raise SQLAlchemyError("database commit failure")

    with pytest.raises(CompanionGovernanceError) as database:
        with ft013_database.session() as session:
            event.listen(session, "before_commit", fail_commit)
            CompanionGovernanceService(
                session,
                timeline_appender=TimelineRecorder(),
                clock=lambda: FT013_NOW,
            ).decide_companion_proposal(
                _decision_command(
                    boss,
                    plant_id=plant.plant_id,
                    proposal_id=persisted.proposal_id,
                )
            )
    assert database.value.code is CompanionGovernanceErrorCode.PERSISTENCE_FAILED
    with ft013_database.session() as session:
        proposal = session.get(CompanionProposal, persisted.proposal_id)
        attention = session.get(CompanionHumanAttention, persisted.attention_id)
        assert proposal is not None and proposal.state == "pending"
        assert attention is not None and attention.status == "active"
        assert session.scalar(select(func.count(DecisionRecord.decision_record_id))) == 0
        assert session.scalar(select(func.count(Task.task_id))) == 0


def test_task_source_reload_rejects_wrong_terminal_phase_and_link(
    ft013_database,
    ft013_seed,
    monkeypatch,
):
    farm, boss, _membership, plant = ft013_seed
    persisted = _proposal(ft013_database, farm, boss, plant, effect="check")
    original = TaskFollowUpRepository.lock_governance_decision_source_graph
    mutation = {"kind": "pending"}

    def invalid_graph(repository, decision_record_id):
        graph = original(repository, decision_record_id)
        assert graph is not None
        _decision, proposal, _attention, _issue, _classification = graph
        if mutation["kind"] == "different_link":
            proposal.decision_record_id = uuid.uuid4()
        else:
            proposal.state = mutation["kind"]
        return graph

    monkeypatch.setattr(
        TaskFollowUpRepository,
        "lock_governance_decision_source_graph",
        invalid_graph,
    )
    for kind in ("pending", "rejected", "superseded", "different_link"):
        mutation["kind"] = kind
        with pytest.raises(CompanionGovernanceError) as raised:
            with ft013_database.session() as session:
                CompanionGovernanceService(
                    session,
                    timeline_appender=TimelineRecorder(),
                    clock=lambda: FT013_NOW,
                ).decide_companion_proposal(
                    _decision_command(
                        boss,
                        plant_id=plant.plant_id,
                        proposal_id=persisted.proposal_id,
                    )
                )
        assert raised.value.code is CompanionGovernanceErrorCode.READ_INCONSISTENT
    with ft013_database.session() as session:
        proposal = session.get(CompanionProposal, persisted.proposal_id)
        assert proposal is not None and proposal.state == "pending"
        assert session.scalar(select(func.count(DecisionRecord.decision_record_id))) == 0
        assert session.scalar(select(func.count(Task.task_id))) == 0


def test_all_six_nested_task_errors_translate_and_roll_back(
    ft013_database,
    ft013_seed,
    monkeypatch,
):
    farm, boss, _membership, plant = ft013_seed
    persisted = _proposal(ft013_database, farm, boss, plant, effect="check")
    current = {"code": TaskFollowUpErrorCode.TASK_COMMAND_FORBIDDEN}

    def fail_task(_service, _command):
        raise TaskFollowUpError(current["code"])

    monkeypatch.setattr(TaskFollowUpService, "create_ordinary_task", fail_task)
    translations = (
        (
            TaskFollowUpErrorCode.TASK_COMMAND_FORBIDDEN,
            CompanionGovernanceErrorCode.COMMAND_FORBIDDEN,
        ),
        (
            TaskFollowUpErrorCode.TASK_PLANT_NOT_ACTIVE,
            CompanionGovernanceErrorCode.PLANT_NOT_ACTIVE,
        ),
        (
            TaskFollowUpErrorCode.TASK_SOURCE_INVALID,
            CompanionGovernanceErrorCode.READ_INCONSISTENT,
        ),
        (
            TaskFollowUpErrorCode.TASK_VERSION_CONFLICT,
            CompanionGovernanceErrorCode.VERSION_CONFLICT,
        ),
        (
            TaskFollowUpErrorCode.TASK_AUDIT_FAILED,
            CompanionGovernanceErrorCode.AUDIT_FAILED,
        ),
        (
            TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED,
            CompanionGovernanceErrorCode.PERSISTENCE_FAILED,
        ),
    )
    for task_code, companion_code in translations:
        current["code"] = task_code
        with pytest.raises(CompanionGovernanceError) as raised:
            with ft013_database.session() as session:
                CompanionGovernanceService(
                    session,
                    timeline_appender=TimelineRecorder(),
                    clock=lambda: FT013_NOW,
                ).decide_companion_proposal(
                    _decision_command(
                        boss,
                        plant_id=plant.plant_id,
                        proposal_id=persisted.proposal_id,
                    )
                )
        assert raised.value.code is companion_code
    with ft013_database.session() as session:
        proposal = session.get(CompanionProposal, persisted.proposal_id)
        assert proposal is not None and proposal.state == "pending"
        assert session.scalar(select(func.count(DecisionRecord.decision_record_id))) == 0
        assert session.scalar(select(func.count(Task.task_id))) == 0
