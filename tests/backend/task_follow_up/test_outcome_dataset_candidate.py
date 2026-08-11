"""FT-014-AC-011 wiring tests: record_outcome creates one follow_up_outcome
Dataset Candidate inside its own unit of work."""

from __future__ import annotations

from datetime import timedelta
import uuid

import pytest
from sqlalchemy import func, select

from backend.app.dataset_governance import (
    DatasetCandidate,
    DatasetGovernanceError,
    DatasetGovernanceErrorCode,
    DatasetGovernanceService,
    SourceKind,
)
from backend.app.task_follow_up import (
    CompleteTaskCommandV1,
    Outcome,
    OutcomeValue,
    RecordOutcomeCommandV1,
    Task,
    TaskFollowUpError,
    TaskFollowUpErrorCode,
    TaskFollowUpService,
)
from tests.backend.dataset_governance.conftest import TimelineRecorder
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    create_active_plant,
    grant_access,
    revoke_access,
    seed_farm,
)
from tests.backend.task_follow_up.test_domain_loop import (
    NOW,
    _approval_command,
    _measurement,
    _pending_decision,
)


def _open_follow_up(database, farm, boss, plant, timeline):
    decision_id, _ph, _ec = _pending_decision(
        database,
        farm,
        boss,
        plant,
        expires_at=NOW + timedelta(hours=1),
    )
    with database.session() as session:
        service = TaskFollowUpService(
            session, timeline_appender=timeline, clock=lambda: NOW
        )
        service.materialize_pending_approval(decision_id)
        action = service.decide_approval(
            _approval_command(boss, plant, decision_id)
        ).action_task
    with database.session() as session:
        follow_up = TaskFollowUpService(
            session, timeline_appender=timeline, clock=lambda: NOW
        ).complete_task(
            CompleteTaskCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                task_id=action.task_id,
                request_id=uuid.uuid4(),
            )
        ).follow_up_task
    assert follow_up is not None and follow_up.status == "open"
    return follow_up


def _record_outcome(database, boss, *, plant_id, follow_up_task_id, timeline,
                    value=OutcomeValue.IMPROVED, evidence_refs=()):
    with database.session() as session:
        service = TaskFollowUpService(
            session,
            timeline_appender=timeline,
            clock=lambda: NOW,
        )
        return service.record_outcome(
            RecordOutcomeCommandV1(
                actor_context=boss,
                plant_id=plant_id,
                follow_up_task_id=follow_up_task_id,
                request_id=uuid.uuid4(),
                value=value,
                evidence_refs=evidence_refs,
            )
        )


def _candidate_for(database, *, outcome_id):
    with database.session() as session:
        return session.scalar(
            select(DatasetCandidate).where(DatasetCandidate.source_ref == outcome_id)
        )


def _candidate_count(database, *, outcome_id) -> int:
    with database.session() as session:
        return session.scalar(
            select(func.count(DatasetCandidate.candidate_id)).where(
                DatasetCandidate.source_ref == outcome_id
            )
        )


def test_ft014_ac011_record_outcome_creates_exact_candidate_and_event_in_same_uow(
    ft012_database,
):
    farm = seed_farm(ft012_database)
    boss, _ = create_actor(ft012_database, farm, "boss")
    plant = create_active_plant(ft012_database, boss, plant_key="ac011_001")
    timeline = TimelineRecorder()

    follow_up = _open_follow_up(ft012_database, farm, boss, plant, timeline)
    evidence = _measurement(ft012_database, boss, plant, ph="6.50", measured_at=NOW)
    result = _record_outcome(
        ft012_database,
        boss,
        plant_id=plant.plant_id,
        follow_up_task_id=follow_up.task_id,
        timeline=timeline,
        evidence_refs=(f"manual_measurement:{evidence.measurement_id}",),
    )

    assert result.result == "created"
    outcome_id = result.outcome.outcome_id
    assert result.task.status == "completed"

    assert _candidate_count(ft012_database, outcome_id=outcome_id) == 1
    candidate = _candidate_for(ft012_database, outcome_id=outcome_id)
    assert candidate.farm_id == farm.farm_id
    assert candidate.plant_id == plant.plant_id
    assert candidate.candidate_status == "candidate"
    assert candidate.candidate_origin == "raw"
    assert candidate.quality_tier == "standard"
    assert candidate.split is None
    assert candidate.confirmation_source is None
    assert candidate.can_train_on is False
    assert candidate.follow_up_seen is True
    assert candidate.curator_run_id is None
    assert candidate.curator_command_sha256 is None
    assert candidate.curator_recorded_at is None
    assert candidate.corrected is False
    assert candidate.record_version == 1
    assert candidate.evidence_refs == [
        {"kind": "follow_up_outcome", "ref": str(outcome_id)}
    ]
    assert candidate.source_kind == "follow_up_outcome"
    assert candidate.source_ref == outcome_id
    assert len(candidate.event_refs) == 1
    created = candidate.event_refs[0]
    assert created["event_type"] == "dataset_candidate_created"
    assert created["timeline_ref"].startswith("timeline.jsonl#")
    assert uuid.UUID(created["timeline_event_id"])

    created_events = [
        e for e in timeline.events if e.event_type == "dataset_candidate_created"
    ]
    assert len(created_events) == 1
    assert created_events[0].source_type == "dataset_candidate"
    assert created_events[0].source_id == candidate.candidate_id
    assert created_events[0].payload_summary["source_kind"] == "follow_up_outcome"
    assert created_events[0].payload_summary["candidate_origin"] == "raw"
    assert created_events[0].payload_summary["can_train_on"] is False
    assert created_events[0].payload_summary["evidence_ref_count"] == 1


def test_ft014_ac011_no_data_outcome_creates_candidate_too(ft012_database):
    farm = seed_farm(ft012_database)
    boss, _ = create_actor(ft012_database, farm, "boss")
    plant = create_active_plant(ft012_database, boss, plant_key="ac011_no_data")
    timeline = TimelineRecorder()

    follow_up = _open_follow_up(ft012_database, farm, boss, plant, timeline)
    result = _record_outcome(
        ft012_database,
        boss,
        plant_id=plant.plant_id,
        follow_up_task_id=follow_up.task_id,
        timeline=timeline,
        value=OutcomeValue.NO_DATA,
    )
    outcome_id = result.outcome.outcome_id
    assert _candidate_count(ft012_database, outcome_id=outcome_id) == 1
    candidate = _candidate_for(ft012_database, outcome_id=outcome_id)
    assert candidate.follow_up_seen is True
    assert candidate.can_train_on is False
    assert candidate.evidence_refs == [
        {"kind": "follow_up_outcome", "ref": str(outcome_id)}
    ]


def test_ft014_ac011_identical_retry_returns_existing_graph_without_new_append(
    ft012_database,
):
    farm = seed_farm(ft012_database)
    boss, _ = create_actor(ft012_database, farm, "boss")
    plant = create_active_plant(ft012_database, boss, plant_key="ac011_idem")
    timeline = TimelineRecorder()

    follow_up = _open_follow_up(ft012_database, farm, boss, plant, timeline)
    evidence = _measurement(ft012_database, boss, plant, ph="6.60", measured_at=NOW)
    command = RecordOutcomeCommandV1(
        actor_context=boss,
        plant_id=plant.plant_id,
        follow_up_task_id=follow_up.task_id,
        request_id=uuid.uuid4(),
        value=OutcomeValue.IMPROVED,
        evidence_refs=(f"manual_measurement:{evidence.measurement_id}",),
    )
    with ft012_database.session() as session:
        first = TaskFollowUpService(
            session, timeline_appender=timeline, clock=lambda: NOW
        ).record_outcome(command)
    outcome_id = first.outcome.outcome_id
    assert _candidate_count(ft012_database, outcome_id=outcome_id) == 1
    timeline.events.clear()

    with ft012_database.session() as session:
        second = TaskFollowUpService(
            session, timeline_appender=timeline, clock=lambda: NOW
        ).record_outcome(command)
    assert second.result == "duplicate"
    assert second.outcome.outcome_id == outcome_id
    assert second.task.task_id == follow_up.task_id
    assert _candidate_count(ft012_database, outcome_id=outcome_id) == 1
    assert timeline.events == []


def test_ft014_ac011_conflicting_request_stays_conflict(ft012_database):
    farm = seed_farm(ft012_database)
    boss, _ = create_actor(ft012_database, farm, "boss")
    plant = create_active_plant(ft012_database, boss, plant_key="ac011_conflict")
    timeline = TimelineRecorder()

    follow_up = _open_follow_up(ft012_database, farm, boss, plant, timeline)
    evidence = _measurement(ft012_database, boss, plant, ph="6.50", measured_at=NOW)
    first = _record_outcome(
        ft012_database,
        boss,
        plant_id=plant.plant_id,
        follow_up_task_id=follow_up.task_id,
        timeline=timeline,
        value=OutcomeValue.IMPROVED,
        evidence_refs=(f"manual_measurement:{evidence.measurement_id}",),
    )
    outcome_id = first.outcome.outcome_id

    with ft012_database.session() as session, pytest.raises(TaskFollowUpError) as failed:
        TaskFollowUpService(
            session, timeline_appender=timeline, clock=lambda: NOW
        ).record_outcome(
            RecordOutcomeCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                follow_up_task_id=follow_up.task_id,
                request_id=uuid.uuid4(),
                value=OutcomeValue.WORSENED,
                evidence_refs=(f"manual_measurement:{evidence.measurement_id}",),
            )
        )
    assert failed.value.code is TaskFollowUpErrorCode.TASK_VERSION_CONFLICT
    assert _candidate_count(ft012_database, outcome_id=outcome_id) == 1
    with ft012_database.session() as session:
        assert session.scalar(select(func.count(Outcome.outcome_id))) == 1


def test_ft014_ac011_audit_failure_rolls_back_outcome_task_and_candidate(
    ft012_database,
):
    farm = seed_farm(ft012_database)
    boss, _ = create_actor(ft012_database, farm, "boss")
    plant = create_active_plant(ft012_database, boss, plant_key="ac011_audit")
    recorder = TimelineRecorder(fail_on="dataset_candidate_created")

    follow_up = _open_follow_up(ft012_database, farm, boss, plant, recorder)
    evidence = _measurement(ft012_database, boss, plant, ph="6.60", measured_at=NOW)
    with ft012_database.session() as session, pytest.raises(TaskFollowUpError) as failed:
        TaskFollowUpService(
            session,
            timeline_appender=recorder,
            clock=lambda: NOW,
            dataset_governance=DatasetGovernanceService(
                session,
                timeline_appender=recorder,
            ),
        ).record_outcome(
            RecordOutcomeCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                follow_up_task_id=follow_up.task_id,
                request_id=uuid.uuid4(),
                value=OutcomeValue.IMPROVED,
                evidence_refs=(f"manual_measurement:{evidence.measurement_id}",),
            )
        )
    assert failed.value.code is TaskFollowUpErrorCode.TASK_AUDIT_FAILED
    with ft012_database.session() as session:
        stored = session.get(Task, follow_up.task_id)
        assert stored is not None and stored.status == "open"
        assert session.scalar(select(func.count(Outcome.outcome_id))) == 0
        assert session.scalar(
            select(func.count(DatasetCandidate.candidate_id))
        ) == 0


def test_ft014_ac011_persistence_failure_rolls_back_outcome_task_and_candidate(
    ft012_database,
):
    farm = seed_farm(ft012_database)
    boss, _ = create_actor(ft012_database, farm, "boss")
    plant = create_active_plant(ft012_database, boss, plant_key="ac011_persist")
    recorder = TimelineRecorder()

    class FailingGovernance(DatasetGovernanceService):
        def record_dataset_evidence(self, command):
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.PERSISTENCE_FAILED
            )

    follow_up = _open_follow_up(ft012_database, farm, boss, plant, recorder)
    evidence = _measurement(ft012_database, boss, plant, ph="6.70", measured_at=NOW)
    with ft012_database.session() as session, pytest.raises(TaskFollowUpError) as failed:
        TaskFollowUpService(
            session,
            timeline_appender=recorder,
            clock=lambda: NOW,
            dataset_governance=FailingGovernance(session, timeline_appender=recorder),
        ).record_outcome(
            RecordOutcomeCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                follow_up_task_id=follow_up.task_id,
                request_id=uuid.uuid4(),
                value=OutcomeValue.IMPROVED,
                evidence_refs=(f"manual_measurement:{evidence.measurement_id}",),
            )
        )
    assert failed.value.code is TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
    with ft012_database.session() as session:
        stored = session.get(Task, follow_up.task_id)
        assert stored is not None and stored.status == "open"
        assert session.scalar(select(func.count(Outcome.outcome_id))) == 0
        assert session.scalar(
            select(func.count(DatasetCandidate.candidate_id))
        ) == 0


def test_ft014_ac011_archive_revoke_and_consultant_deny_before_any_write(
    ft012_database,
):
    farm = seed_farm(ft012_database)
    boss, _ = create_actor(ft012_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft012_database, farm, "engineer")
    consultant, consultant_membership = create_actor(
        ft012_database, farm, "consultant"
    )
    timeline = TimelineRecorder()

    revoked_plant = create_active_plant(ft012_database, boss, plant_key="ac011_revoked")
    grant_access(
        ft012_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    revoke_access(
        ft012_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )

    archived_plant = create_active_plant(ft012_database, boss, plant_key="ac011_archived")
    grant_access(
        ft012_database,
        boss,
        plant_id=archived_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archive_plant(ft012_database, boss, plant_id=archived_plant.plant_id)

    consultant_plant = create_active_plant(ft012_database, boss, plant_key="ac011_consultant")
    grant_access(
        ft012_database,
        boss,
        plant_id=consultant_plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )

    ungranted_plant = create_active_plant(ft012_database, boss, plant_key="ac011_ungranted")

    cases = [
        (engineer, revoked_plant, engineer_membership),
        (boss, archived_plant, None),
        (consultant, consultant_plant, consultant_membership),
        (engineer, ungranted_plant, engineer_membership),
    ]
    for actor, plant, _membership in cases:
        with ft012_database.session() as session, pytest.raises(TaskFollowUpError) as denied:
            TaskFollowUpService(
                session, timeline_appender=timeline, clock=lambda: NOW
            ).record_outcome(
                RecordOutcomeCommandV1(
                    actor_context=actor,
                    plant_id=plant.plant_id,
                    follow_up_task_id=uuid.uuid4(),
                    request_id=uuid.uuid4(),
                    value=OutcomeValue.NO_DATA,
                    evidence_refs=(),
                )
            )
        assert denied.value.code in {
            TaskFollowUpErrorCode.TASK_SCOPE_NOT_FOUND,
            TaskFollowUpErrorCode.TASK_COMMAND_FORBIDDEN,
            TaskFollowUpErrorCode.TASK_PLANT_NOT_ACTIVE,
        }

    with ft012_database.session() as session:
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
        assert session.scalar(select(func.count(Outcome.outcome_id))) == 0
    assert timeline.events == []
