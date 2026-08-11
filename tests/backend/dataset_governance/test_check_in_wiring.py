from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.app.dataset_governance import (
    DatasetCandidate,
    DatasetGovernanceService,
    DatasetGovernanceError,
    DatasetGovernanceErrorCode,
    RecordDatasetEvidenceCommandV1,
    SourceKind,
)
from backend.app.plant_operations import (
    DailyCheckIn,
    ManualMeasurement,
    ManualMeasurementInput,
    PlantOperationError,
    PlantOperationErrorCode,
    PlantOperationsService,
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


def _candidate_count(database, *, plant_id, check_in_id) -> int:
    with database.session() as session:
        return session.scalar(
            select(func.count(DatasetCandidate.candidate_id)).where(
                DatasetCandidate.plant_id == plant_id,
                DatasetCandidate.source_kind == SourceKind.DAILY_CHECK_IN.value,
                DatasetCandidate.source_ref == check_in_id,
            )
        )


def _candidate_for(database, *, check_in_id):
    with database.session() as session:
        return session.scalar(
            select(DatasetCandidate).where(DatasetCandidate.source_ref == check_in_id)
        )


def _create_check_in(
    database,
    actor,
    *,
    plant_id,
    recorder,
    observation_state="observed",
    observation_text="Wiring check-in",
    measurement=None,
):
    with database.session() as session:
        service = PlantOperationsService(
            session,
            timeline_append=recorder,
            dataset_governance=DatasetGovernanceService(
                session,
                timeline_appender=recorder,
                clock=lambda: FT014_NOW,
            ),
        )
        return service.create_check_in(
            actor,
            plant_id=plant_id,
            observation_state=observation_state,
            observation_text=observation_text,
            measurement=measurement,
        )


def test_ft014_ac009_check_in_only_creates_exact_candidate_and_event_in_same_uow(
    ft014_database,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft014_database, farm, "engineer")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_ci_001")
    grant_access(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    recorder = TimelineRecorder()

    result = _create_check_in(
        ft014_database,
        engineer,
        plant_id=plant.plant_id,
        recorder=recorder,
        observation_state="observed",
        observation_text="Check-in only",
    )
    check_in_id = result.check_in.check_in_id

    assert _candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        check_in_id=check_in_id,
    ) == 1
    candidate = _candidate_for(ft014_database, check_in_id=check_in_id)
    assert candidate.farm_id == farm.farm_id
    assert candidate.plant_id == plant.plant_id
    assert candidate.candidate_status == "candidate"
    assert candidate.candidate_origin == "raw"
    assert candidate.quality_tier == "standard"
    assert candidate.split is None
    assert candidate.confirmation_source is None
    assert candidate.can_train_on is False
    assert candidate.follow_up_seen is False
    assert candidate.curator_run_id is None
    assert candidate.curator_command_sha256 is None
    assert candidate.curator_recorded_at is None
    assert candidate.corrected is False
    assert candidate.record_version == 1
    assert candidate.evidence_refs == [
        {"kind": "observation", "ref": str(check_in_id)}
    ]
    assert candidate.source_kind == "daily_check_in"
    assert candidate.source_ref == check_in_id
    assert len(candidate.event_refs) == 1
    created = candidate.event_refs[0]
    assert created["event_type"] == "dataset_candidate_created"
    assert created["timeline_ref"].startswith("timeline.jsonl#")
    assert uuid.UUID(created["timeline_event_id"])

    created_events = [
        e
        for e in recorder.events
        if e.event_type == "dataset_candidate_created"
    ]
    assert len(created_events) == 1
    assert created_events[0].source_type == "dataset_candidate"
    assert created_events[0].source_id == candidate.candidate_id
    assert created_events[0].payload_summary["source_kind"] == "daily_check_in"
    assert created_events[0].payload_summary["candidate_origin"] == "raw"
    assert created_events[0].payload_summary["can_train_on"] is False

    assert result.check_in.observation_state == "observed"
    assert result.check_in.event_refs.keys() == {"daily_checkin_recorded"}
    assert len(result.measurements) == 0
    assert result.freshness.computed_at is not None


def test_ft014_ac009_check_in_with_measurement_creates_measurement_candidate_too(
    ft014_database,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft014_database, farm, "engineer")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_ci_002")
    grant_access(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    recorder = TimelineRecorder()

    result = _create_check_in(
        ft014_database,
        engineer,
        plant_id=plant.plant_id,
        recorder=recorder,
        observation_state="observed",
        observation_text="Check-in with measurement",
        measurement=ManualMeasurementInput(ph="6.50", ec_ms_cm="1.250"),
    )
    check_in_id = result.check_in.check_in_id
    measurement_id = result.measurements[0].measurement_id

    with ft014_database.session() as session:
        assert session.scalar(select(func.count(DailyCheckIn.check_in_id))) == 1
        assert session.scalar(select(func.count(ManualMeasurement.measurement_id))) == 1

    assert _candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        check_in_id=check_in_id,
    ) == 1
    candidate = _candidate_for(ft014_database, check_in_id=check_in_id)
    assert candidate.evidence_refs == [
        {"kind": "observation", "ref": str(check_in_id)}
    ]

    with ft014_database.session() as session:
        measurement_candidate = session.scalar(
            select(DatasetCandidate).where(
                DatasetCandidate.source_ref == measurement_id
            )
        )
        assert measurement_candidate is not None
        assert measurement_candidate.source_kind == SourceKind.MANUAL_MEASUREMENT.value
        assert measurement_candidate.candidate_origin == "raw"
        assert measurement_candidate.can_train_on is False
        assert measurement_candidate.evidence_refs == [
            {"kind": "measurement", "ref": str(measurement_id)}
        ]
        assert len(measurement_candidate.event_refs) == 1
        assert measurement_candidate.candidate_id != candidate.candidate_id
    assert result.freshness.latest_ph_ref == measurement_id


def test_ft014_ac009_same_check_in_seam_retry_is_idempotent_and_new_check_in_is_new_evidence(
    ft014_database,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft014_database, farm, "engineer")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_idem_ci_001")
    grant_access(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    recorder = TimelineRecorder()

    result = _create_check_in(
        ft014_database,
        engineer,
        plant_id=plant.plant_id,
        recorder=recorder,
        observation_state="no_observation_provided",
        observation_text=None,
    )
    check_in_id = result.check_in.check_in_id
    assert _candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        check_in_id=check_in_id,
    ) == 1

    recorder.events.clear()
    with ft014_database.session() as session:
        retry = DatasetGovernanceService(
            session,
            timeline_appender=recorder,
            clock=lambda: FT014_NOW,
        ).record_dataset_evidence(
            RecordDatasetEvidenceCommandV1(
                actor_context=engineer,
                plant_id=plant.plant_id,
                source_kind=SourceKind.DAILY_CHECK_IN,
                source_ref=check_in_id,
            )
        )
    assert retry.result == "duplicate"
    assert retry.candidate_id == _candidate_for(
        ft014_database,
        check_in_id=check_in_id,
    ).candidate_id
    assert _candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        check_in_id=check_in_id,
    ) == 1
    assert recorder.events == []

    second = _create_check_in(
        ft014_database,
        engineer,
        plant_id=plant.plant_id,
        recorder=recorder,
        observation_state="observed",
        observation_text="Distinct new check-in",
    )
    assert second.check_in.check_in_id != check_in_id
    assert _candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        check_in_id=check_in_id,
    ) == 1
    assert _candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        check_in_id=second.check_in.check_in_id,
    ) == 1


def test_ft014_ac009_audit_failure_rolls_back_check_in_measurement_and_candidate(
    ft014_database,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft014_database, farm, "engineer")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_audit_ci_001")
    grant_access(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    recorder = TimelineRecorder(fail_on="dataset_candidate_created")

    with ft014_database.session() as session:
        with pytest.raises(PlantOperationError) as failure:
            PlantOperationsService(
                session,
                timeline_append=recorder,
                dataset_governance=DatasetGovernanceService(
                    session,
                    timeline_appender=recorder,
                    clock=lambda: FT014_NOW,
                ),
            ).create_check_in(
                engineer,
                plant_id=plant.plant_id,
                observation_state="observed",
                observation_text="Audit failure",
                measurement=ManualMeasurementInput(ph="6.50"),
            )

    assert failure.value.code is PlantOperationErrorCode.OPERATION_PERSISTENCE_FAILED
    with ft014_database.session() as session:
        assert session.scalar(select(func.count(DailyCheckIn.check_in_id))) == 0
        assert session.scalar(select(func.count(ManualMeasurement.measurement_id))) == 0
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0


def test_ft014_ac009_persistence_failure_rolls_back_check_in_measurement_and_candidate(
    ft014_database,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft014_database, farm, "engineer")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_persist_ci_001")
    grant_access(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    recorder = TimelineRecorder()

    class FailingGovernance(DatasetGovernanceService):
        def record_dataset_evidence(self, command):
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.PERSISTENCE_FAILED
            )

    with ft014_database.session() as session:
        with pytest.raises(PlantOperationError) as failure:
            PlantOperationsService(
                session,
                timeline_append=recorder,
                dataset_governance=FailingGovernance(
                    session,
                    timeline_appender=recorder,
                ),
            ).create_check_in(
                engineer,
                plant_id=plant.plant_id,
                observation_state="observed",
                observation_text="Persistence failure",
                measurement=ManualMeasurementInput(ec_ms_cm="1.250"),
            )

    assert failure.value.code is PlantOperationErrorCode.OPERATION_PERSISTENCE_FAILED
    with ft014_database.session() as session:
        assert session.scalar(select(func.count(DailyCheckIn.check_in_id))) == 0
        assert session.scalar(select(func.count(ManualMeasurement.measurement_id))) == 0
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0


def test_ft014_ac009_unauthorized_and_archived_plant_check_in_creates_neither(
    ft014_database,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft014_database, farm, "engineer")
    consultant, consultant_membership = create_actor(
        ft014_database, farm, "consultant"
    )
    recorder = TimelineRecorder()

    revoked_plant = create_active_plant(ft014_database, boss, plant_key="wire_revoked_ci")
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
        ft014_database, boss, plant_key="wire_archived_ci"
    )
    grant_access(
        ft014_database,
        boss,
        plant_id=archived_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archive_plant(ft014_database, boss, plant_id=archived_plant.plant_id)

    consultant_plant = create_active_plant(
        ft014_database, boss, plant_key="wire_consultant_ci"
    )
    grant_access(
        ft014_database,
        boss,
        plant_id=consultant_plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )

    cases = [
        (engineer, revoked_plant),
        (boss, archived_plant),
        (consultant, consultant_plant),
        (engineer, create_active_plant(ft014_database, boss, plant_key="wire_ungranted_ci")),
    ]
    for actor, plant in cases:
        with ft014_database.session() as session:
            with pytest.raises(PlantOperationError) as denied:
                PlantOperationsService(
                    session,
                    timeline_append=recorder,
                ).create_check_in(
                    actor,
                    plant_id=plant.plant_id,
                    observation_state="observed",
                    observation_text="Denied",
                )
        assert denied.value.code is PlantOperationErrorCode.AUTH_PLANT_FORBIDDEN

    with ft014_database.session() as session:
        assert session.scalar(select(func.count(DailyCheckIn.check_in_id))) == 0
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
    assert recorder.events == []
