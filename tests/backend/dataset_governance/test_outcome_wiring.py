"""FT-014-AC-011 wiring tests from the Dataset Governance side: the follow-up
Outcome source flow produces one exact raw candidate through the sole creation
seam inside the record_outcome unit of work."""

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
    RecordDatasetEvidenceCommandV1,
    SourceKind,
)
from backend.app.task_follow_up import (
    CompleteTaskCommandV1,
    Outcome,
    OutcomeValue,
    RecordOutcomeCommandV1,
    TaskFollowUpService,
)
from tests.backend.dataset_governance.conftest import (
    FT014_NOW,
    TimelineRecorder,
)
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
                    evidence_refs=()):
    with database.session() as session:
        service = TaskFollowUpService(
            session,
            timeline_appender=timeline,
            clock=lambda: NOW,
            dataset_governance=DatasetGovernanceService(
                session,
                timeline_appender=timeline,
                clock=lambda: FT014_NOW,
            ),
        )
        return service.record_outcome(
            RecordOutcomeCommandV1(
                actor_context=boss,
                plant_id=plant_id,
                follow_up_task_id=follow_up_task_id,
                request_id=uuid.uuid4(),
                value=OutcomeValue.NO_DATA,
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


def test_ft014_ac011_record_outcome_commits_one_exact_candidate_and_event(
    ft014_database,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_outcome_001")
    recorder = TimelineRecorder()

    follow_up = _open_follow_up(ft014_database, farm, boss, plant, recorder)
    result = _record_outcome(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        follow_up_task_id=follow_up.task_id,
        timeline=recorder,
    )
    outcome_id = result.outcome.outcome_id

    assert _candidate_count(ft014_database, outcome_id=outcome_id) == 1
    candidate = _candidate_for(ft014_database, outcome_id=outcome_id)
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
        e for e in recorder.events if e.event_type == "dataset_candidate_created"
    ]
    assert len(created_events) == 1
    assert created_events[0].source_type == "dataset_candidate"
    assert created_events[0].source_id == candidate.candidate_id
    assert created_events[0].payload_summary["source_kind"] == "follow_up_outcome"
    assert created_events[0].payload_summary["candidate_origin"] == "raw"
    assert created_events[0].payload_summary["can_train_on"] is False
    assert result.task.status == "completed"


def test_ft014_ac011_same_outcome_seam_retry_idempotent_new_outcome_new_evidence(
    ft014_database,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_outcome_idem")
    recorder = TimelineRecorder()

    follow_up = _open_follow_up(ft014_database, farm, boss, plant, recorder)
    result = _record_outcome(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        follow_up_task_id=follow_up.task_id,
        timeline=recorder,
    )
    outcome_id = result.outcome.outcome_id
    assert _candidate_count(ft014_database, outcome_id=outcome_id) == 1

    recorder.events.clear()
    with ft014_database.session() as session:
        retry = DatasetGovernanceService(
            session,
            timeline_appender=recorder,
            clock=lambda: FT014_NOW,
        ).record_dataset_evidence(
            RecordDatasetEvidenceCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                source_kind=SourceKind.FOLLOW_UP_OUTCOME,
                source_ref=outcome_id,
            )
        )
    assert retry.result == "duplicate"
    assert retry.candidate_id == _candidate_for(
        ft014_database, outcome_id=outcome_id
    ).candidate_id
    assert _candidate_count(ft014_database, outcome_id=outcome_id) == 1
    assert recorder.events == []

    second_follow_up = _open_follow_up(
        ft014_database, farm, boss, plant, recorder
    )
    second = _record_outcome(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        follow_up_task_id=second_follow_up.task_id,
        timeline=recorder,
    )
    second_outcome_id = second.outcome.outcome_id
    assert second_outcome_id != outcome_id
    assert _candidate_count(ft014_database, outcome_id=outcome_id) == 1
    assert _candidate_count(
        ft014_database, outcome_id=second_outcome_id
    ) == 1
    assert (
        _candidate_for(ft014_database, outcome_id=outcome_id).candidate_id
        != _candidate_for(ft014_database, outcome_id=second_outcome_id).candidate_id
    )


def test_ft014_ac011_evidence_outcome_and_no_data_outcome_each_get_candidate(
    ft014_database,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_outcome_evid")
    recorder = TimelineRecorder()

    evidence_follow_up = _open_follow_up(
        ft014_database, farm, boss, plant, recorder
    )
    evidence = _measurement(
        ft014_database, boss, plant, ph="6.50", measured_at=NOW
    )
    evidenced = _record_outcome(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        follow_up_task_id=evidence_follow_up.task_id,
        timeline=recorder,
        evidence_refs=(f"manual_measurement:{evidence.measurement_id}",),
    )
    no_data_follow_up = _open_follow_up(ft014_database, farm, boss, plant, recorder)
    no_data = _record_outcome(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        follow_up_task_id=no_data_follow_up.task_id,
        timeline=recorder,
    )
    assert _candidate_count(ft014_database, outcome_id=evidenced.outcome.outcome_id) == 1
    assert _candidate_count(ft014_database, outcome_id=no_data.outcome.outcome_id) == 1


def test_ft014_ac011_audit_failure_rolls_back_outcome_and_candidate(ft014_database):
    from backend.app.task_follow_up import TaskFollowUpError, TaskFollowUpErrorCode

    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_outcome_audit")
    recorder = TimelineRecorder(fail_on="dataset_candidate_created")

    follow_up = _open_follow_up(ft014_database, farm, boss, plant, recorder)
    with ft014_database.session() as session, pytest.raises(TaskFollowUpError) as failed:
        TaskFollowUpService(
            session,
            timeline_appender=recorder,
            clock=lambda: NOW,
            dataset_governance=DatasetGovernanceService(
                session,
                timeline_appender=recorder,
                clock=lambda: FT014_NOW,
            ),
        ).record_outcome(
            RecordOutcomeCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                follow_up_task_id=follow_up.task_id,
                request_id=uuid.uuid4(),
                value=OutcomeValue.NO_DATA,
                evidence_refs=(),
            )
        )
    assert failed.value.code is TaskFollowUpErrorCode.TASK_AUDIT_FAILED
    with ft014_database.session() as session:
        assert session.scalar(select(func.count(Outcome.outcome_id))) == 0
        assert session.scalar(
            select(func.count(DatasetCandidate.candidate_id))
        ) == 0


def test_ft014_ac011_unauthorized_and_archived_plant_creates_no_candidate(
    ft014_database,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft014_database, farm, "engineer")
    consultant, consultant_membership = create_actor(
        ft014_database, farm, "consultant"
    )
    recorder = TimelineRecorder()

    revoked_plant = create_active_plant(
        ft014_database, boss, plant_key="wire_outcome_revoked"
    )
    grant_access(
        ft014_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    revoke_access(
        ft014_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archived_plant = create_active_plant(
        ft014_database, boss, plant_key="wire_outcome_archived"
    )
    grant_access(
        ft014_database,
        boss,
        plant_id=archived_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archive_plant(ft014_database, boss, plant_id=archived_plant.plant_id)
    consultant_plant = create_active_plant(
        ft014_database, boss, plant_key="wire_outcome_consultant"
    )
    grant_access(
        ft014_database,
        boss,
        plant_id=consultant_plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )
    ungranted_plant = create_active_plant(
        ft014_database, boss, plant_key="wire_outcome_ungranted"
    )

    outcome_id = uuid.uuid4()
    for actor, plant in [
        (engineer, revoked_plant),
        (boss, archived_plant),
        (consultant, consultant_plant),
        (engineer, ungranted_plant),
    ]:
        with ft014_database.session() as session, pytest.raises(
            DatasetGovernanceError
        ) as denied:
            DatasetGovernanceService(
                session,
                timeline_appender=recorder,
                clock=lambda: FT014_NOW,
            ).record_dataset_evidence(
                RecordDatasetEvidenceCommandV1(
                    actor_context=actor,
                    plant_id=plant.plant_id,
                    source_kind=SourceKind.FOLLOW_UP_OUTCOME,
                    source_ref=outcome_id,
                )
            )
        assert denied.value.code is DatasetGovernanceErrorCode.CONTEXT_FORBIDDEN

    with ft014_database.session() as session:
        assert session.scalar(
            select(func.count(DatasetCandidate.candidate_id))
        ) == 0
    assert recorder.events == []
