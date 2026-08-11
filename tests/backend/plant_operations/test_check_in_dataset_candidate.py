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


def _candidate_for_check_in(database, *, check_in_id):
    with database.session() as session:
        return session.scalar(
            select(DatasetCandidate).where(DatasetCandidate.source_ref == check_in_id)
        )


def test_create_check_in_default_seam_creates_one_non_trainable_candidate(
    ft004_database,
    event_ref_factory,
):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft004_database, farm, "engineer")
    plant = create_active_plant(ft004_database, boss, plant_key="candidate_ci_001")
    grant_access(
        ft004_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )

    with ft004_database.session() as session:
        result = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).create_check_in(
            engineer,
            plant_id=plant.plant_id,
            observation_state="observed",
            observation_text="  Leaves are upright.  ",
            measurement=ManualMeasurementInput(ph="6.50", ec_ms_cm="1.250"),
        )

    check_in_id = result.check_in.check_in_id
    assert row_counts(ft004_database) == (1, 1)
    assert result.check_in.observation_text == "Leaves are upright."
    assert result.check_in.event_refs.keys() == {"daily_checkin_recorded"}

    candidate = _candidate_for_check_in(ft004_database, check_in_id=check_in_id)
    assert candidate is not None
    assert candidate.farm_id == farm.farm_id
    assert candidate.plant_id == plant.plant_id
    assert candidate.source_kind == SourceKind.DAILY_CHECK_IN.value
    assert candidate.source_ref == check_in_id
    assert candidate.candidate_status == "candidate"
    assert candidate.candidate_origin == "raw"
    assert candidate.quality_tier == "standard"
    assert candidate.split is None
    assert candidate.confirmation_source is None
    assert candidate.can_train_on is False
    assert candidate.evidence_refs == [{"kind": "observation", "ref": str(check_in_id)}]
    assert len(candidate.event_refs) == 1
    assert candidate.event_refs[0]["event_type"] == "dataset_candidate_created"

    created = [
        e
        for e in event_ref_factory.events
        if e.event_type == "dataset_candidate_created"
    ]
    assert len(created) == 2
    assert candidate.candidate_id in {e.source_id for e in created}

    with ft004_database.session() as session:
        measurement_candidate = session.scalar(
            select(DatasetCandidate).where(
                DatasetCandidate.source_ref == result.measurements[0].measurement_id
            )
        )
    assert measurement_candidate is not None
    assert measurement_candidate.source_kind == SourceKind.MANUAL_MEASUREMENT.value
    assert measurement_candidate.evidence_refs == [
        {"kind": "measurement", "ref": str(result.measurements[0].measurement_id)}
    ]
    assert measurement_candidate.can_train_on is False
    assert len(measurement_candidate.event_refs) == 1
    assert {e.source_id for e in created} == {
        candidate.candidate_id,
        measurement_candidate.candidate_id,
    }


def test_two_check_ins_are_distinct_candidates_and_new_row_identity(
    ft004_database,
    event_ref_factory,
):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft004_database, farm, "engineer")
    plant = create_active_plant(ft004_database, boss, plant_key="candidate_ci_002")
    grant_access(
        ft004_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )

    first = None
    second = None
    with ft004_database.session() as session:
        service = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        )
        first = service.create_check_in(
            engineer,
            plant_id=plant.plant_id,
            observation_state="observed",
            observation_text="First check-in",
        )
        second = service.create_check_in(
            engineer,
            plant_id=plant.plant_id,
            observation_state="observed",
            observation_text="Second check-in",
        )

    assert first.check_in.check_in_id != second.check_in.check_in_id
    assert row_counts(ft004_database) == (2, 0)
    assert first.check_in.event_refs.keys() == {"daily_checkin_recorded"}
    assert second.check_in.event_refs.keys() == {"daily_checkin_recorded"}

    first_candidate = _candidate_for_check_in(
        ft004_database,
        check_in_id=first.check_in.check_in_id,
    )
    second_candidate = _candidate_for_check_in(
        ft004_database,
        check_in_id=second.check_in.check_in_id,
    )
    assert first_candidate.candidate_id != second_candidate.candidate_id
    assert first_candidate.source_ref == first.check_in.check_in_id
    assert second_candidate.source_ref == second.check_in.check_in_id

    with ft004_database.session() as session:
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 2


def test_archived_plant_check_in_creates_no_source_row_and_no_candidate(
    ft004_database,
    event_ref_factory,
):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft004_database, farm, "engineer")
    plant = create_active_plant(ft004_database, boss, plant_key="candidate_ci_arch")
    grant_access(
        ft004_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archive_plant(ft004_database, boss, plant_id=plant.plant_id)

    with ft004_database.session() as session:
        try:
            PlantOperationsService(
                session,
                timeline_append=event_ref_factory,
            ).create_check_in(
                engineer,
                plant_id=plant.plant_id,
                observation_state="observed",
                observation_text="Denied",
            )
        except PlantOperationError:
            pass
        else:
            raise AssertionError("archived-Plant check-in must fail")

    assert row_counts(ft004_database) == (0, 0)
    with ft004_database.session() as session:
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
    assert event_ref_factory.events == []


def test_unknown_plant_id_check_in_creates_no_candidate(
    ft004_database,
    event_ref_factory,
):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    with ft004_database.session() as session:
        try:
            PlantOperationsService(
                session,
                timeline_append=event_ref_factory,
            ).create_check_in(
                boss,
                plant_id=uuid.uuid4(),
                observation_state="observed",
                observation_text="Denied",
            )
        except PlantOperationError:
            pass
        else:
            raise AssertionError("unknown-Plant check-in must fail")

    assert row_counts(ft004_database) == (0, 0)
    with ft004_database.session() as session:
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
    assert event_ref_factory.events == []
