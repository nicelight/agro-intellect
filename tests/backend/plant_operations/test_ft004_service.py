from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest
from sqlalchemy import func, select

from backend.app.access_admin.models import FarmMembership
from backend.app.plant_operations import (
    DailyCheckIn,
    ManualMeasurement,
    ManualMeasurementInput,
    PlantOperationError,
    PlantOperationErrorCode,
    PlantOperationsService,
)
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    create_active_plant,
    disable_membership,
    grant_access,
    revoke_access,
    row_counts,
    seed_farm,
)


def test_ft004_bhv001_engineer_records_check_in_measurement_and_timeline_refs(
    ft004_database,
    event_ref_factory,
):
    farm = seed_farm(ft004_database)
    boss, _boss_membership = create_actor(ft004_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft004_database, farm, "engineer")
    plant = create_active_plant(ft004_database, boss, plant_key="tomato_001")
    grant = grant_access(
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

    assert result.check_in.observation_text == "Leaves are upright."
    assert result.measurements[0].ph == Decimal("6.50")
    assert result.measurements[0].ec_ms_cm == Decimal("1.250")
    assert result.freshness.ph_fresh_for_analysis is True
    assert result.freshness.ec_fresh_for_approval_input is True
    assert result.freshness.missing_or_stale == []
    assert [event.event_type for event in event_ref_factory.events] == [
        "daily_checkin_recorded",
        "manual_measurement_recorded",
    ]
    assert event_ref_factory.events[0].source_id == result.check_in.check_in_id
    assert event_ref_factory.events[1].source_id == result.measurements[0].measurement_id

    with ft004_database.session() as session:
        check_in = session.scalar(select(DailyCheckIn))
        measurement = session.scalar(select(ManualMeasurement))
        assert check_in.event_refs["daily_checkin_recorded"]["event_type"] == (
            "daily_checkin_recorded"
        )
        assert measurement.event_refs["manual_measurement_recorded"]["event_type"] == (
            "manual_measurement_recorded"
        )
        assert check_in.source_refs["account_id"] == str(engineer.account_id)
        assert check_in.source_refs["membership_id"] == str(
            engineer_membership.membership_id
        )
        assert check_in.source_refs["permission_source"] == "plant_access_grant"
        assert check_in.source_refs["grant_id"] == str(grant.grant_id)
        assert "synthetic-test-token" not in str(check_in.source_refs)


def test_ft004_bhv003_denied_paths_fail_before_persistence_and_timeline(
    ft004_database,
    event_ref_factory,
):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft004_database, farm, "engineer")
    consultant, consultant_membership = create_actor(
        ft004_database, farm, "consultant"
    )
    disabled_engineer, disabled_membership = create_actor(
        ft004_database, farm, "engineer"
    )

    consultant_plant = create_active_plant(
        ft004_database, boss, plant_key="consultant_001"
    )
    grant_access(
        ft004_database,
        boss,
        plant_id=consultant_plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )

    revoked_plant = create_active_plant(ft004_database, boss, plant_key="revoked_001")
    grant_access(
        ft004_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    revoke_access(
        ft004_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )

    archived_plant = create_active_plant(ft004_database, boss, plant_key="archived_001")
    grant_access(
        ft004_database,
        boss,
        plant_id=archived_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archive_plant(ft004_database, boss, plant_id=archived_plant.plant_id)

    disabled_plant = create_active_plant(ft004_database, boss, plant_key="disabled_001")
    grant_access(
        ft004_database,
        boss,
        plant_id=disabled_plant.plant_id,
        membership_id=disabled_membership.membership_id,
    )
    disable_membership(ft004_database, disabled_membership.membership_id)

    cases = [
        (consultant, consultant_plant.plant_id),
        (engineer, revoked_plant.plant_id),
        (engineer, archived_plant.plant_id),
        (disabled_engineer, disabled_plant.plant_id),
        (engineer, uuid.uuid4()),
    ]
    for actor, plant_id in cases:
        with ft004_database.session() as session:
            with pytest.raises(PlantOperationError) as denied:
                PlantOperationsService(
                    session,
                    timeline_append=event_ref_factory,
                ).create_check_in(
                    actor,
                    plant_id=plant_id,
                    observation_state="observed",
                    observation_text="Denied write",
                )
        assert denied.value.code is PlantOperationErrorCode.AUTH_PLANT_FORBIDDEN

    assert row_counts(ft004_database) == (0, 0)
    assert event_ref_factory.events == []


def test_timeline_append_failure_rolls_back_and_uses_safe_error(ft004_database):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft004_database, farm, "engineer")
    plant = create_active_plant(ft004_database, boss, plant_key="failure_001")
    grant_access(
        ft004_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )

    def failing_append(_event):
        raise RuntimeError("timeline secret=hidden")

    with ft004_database.session() as session:
        with pytest.raises(PlantOperationError) as failure:
            PlantOperationsService(
                session,
                timeline_append=failing_append,
            ).create_check_in(
                engineer,
                plant_id=plant.plant_id,
                observation_state="observed",
                observation_text="Rollback check",
                measurement=ManualMeasurementInput(ph="6.4"),
            )

    assert failure.value.code is PlantOperationErrorCode.TIMELINE_APPEND_FAILED
    assert "hidden" not in str(failure.value)
    assert row_counts(ft004_database) == (0, 0)


def test_ft004_bhv002_freshness_is_computed_from_measurement_rows_independently(
    ft004_database,
    event_ref_factory,
):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft004_database, farm, "engineer")
    plant = create_active_plant(ft004_database, boss, plant_key="freshness_001")
    grant_access(
        ft004_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    measured_at = datetime.now(timezone.utc) - timedelta(hours=3)

    with ft004_database.session() as session:
        PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).create_manual_measurement(
            engineer,
            plant_id=plant.plant_id,
            measurement=ManualMeasurementInput(ph="6.10", measured_at=measured_at),
        )
    with ft004_database.session() as session:
        projection = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).latest_measurements(
            engineer,
            plant_id=plant.plant_id,
            purpose="approval_input",
        )

    assert projection.latest_ph == Decimal("6.10")
    assert projection.latest_ec_ms_cm is None
    assert projection.ph_fresh_for_analysis is True
    assert projection.ph_fresh_for_approval_input is False
    assert projection.ec_fresh_for_analysis is False
    assert projection.ec_fresh_for_approval_input is False
    assert projection.missing_or_stale == ["ph", "ec"]

    with ft004_database.session() as session:
        assert session.scalar(select(func.count(ManualMeasurement.measurement_id))) == 1
        assert session.scalar(select(func.count(DailyCheckIn.check_in_id))) == 0


def test_excess_scale_values_are_canonical_across_postgresql_and_timeline(
    ft004_database,
    event_ref_factory,
):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft004_database, farm, "engineer")
    plant = create_active_plant(ft004_database, boss, plant_key="precision_001")
    grant_access(
        ft004_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )

    with ft004_database.session() as session:
        created = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).create_manual_measurement(
            engineer,
            plant_id=plant.plant_id,
            measurement=ManualMeasurementInput(ph="6.555", ec_ms_cm="1.2345"),
        )

    measurement_id = created.measurement.measurement_id
    assert created.measurement.ph == Decimal("6.56")
    assert created.measurement.ec_ms_cm == Decimal("1.235")
    assert created.freshness.latest_ph_ref == measurement_id
    assert created.freshness.latest_ec_ref == measurement_id
    assert created.freshness.latest_ph == Decimal("6.56")
    assert created.freshness.latest_ec_ms_cm == Decimal("1.235")
    event = event_ref_factory.events[0]
    assert event.source_id == measurement_id
    assert event.payload_summary["ph"] == Decimal("6.56")
    assert event.payload_summary["ec_ms_cm"] == Decimal("1.235")

    with ft004_database.session() as session:
        persisted = session.get(ManualMeasurement, measurement_id)
        assert persisted.ph == Decimal("6.56")
        assert persisted.ec_ms_cm == Decimal("1.235")

    with ft004_database.session() as session:
        later = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).latest_measurements(
            engineer,
            plant_id=plant.plant_id,
            purpose="analysis",
        )
    assert later.latest_ph_ref == measurement_id
    assert later.latest_ec_ref == measurement_id
    assert later.latest_ph == Decimal("6.56")
    assert later.latest_ec_ms_cm == Decimal("1.235")


def test_future_measurement_is_stale_for_both_freshness_purposes(
    ft004_database,
    event_ref_factory,
):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft004_database, farm, "engineer")
    plant = create_active_plant(ft004_database, boss, plant_key="future_001")
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
        ).create_manual_measurement(
            engineer,
            plant_id=plant.plant_id,
            measurement=ManualMeasurementInput(
                ph="6.40",
                measured_at=datetime.now(timezone.utc) + timedelta(days=365),
            ),
        )
    assert result.freshness.ph_fresh_for_analysis is False
    assert result.freshness.ph_fresh_for_approval_input is False
    assert result.freshness.missing_or_stale == ["ph", "ec"]

    with ft004_database.session() as session:
        approval = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).latest_measurements(
            engineer,
            plant_id=plant.plant_id,
            purpose="approval_input",
        )
    assert approval.ph_fresh_for_analysis is False
    assert approval.ph_fresh_for_approval_input is False
    assert approval.missing_or_stale == ["ph", "ec"]


def test_observation_text_without_state_is_rejected_without_writes(
    ft004_database,
    event_ref_factory,
):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft004_database, farm, "engineer")
    plant = create_active_plant(ft004_database, boss, plant_key="observation_001")
    grant_access(
        ft004_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )

    with ft004_database.session() as session:
        with pytest.raises(PlantOperationError) as rejected:
            PlantOperationsService(
                session,
                timeline_append=event_ref_factory,
            ).create_check_in(
                engineer,
                plant_id=plant.plant_id,
                observation_state=None,
                observation_text="Leaves are yellow",
                measurement=ManualMeasurementInput(ph="6.40"),
            )

    assert rejected.value.code is PlantOperationErrorCode.VALIDATION_FAILED
    assert row_counts(ft004_database) == (0, 0)
    assert event_ref_factory.events == []


def test_validation_errors_do_not_persist(ft004_database, event_ref_factory):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft004_database, farm, "engineer")
    plant = create_active_plant(ft004_database, boss, plant_key="validation_001")
    grant_access(
        ft004_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )

    cases = [
        {
            "observation_state": "observed",
            "observation_text": " ",
            "measurement": None,
            "code": PlantOperationErrorCode.OBSERVATION_TEXT_REQUIRED,
        },
        {
            "observation_state": "no_observation_provided",
            "observation_text": "unexpected",
            "measurement": None,
            "code": PlantOperationErrorCode.OBSERVATION_TEXT_FORBIDDEN,
        },
        {
            "observation_state": None,
            "observation_text": None,
            "measurement": None,
            "code": PlantOperationErrorCode.CHECK_IN_EMPTY,
        },
        {
            "observation_state": "observed",
            "observation_text": "Bad pH",
            "measurement": ManualMeasurementInput(ph="14.5"),
            "code": PlantOperationErrorCode.PH_INVALID,
        },
        {
            "observation_state": "observed",
            "observation_text": "Bad EC",
            "measurement": ManualMeasurementInput(ec_ms_cm="-0.1"),
            "code": PlantOperationErrorCode.EC_INVALID,
        },
    ]
    for case in cases:
        with ft004_database.session() as session:
            with pytest.raises(PlantOperationError) as error:
                PlantOperationsService(
                    session,
                    timeline_append=event_ref_factory,
                ).create_check_in(
                    engineer,
                    plant_id=plant.plant_id,
                    observation_state=case["observation_state"],
                    observation_text=case["observation_text"],
                    measurement=case["measurement"],
                )
        assert error.value.code is case["code"]

    assert row_counts(ft004_database) == (0, 0)
    assert event_ref_factory.events == []
