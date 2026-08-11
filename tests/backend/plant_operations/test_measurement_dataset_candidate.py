from __future__ import annotations

import uuid

from sqlalchemy import func, select

from backend.app.dataset_governance import DatasetCandidate, SourceKind
from backend.app.plant_operations import (
    ManualMeasurementInput,
    PlantOperationError,
    PlantOperationsService,
)
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    create_active_plant,
    grant_access,
    row_counts,
    seed_farm,
)


def _candidate_for_measurement(database, *, measurement_id):
    with database.session() as session:
        return session.scalar(
            select(DatasetCandidate).where(
                DatasetCandidate.source_ref == measurement_id
            )
        )


def _measurement_candidate_count(database, *, plant_id) -> int:
    with database.session() as session:
        return session.scalar(
            select(func.count(DatasetCandidate.candidate_id)).where(
                DatasetCandidate.plant_id == plant_id,
                DatasetCandidate.source_kind == SourceKind.MANUAL_MEASUREMENT.value,
            )
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


def test_create_manual_measurement_default_seam_creates_one_non_trainable_candidate(
    ft004_database,
    event_ref_factory,
):
    farm, _boss, engineer, plant = _seed_engineer(
        ft004_database, plant_key="candidate_meas_001"
    )

    with ft004_database.session() as session:
        result = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).create_manual_measurement(
            engineer,
            plant_id=plant.plant_id,
            measurement=ManualMeasurementInput(ph="6.50", ec_ms_cm="1.250"),
        )

    measurement_id = result.measurement.measurement_id
    assert row_counts(ft004_database) == (0, 1)
    assert result.measurement.source_type == "manual_user"
    assert result.measurement.trust_status == "confirmed"
    assert result.measurement.event_refs.keys() == {"manual_measurement_recorded"}

    candidate = _candidate_for_measurement(ft004_database, measurement_id=measurement_id)
    assert candidate is not None
    assert candidate.farm_id == farm.farm_id
    assert candidate.plant_id == plant.plant_id
    assert candidate.source_kind == SourceKind.MANUAL_MEASUREMENT.value
    assert candidate.source_ref == measurement_id
    assert candidate.candidate_status == "candidate"
    assert candidate.candidate_origin == "raw"
    assert candidate.quality_tier == "standard"
    assert candidate.split is None
    assert candidate.confirmation_source is None
    assert candidate.can_train_on is False
    assert candidate.evidence_refs == [
        {"kind": "measurement", "ref": str(measurement_id)}
    ]
    assert len(candidate.event_refs) == 1
    assert candidate.event_refs[0]["event_type"] == "dataset_candidate_created"

    created = [
        e
        for e in event_ref_factory.events
        if e.event_type == "dataset_candidate_created"
    ]
    assert len(created) == 1
    assert created[0].source_id == candidate.candidate_id

    assert result.freshness.latest_ph_ref == measurement_id
    assert result.freshness.latest_ec_ref == measurement_id


def test_measurement_inside_check_in_creates_measurement_candidate(
    ft004_database,
    event_ref_factory,
):
    farm, _boss, engineer, plant = _seed_engineer(
        ft004_database, plant_key="candidate_meas_ci_001"
    )

    with ft004_database.session() as session:
        result = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).create_check_in(
            engineer,
            plant_id=plant.plant_id,
            observation_state="observed",
            observation_text="Check-in with measurement",
            measurement=ManualMeasurementInput(ph="6.50"),
        )

    measurement_id = result.measurements[0].measurement_id
    check_in_id = result.check_in.check_in_id
    assert row_counts(ft004_database) == (1, 1)

    measurement_candidate = _candidate_for_measurement(
        ft004_database, measurement_id=measurement_id
    )
    check_in_candidate = _candidate_for_measurement(
        ft004_database, measurement_id=check_in_id
    )
    assert measurement_candidate is not None
    assert check_in_candidate is not None
    assert measurement_candidate.candidate_id != check_in_candidate.candidate_id
    assert measurement_candidate.source_kind == SourceKind.MANUAL_MEASUREMENT.value
    assert check_in_candidate.source_kind == SourceKind.DAILY_CHECK_IN.value
    assert measurement_candidate.evidence_refs == [
        {"kind": "measurement", "ref": str(measurement_id)}
    ]

    created = [
        e
        for e in event_ref_factory.events
        if e.event_type == "dataset_candidate_created"
    ]
    assert len(created) == 2
    assert {e.source_id for e in created} == {
        measurement_candidate.candidate_id,
        check_in_candidate.candidate_id,
    }


def test_two_measurements_are_distinct_candidates_and_new_row_identity(
    ft004_database,
    event_ref_factory,
):
    farm, _boss, engineer, plant = _seed_engineer(
        ft004_database, plant_key="candidate_meas_002"
    )

    first = None
    second = None
    with ft004_database.session() as session:
        service = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        )
        first = service.create_manual_measurement(
            engineer,
            plant_id=plant.plant_id,
            measurement=ManualMeasurementInput(ph="6.50"),
        )
        second = service.create_manual_measurement(
            engineer,
            plant_id=plant.plant_id,
            measurement=ManualMeasurementInput(ph="6.70"),
        )

    assert first.measurement.measurement_id != second.measurement.measurement_id
    assert row_counts(ft004_database) == (0, 2)

    first_candidate = _candidate_for_measurement(
        ft004_database, measurement_id=first.measurement.measurement_id
    )
    second_candidate = _candidate_for_measurement(
        ft004_database, measurement_id=second.measurement.measurement_id
    )
    assert first_candidate.candidate_id != second_candidate.candidate_id
    assert first_candidate.source_ref == first.measurement.measurement_id
    assert second_candidate.source_ref == second.measurement.measurement_id
    assert _measurement_candidate_count(
        ft004_database, plant_id=plant.plant_id
    ) == 2


def test_archived_plant_measurement_creates_no_source_row_and_no_candidate(
    ft004_database,
    event_ref_factory,
):
    farm, boss, engineer, plant = _seed_engineer(
        ft004_database, plant_key="candidate_meas_arch"
    )
    archive_plant(ft004_database, boss, plant_id=plant.plant_id)

    with ft004_database.session() as session:
        try:
            PlantOperationsService(
                session,
                timeline_append=event_ref_factory,
            ).create_manual_measurement(
                engineer,
                plant_id=plant.plant_id,
                measurement=ManualMeasurementInput(ph="6.50"),
            )
        except PlantOperationError:
            pass
        else:
            raise AssertionError("archived-Plant measurement must fail")

    assert row_counts(ft004_database) == (0, 0)
    with ft004_database.session() as session:
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
    assert event_ref_factory.events == []


def test_unknown_plant_id_measurement_creates_no_candidate(
    ft004_database,
    event_ref_factory,
):
    farm, _boss, engineer, _plant = _seed_engineer(
        ft004_database, plant_key="candidate_meas_unknown"
    )
    with ft004_database.session() as session:
        try:
            PlantOperationsService(
                session,
                timeline_append=event_ref_factory,
            ).create_manual_measurement(
                engineer,
                plant_id=uuid.uuid4(),
                measurement=ManualMeasurementInput(ph="6.50"),
            )
        except PlantOperationError:
            pass
        else:
            raise AssertionError("unknown-Plant measurement must fail")

    assert row_counts(ft004_database) == (0, 0)
    with ft004_database.session() as session:
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
    assert event_ref_factory.events == []
