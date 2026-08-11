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


def _measurement_candidate_count(database, *, plant_id, measurement_id) -> int:
    with database.session() as session:
        return session.scalar(
            select(func.count(DatasetCandidate.candidate_id)).where(
                DatasetCandidate.plant_id == plant_id,
                DatasetCandidate.source_kind == SourceKind.MANUAL_MEASUREMENT.value,
                DatasetCandidate.source_ref == measurement_id,
            )
        )


def _candidate_for(database, *, measurement_id):
    with database.session() as session:
        return session.scalar(
            select(DatasetCandidate).where(
                DatasetCandidate.source_ref == measurement_id
            )
        )


def _create_measurement(
    database,
    actor,
    *,
    plant_id,
    recorder,
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
        return service.create_manual_measurement(
            actor,
            plant_id=plant_id,
            measurement=measurement
            or ManualMeasurementInput(ph="6.50", ec_ms_cm="1.250"),
        )


def _seed_engineer(database, *, plant_key):
    farm = seed_farm(database)
    boss, _ = create_actor(database, farm, "boss")
    engineer, engineer_membership = create_actor(database, farm, "engineer")
    plant = create_active_plant(database, boss, plant_key=plant_key)
    grant_access(
        database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    return farm, boss, engineer, plant


def test_ft014_ac010_standalone_measurement_creates_exact_candidate_and_event_in_same_uow(
    ft014_database,
):
    farm, boss, engineer, plant = _seed_engineer(
        ft014_database, plant_key="wire_meas_001"
    )
    recorder = TimelineRecorder()

    result = _create_measurement(
        ft014_database,
        engineer,
        plant_id=plant.plant_id,
        recorder=recorder,
        measurement=ManualMeasurementInput(ph="6.50", ec_ms_cm="1.250"),
    )
    measurement_id = result.measurement.measurement_id

    assert _measurement_candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        measurement_id=measurement_id,
    ) == 1
    candidate = _candidate_for(ft014_database, measurement_id=measurement_id)
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
        {"kind": "measurement", "ref": str(measurement_id)}
    ]
    assert candidate.source_kind == "manual_measurement"
    assert candidate.source_ref == measurement_id
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
    assert created_events[0].payload_summary["source_kind"] == "manual_measurement"
    assert created_events[0].payload_summary["candidate_origin"] == "raw"
    assert created_events[0].payload_summary["can_train_on"] is False

    assert result.measurement.source_type == "manual_user"
    assert result.measurement.trust_status == "confirmed"
    assert result.measurement.event_refs.keys() == {"manual_measurement_recorded"}
    assert result.freshness.latest_ph_ref == measurement_id
    assert result.freshness.latest_ec_ref == measurement_id
    assert result.freshness.computed_at is not None


def test_ft014_ac010_check_in_owned_measurement_creates_exact_candidate(
    ft014_database,
):
    farm, boss, engineer, plant = _seed_engineer(
        ft014_database, plant_key="wire_meas_ci_001"
    )
    recorder = TimelineRecorder()

    with ft014_database.session() as session:
        service = PlantOperationsService(
            session,
            timeline_append=recorder,
            dataset_governance=DatasetGovernanceService(
                session,
                timeline_appender=recorder,
                clock=lambda: FT014_NOW,
            ),
        )
        result = service.create_check_in(
            engineer,
            plant_id=plant.plant_id,
            observation_state="observed",
            observation_text="Check-in with measurement",
            measurement=ManualMeasurementInput(ph="6.50", ec_ms_cm="1.250"),
        )
    measurement_id = result.measurements[0].measurement_id
    check_in_id = result.check_in.check_in_id

    with ft014_database.session() as session:
        assert session.scalar(select(func.count(DailyCheckIn.check_in_id))) == 1
        assert session.scalar(select(func.count(ManualMeasurement.measurement_id))) == 1

    assert _measurement_candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        measurement_id=measurement_id,
    ) == 1
    candidate = _candidate_for(ft014_database, measurement_id=measurement_id)
    assert candidate.candidate_origin == "raw"
    assert candidate.can_train_on is False
    assert candidate.evidence_refs == [
        {"kind": "measurement", "ref": str(measurement_id)}
    ]
    assert candidate.source_kind == "manual_measurement"
    assert candidate.source_ref == measurement_id
    assert len(candidate.event_refs) == 1

    check_in_candidate = _candidate_for(ft014_database, measurement_id=check_in_id)
    assert check_in_candidate.source_kind == "daily_check_in"
    assert check_in_candidate.candidate_id != candidate.candidate_id
    with ft014_database.session() as session:
        assert session.scalar(
            select(func.count(DatasetCandidate.candidate_id)).where(
                DatasetCandidate.plant_id == plant.plant_id
            )
        ) == 2
    assert result.freshness.latest_ph_ref == measurement_id


def test_ft014_ac010_same_measurement_seam_retry_is_idempotent_and_new_measurement_is_new_evidence(
    ft014_database,
):
    farm, boss, engineer, plant = _seed_engineer(
        ft014_database, plant_key="wire_idem_meas_001"
    )
    recorder = TimelineRecorder()

    result = _create_measurement(
        ft014_database,
        engineer,
        plant_id=plant.plant_id,
        recorder=recorder,
        measurement=ManualMeasurementInput(ph="6.50"),
    )
    measurement_id = result.measurement.measurement_id
    assert _measurement_candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        measurement_id=measurement_id,
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
                source_kind=SourceKind.MANUAL_MEASUREMENT,
                source_ref=measurement_id,
            )
        )
    assert retry.result == "duplicate"
    assert retry.candidate_id == _candidate_for(
        ft014_database, measurement_id=measurement_id
    ).candidate_id
    assert _measurement_candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        measurement_id=measurement_id,
    ) == 1
    assert recorder.events == []

    second = _create_measurement(
        ft014_database,
        engineer,
        plant_id=plant.plant_id,
        recorder=recorder,
        measurement=ManualMeasurementInput(ec_ms_cm="2.000"),
    )
    second_id = second.measurement.measurement_id
    assert second_id != measurement_id
    assert _measurement_candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        measurement_id=measurement_id,
    ) == 1
    assert _measurement_candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        measurement_id=second_id,
    ) == 1


def test_ft014_ac010_audit_failure_rolls_back_measurement_and_candidate(
    ft014_database,
):
    farm, boss, engineer, plant = _seed_engineer(
        ft014_database, plant_key="wire_audit_meas_001"
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
            ).create_manual_measurement(
                engineer,
                plant_id=plant.plant_id,
                measurement=ManualMeasurementInput(ph="6.50"),
            )

    assert failure.value.code is PlantOperationErrorCode.OPERATION_DATASET_AUDIT_FAILED
    with ft014_database.session() as session:
        assert session.scalar(select(func.count(ManualMeasurement.measurement_id))) == 0
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0


def test_ft014_ac010_persistence_failure_rolls_back_measurement_and_candidate(
    ft014_database,
):
    farm, boss, engineer, plant = _seed_engineer(
        ft014_database, plant_key="wire_persist_meas_001"
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
            ).create_manual_measurement(
                engineer,
                plant_id=plant.plant_id,
                measurement=ManualMeasurementInput(ec_ms_cm="1.250"),
            )

    assert failure.value.code is PlantOperationErrorCode.OPERATION_PERSISTENCE_FAILED
    with ft014_database.session() as session:
        assert session.scalar(select(func.count(ManualMeasurement.measurement_id))) == 0
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0


def test_ft014_ac010_unauthorized_and_archived_plant_measurement_creates_neither(
    ft014_database,
):
    farm, boss, engineer, _ = _seed_engineer(
        ft014_database, plant_key="wire_revoked_meas"
    )
    consultant, consultant_membership = create_actor(
        ft014_database, farm, "consultant"
    )
    recorder = TimelineRecorder()

    engineer_membership = engineer.membership_id
    revoked_plant = create_active_plant(ft014_database, boss, plant_key="wire_revoked_meas_p")
    grant_access(
        ft014_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership,
    )
    revoke_access(
        ft014_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership,
    )

    archived_plant = create_active_plant(ft014_database, boss, plant_key="wire_archived_meas")
    grant_access(
        ft014_database,
        boss,
        plant_id=archived_plant.plant_id,
        membership_id=engineer_membership,
    )
    archive_plant(ft014_database, boss, plant_id=archived_plant.plant_id)

    consultant_plant = create_active_plant(
        ft014_database, boss, plant_key="wire_consultant_meas"
    )
    grant_access(
        ft014_database,
        boss,
        plant_id=consultant_plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )

    ungranted_plant = create_active_plant(
        ft014_database, boss, plant_key="wire_ungranted_meas"
    )

    cases = [
        (engineer, revoked_plant),
        (boss, archived_plant),
        (consultant, consultant_plant),
        (engineer, ungranted_plant),
    ]
    for actor, plant in cases:
        with ft014_database.session() as session:
            with pytest.raises(PlantOperationError) as denied:
                PlantOperationsService(
                    session,
                    timeline_append=recorder,
                ).create_manual_measurement(
                    actor,
                    plant_id=plant.plant_id,
                    measurement=ManualMeasurementInput(ph="6.50"),
                )
        assert denied.value.code is PlantOperationErrorCode.AUTH_PLANT_FORBIDDEN

    with ft014_database.session() as session:
        assert session.scalar(select(func.count(ManualMeasurement.measurement_id))) == 0
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
    assert recorder.events == []


def test_ft014_ac010_measurement_values_freshness_and_public_shape_unchanged(
    ft014_database,
):
    from decimal import Decimal

    farm, boss, engineer, plant = _seed_engineer(
        ft014_database, plant_key="wire_unchanged_meas"
    )
    recorder = TimelineRecorder()

    result = _create_measurement(
        ft014_database,
        engineer,
        plant_id=plant.plant_id,
        recorder=recorder,
        measurement=ManualMeasurementInput(ph="6.555", ec_ms_cm="1.2345"),
    )
    measurement_id = result.measurement.measurement_id

    assert result.measurement.ph == Decimal("6.56")
    assert result.measurement.ec_ms_cm == Decimal("1.235")
    assert result.measurement.event_refs.keys() == {"manual_measurement_recorded"}
    assert result.freshness.latest_ph == Decimal("6.56")
    assert result.freshness.latest_ec_ms_cm == Decimal("1.235")
    assert result.freshness.latest_ph_ref == measurement_id
    assert result.freshness.latest_ec_ref == measurement_id

    with ft014_database.session() as session:
        persisted = session.get(ManualMeasurement, measurement_id)
        assert persisted.ph == Decimal("6.56")
        assert persisted.ec_ms_cm == Decimal("1.235")
        assert persisted.source_type == "manual_user"
        assert persisted.trust_status == "confirmed"

    measurement_events = [
        e for e in recorder.events if e.event_type == "manual_measurement_recorded"
    ]
    assert len(measurement_events) == 1
    assert measurement_events[0].payload_summary["ph"] == Decimal("6.56")
    assert measurement_events[0].payload_summary["ec_ms_cm"] == Decimal("1.235")

    created_events = [
        e for e in recorder.events if e.event_type == "dataset_candidate_created"
    ]
    assert len(created_events) == 1
    assert "ph" not in created_events[0].payload_summary
    assert "ec_ms_cm" not in created_events[0].payload_summary
