from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, func, select

from backend.app.access_admin.models import (
    Account,
    Base,
    Farm,
    FarmMembership,
    LocalSession,
    Plant,
    PlantAccessGrant,
)
from backend.app.access_admin.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
)
from backend.app.config import AppSettings
from backend.app.database import build_database
from backend.app.main import create_app
from backend.app.plant_operations import (
    DailyCheckIn,
    ManualMeasurement,
    PlantOperationError,
    PlantOperationErrorCode,
)


@dataclass(frozen=True)
class ActorSeed:
    account_id: uuid.UUID
    membership_id: uuid.UUID
    token: str


@dataclass(frozen=True)
class OperationsApiSeed:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    wrong_farm_plant_id: uuid.UUID
    revoked_plant_id: uuid.UUID
    archived_plant_id: uuid.UUID
    boss: ActorSeed
    engineer: ActorSeed
    consultant: ActorSeed
    disabled: ActorSeed


@pytest.fixture
def operations_api_runtime(tmp_path: Path):
    settings = AppSettings(
        database_url="sqlite+pysqlite:///:memory:",
        local_timeline_root=tmp_path / "timeline",
    )
    database = build_database(settings)
    engine = database.engine()
    event.listen(
        engine,
        "connect",
        lambda connection, _record: connection.create_function(
            "btrim",
            1,
            lambda value: value.strip() if isinstance(value, str) else value,
        ),
    )
    Base.metadata.create_all(engine)
    seed = _seed(database)
    app = create_app(settings=settings, database=database)
    try:
        with TestClient(app, base_url="http://127.0.0.1") as client:
            yield client, database, seed, settings.local_timeline_root
    finally:
        database.dispose()


def test_ft004_bhv001_engineer_check_in_persists_projection_and_timeline_refs(
    operations_api_runtime,
):
    client, database, seed, timeline_root = operations_api_runtime

    prompt = client.get(
        f"/api/plants/{seed.plant_id}/operations/check-in-prompt",
        cookies=_cookies(seed.engineer),
    )
    assert prompt.status_code == 200
    assert prompt.headers["cache-control"] == "no-store"
    assert prompt.json()["photo_upload_available"] is False

    response = client.post(
        f"/api/plants/{seed.plant_id}/operations/check-ins",
        json={
            "observation_state": "observed",
            "observation_text": "  Leaves are upright.  ",
            "measurement": {
                "ph": "6.50",
                "ec_ms_cm": "1.250",
                "provenance_note": "manual meter",
            },
        },
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft004-bhv001"},
    )
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["observation_state"] == "observed"
    assert body["observation_text"] == "Leaves are upright."
    assert body["photo_upload_available"] is False
    assert len(body["measurement_refs"]) == 1
    assert body["event_refs"]["daily_checkin_recorded"]["event_type"] == (
        "daily_checkin_recorded"
    )
    assert _as_decimal(body["freshness"]["latest_ph"]) == Decimal("6.50")
    assert _as_decimal(body["freshness"]["latest_ec_ms_cm"]) == Decimal("1.250")
    assert body["freshness"]["missing_or_stale"] == []

    timeline_path = timeline_root / "timeline.jsonl"
    timeline_events = [
        json.loads(line)
        for line in timeline_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [event["event_type"] for event in timeline_events] == [
        "daily_checkin_recorded",
        "manual_measurement_recorded",
    ]
    assert "synthetic-test-token" not in timeline_path.read_text(encoding="utf-8")

    timeline_path.unlink()
    latest = client.get(
        f"/api/plants/{seed.plant_id}/operations/measurements/latest",
        cookies=_cookies(seed.engineer),
    )
    assert latest.status_code == 200
    assert latest.headers["cache-control"] == "no-store"
    latest_body = latest.json()
    assert latest_body["latest_ph_ref"] == body["measurement_refs"][0]
    assert latest_body["latest_ec_ref"] == body["measurement_refs"][0]
    assert _as_decimal(latest_body["latest_ph"]) == Decimal("6.50")
    assert _as_decimal(latest_body["latest_ec_ms_cm"]) == Decimal("1.250")

    with database.session() as session:
        check_in = session.scalar(select(DailyCheckIn))
        measurement = session.scalar(select(ManualMeasurement))
        assert check_in.source_refs["account_id"] == str(seed.engineer.account_id)
        assert check_in.source_refs["membership_id"] == str(
            seed.engineer.membership_id
        )
        assert measurement.event_refs["manual_measurement_recorded"]["event_type"] == (
            "manual_measurement_recorded"
        )
        assert session.scalar(select(func.count(DailyCheckIn.check_in_id))) == 1
        assert session.scalar(select(func.count(ManualMeasurement.measurement_id))) == 1


def test_ft004_bhv002_boss_manual_measurement_and_stale_projection(
    operations_api_runtime,
):
    client, _database, seed, _timeline_root = operations_api_runtime
    measured_at = datetime.now(timezone.utc) - timedelta(hours=3)

    measurement = client.post(
        f"/api/plants/{seed.plant_id}/operations/measurements",
        json={"ph": "6.10", "measured_at": measured_at.isoformat()},
        cookies=_cookies(seed.boss),
        headers={"x-request-id": "req-ft004-boss-measurement"},
    )
    assert measurement.status_code == 201
    assert measurement.headers["cache-control"] == "no-store"
    body = measurement.json()
    assert body["check_in_id"] is None
    assert body["trust_status"] == "confirmed"
    assert body["event_refs"]["manual_measurement_recorded"]["event_type"] == (
        "manual_measurement_recorded"
    )

    latest = client.get(
        f"/api/plants/{seed.plant_id}/operations/measurements/latest"
        "?purpose=approval_input",
        cookies=_cookies(seed.boss),
    )
    assert latest.status_code == 200
    projection = latest.json()
    assert _as_decimal(projection["latest_ph"]) == Decimal("6.10")
    assert projection["latest_ec_ms_cm"] is None
    assert projection["ph_fresh_for_analysis"] is True
    assert projection["ph_fresh_for_approval_input"] is False
    assert projection["ec_fresh_for_analysis"] is False
    assert projection["ec_fresh_for_approval_input"] is False
    assert projection["missing_or_stale"] == ["ph", "ec"]
    assert "safety" not in latest.text.lower()
    assert "task" not in latest.text.lower()


def test_measurement_values_are_normalized_before_http_and_timeline_surfaces(
    operations_api_runtime,
):
    client, database, seed, timeline_root = operations_api_runtime

    created = client.post(
        f"/api/plants/{seed.plant_id}/operations/measurements",
        json={"ph": 6.555, "ec_ms_cm": 1.2345},
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft004-canonical-values"},
    )
    assert created.status_code == 201
    body = created.json()
    assert _as_decimal(body["ph"]) == Decimal("6.56")
    assert _as_decimal(body["ec_ms_cm"]) == Decimal("1.235")

    event_body = json.loads(
        (timeline_root / "timeline.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert _as_decimal(event_body["payload_summary"]["ph"]) == Decimal("6.56")
    assert _as_decimal(event_body["payload_summary"]["ec_ms_cm"]) == Decimal(
        "1.235"
    )

    with database.session() as session:
        persisted = session.scalar(select(ManualMeasurement))
        assert persisted.ph == Decimal("6.56")
        assert persisted.ec_ms_cm == Decimal("1.235")

    latest = client.get(
        f"/api/plants/{seed.plant_id}/operations/measurements/latest",
        cookies=_cookies(seed.engineer),
    )
    assert latest.status_code == 200
    projection = latest.json()
    assert projection["latest_ph_ref"] == body["measurement_id"]
    assert projection["latest_ec_ref"] == body["measurement_id"]
    assert _as_decimal(projection["latest_ph"]) == Decimal("6.56")
    assert _as_decimal(projection["latest_ec_ms_cm"]) == Decimal("1.235")


def test_future_measurement_is_stale_in_http_projection_for_both_purposes(
    operations_api_runtime,
):
    client, _database, seed, _timeline_root = operations_api_runtime
    future = datetime.now(timezone.utc) + timedelta(days=365)

    created = client.post(
        f"/api/plants/{seed.plant_id}/operations/measurements",
        json={"ph": 6.4, "measured_at": future.isoformat()},
        cookies=_cookies(seed.engineer),
    )
    assert created.status_code == 201

    for purpose in ("analysis", "approval_input"):
        latest = client.get(
            f"/api/plants/{seed.plant_id}/operations/measurements/latest"
            f"?purpose={purpose}",
            cookies=_cookies(seed.engineer),
        )
        assert latest.status_code == 200
        projection = latest.json()
        assert projection["ph_fresh_for_analysis"] is False
        assert projection["ph_fresh_for_approval_input"] is False
        assert projection["missing_or_stale"] == ["ph", "ec"]


def test_observation_text_without_state_returns_422_and_writes_nothing(
    operations_api_runtime,
):
    client, database, seed, timeline_root = operations_api_runtime

    response = client.post(
        f"/api/plants/{seed.plant_id}/operations/check-ins",
        json={
            "observation_text": "Leaves are yellow",
            "measurement": {"ph": 6.4},
        },
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft004-observation-state"},
    )

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "VALIDATION_FAILED",
        "message": "Request validation failed.",
        "request_id": "req-ft004-observation-state",
    }
    assert _row_counts(database) == (0, 0)
    assert not (timeline_root / "timeline.jsonl").exists()


@pytest.mark.parametrize(
    ("actor_name", "plant_attr", "expected_status", "expected_code"),
    [
        ("consultant", "plant_id", 404, "AUTH_PLANT_FORBIDDEN"),
        ("engineer", "revoked_plant_id", 404, "AUTH_PLANT_FORBIDDEN"),
        ("disabled", "plant_id", 403, "AUTH_MEMBERSHIP_DISABLED"),
        ("engineer", "wrong_farm_plant_id", 404, "AUTH_PLANT_FORBIDDEN"),
        ("engineer", "archived_plant_id", 404, "AUTH_PLANT_FORBIDDEN"),
    ],
)
def test_ft004_bhv003_denials_are_no_leak_and_write_nothing(
    operations_api_runtime,
    actor_name,
    plant_attr,
    expected_status,
    expected_code,
):
    client, database, seed, timeline_root = operations_api_runtime
    actor = getattr(seed, actor_name)
    plant_id = getattr(seed, plant_attr)

    response = client.post(
        f"/api/plants/{plant_id}/operations/check-ins",
        json={
            "observation_state": "observed",
            "observation_text": "Denied write",
            "measurement": {"ph": "6.4"},
        },
        cookies=_cookies(actor),
        headers={"x-request-id": f"req-ft004-denied-{actor_name}"},
    )
    assert response.status_code == expected_status
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"]["code"] == expected_code
    if expected_code == "AUTH_PLANT_FORBIDDEN":
        assert str(plant_id) not in response.text

    assert _row_counts(database) == (0, 0)
    assert not (timeline_root / "timeline.jsonl").exists()


def test_unknown_plant_and_invalid_payloads_use_stable_errors(
    operations_api_runtime,
):
    client, database, seed, _timeline_root = operations_api_runtime

    unknown = client.post(
        f"/api/plants/{uuid.uuid4()}/operations/check-ins",
        json={"observation_state": "observed", "observation_text": "Unknown"},
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft004-unknown"},
    )
    assert unknown.status_code == 404
    assert unknown.json()["error"] == {
        "code": "AUTH_PLANT_FORBIDDEN",
        "message": "Plant is not available.",
        "request_id": "req-ft004-unknown",
    }

    extra = client.post(
        f"/api/plants/{seed.plant_id}/operations/check-ins",
        json={
            "observation_state": "observed",
            "observation_text": "Extra field",
            "unexpected": True,
        },
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft004-extra"},
    )
    assert extra.status_code == 422
    assert extra.json()["error"]["code"] == "VALIDATION_FAILED"

    invalid_ph = client.post(
        f"/api/plants/{seed.plant_id}/operations/measurements",
        json={"ph": True},
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft004-bad-ph"},
    )
    assert invalid_ph.status_code == 422
    assert invalid_ph.json()["error"] == {
        "code": "PH_INVALID",
        "message": "pH value is invalid.",
        "request_id": "req-ft004-bad-ph",
    }
    assert _row_counts(database) == (0, 0)


def test_denied_actor_context_stops_before_operations_service(
    operations_api_runtime,
    monkeypatch,
):
    client, _database, seed, _timeline_root = operations_api_runtime

    class ExplodingService:
        def __init__(self, *_args, **_kwargs) -> None:
            raise AssertionError("service must not run for denied Consultant")

    monkeypatch.setattr(
        "backend.app.api.operations.PlantOperationsService",
        ExplodingService,
    )
    response = client.post(
        f"/api/plants/{seed.plant_id}/operations/check-ins",
        json={"observation_state": "observed", "observation_text": "Denied"},
        cookies=_cookies(seed.consultant),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "AUTH_PLANT_FORBIDDEN"


def test_operation_failures_are_safe_and_do_not_claim_success(
    operations_api_runtime,
    monkeypatch,
):
    client, database, seed, _timeline_root = operations_api_runtime

    class TimelineFailingService:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def create_check_in(self, *_args, **_kwargs):
            raise PlantOperationError(PlantOperationErrorCode.TIMELINE_APPEND_FAILED)

    monkeypatch.setattr(
        "backend.app.api.operations.PlantOperationsService",
        TimelineFailingService,
    )
    timeline_failed = client.post(
        f"/api/plants/{seed.plant_id}/operations/check-ins",
        json={"observation_state": "observed", "observation_text": "Timeline"},
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft004-timeline-failed"},
    )
    assert timeline_failed.status_code == 500
    assert timeline_failed.json()["error"] == {
        "code": "TIMELINE_APPEND_FAILED",
        "message": "Plant operation audit trail could not be recorded.",
        "request_id": "req-ft004-timeline-failed",
    }

    class RawFailingService:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def create_manual_measurement(self, *_args, **_kwargs):
            raise RuntimeError("postgresql://admin:secret@localhost/raw sql")

    monkeypatch.setattr(
        "backend.app.api.operations.PlantOperationsService",
        RawFailingService,
    )
    persistence_failed = client.post(
        f"/api/plants/{seed.plant_id}/operations/measurements",
        json={"ec_ms_cm": "1.2"},
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft004-persistence-failed"},
    )
    assert persistence_failed.status_code == 500
    assert persistence_failed.json()["error"] == {
        "code": "OPERATION_PERSISTENCE_FAILED",
        "message": "Plant operation could not be completed.",
        "request_id": "req-ft004-persistence-failed",
    }
    assert "secret" not in persistence_failed.text
    assert "raw sql" not in persistence_failed.text
    assert _row_counts(database) == (0, 0)


def test_generated_openapi_contains_ft004_operations_contracts():
    database = build_database(AppSettings(database_url="sqlite+pysqlite:///:memory:"))
    try:
        schema = create_app(database=database).openapi()
    finally:
        database.dispose()

    paths = schema["paths"]
    expected = {
        "/api/plants/{plant_id}/operations/check-in-prompt": {"get"},
        "/api/plants/{plant_id}/operations/check-ins": {"post"},
        "/api/plants/{plant_id}/operations/measurements": {"post"},
        "/api/plants/{plant_id}/operations/measurements/latest": {"get"},
    }
    for path, methods in expected.items():
        assert path in paths
        assert methods <= paths[path].keys()

    assert set(
        paths["/api/plants/{plant_id}/operations/check-ins"]["post"]["responses"]
    ) >= {"201", "401", "403", "404", "422", "500"}
    assert set(
        paths["/api/plants/{plant_id}/operations/measurements/latest"]["get"][
            "responses"
        ]
    ) >= {"200", "401", "403", "404", "422", "500"}

    schemas = schema["components"]["schemas"]
    assert schemas["CheckInCreateRequest"]["additionalProperties"] is False
    assert schemas["ManualMeasurementPayload"]["additionalProperties"] is False
    assert schemas["ManualMeasurementCreateRequest"]["additionalProperties"] is False
    assert set(schemas["FreshnessProjectionResponse"]["properties"]) == {
        "latest_ph_ref",
        "latest_ec_ref",
        "latest_ph",
        "latest_ec_ms_cm",
        "ph_fresh_for_analysis",
        "ec_fresh_for_analysis",
        "ph_fresh_for_approval_input",
        "ec_fresh_for_approval_input",
        "missing_or_stale",
        "computed_at",
    }
    assert "event_refs" in schemas["CheckInSummary"]["properties"]
    assert "photo_upload_available" in schemas["CheckInSummary"]["properties"]


def _cookies(actor: ActorSeed) -> dict[str, str]:
    return {"agro_intellect_session": actor.token}


def _seed(database) -> OperationsApiSeed:
    now = datetime.now(timezone.utc)
    farm = Farm(farm_key="local_farm", display_name="Local Farm")
    with database.session() as session:
        session.add(farm)
        session.flush()

        plant = Plant(
            farm_id=farm.farm_id,
            plant_key="tomato_001",
            display_name="Tomato 001",
            status="active",
        )
        revoked_plant = Plant(
            farm_id=farm.farm_id,
            plant_key="revoked_001",
            display_name="Revoked 001",
            status="active",
        )
        archived_plant = Plant(
            farm_id=farm.farm_id,
            plant_key="archived_001",
            display_name="Archived 001",
            status="archived",
        )
        wrong_farm_plant = Plant(
            farm_id=uuid.uuid4(),
            plant_key="wrong_farm_001",
            display_name="Wrong Farm 001",
            status="active",
        )
        session.add_all([plant, revoked_plant, archived_plant, wrong_farm_plant])
        session.flush()

        actors = {}
        memberships = {}
        for name, role, status in (
            ("boss", "boss", "active"),
            ("engineer", "engineer", "active"),
            ("consultant", "consultant", "active"),
            ("disabled", "engineer", "disabled"),
        ):
            account = Account(
                login_name=f"ft004-{name}",
                display_name=name.title(),
                account_status="active",
                password_hash=hash_password("test-only-password"),
            )
            session.add(account)
            session.flush()
            membership = FarmMembership(
                account_id=account.account_id,
                farm_id=farm.farm_id,
                role_preset=role,
                membership_status=status,
                disabled_at=now if status == "disabled" else None,
            )
            session.add(membership)
            session.flush()
            token = generate_session_token()
            session.add(
                LocalSession(
                    account_id=account.account_id,
                    token_hash=hash_session_token(token),
                    created_at=now,
                    expires_at=now + timedelta(days=1),
                    auth_method="local_password",
                )
            )
            actors[name] = ActorSeed(
                account.account_id,
                membership.membership_id,
                token,
            )
            memberships[name] = membership

        for name in ("engineer", "consultant", "disabled"):
            session.add(
                PlantAccessGrant(
                    membership_id=memberships[name].membership_id,
                    plant_id=plant.plant_id,
                    status="active",
                    plant_approve_actions=False,
                )
            )
        session.add(
            PlantAccessGrant(
                membership_id=memberships["engineer"].membership_id,
                plant_id=revoked_plant.plant_id,
                status="revoked",
                plant_approve_actions=False,
            )
        )
        session.add(
            PlantAccessGrant(
                membership_id=memberships["engineer"].membership_id,
                plant_id=archived_plant.plant_id,
                status="active",
                plant_approve_actions=False,
            )
        )
        session.commit()

    return OperationsApiSeed(
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        wrong_farm_plant_id=wrong_farm_plant.plant_id,
        revoked_plant_id=revoked_plant.plant_id,
        archived_plant_id=archived_plant.plant_id,
        boss=actors["boss"],
        engineer=actors["engineer"],
        consultant=actors["consultant"],
        disabled=actors["disabled"],
    )


def _row_counts(database) -> tuple[int, int]:
    with database.session() as session:
        return (
            session.scalar(select(func.count(DailyCheckIn.check_in_id))),
            session.scalar(select(func.count(ManualMeasurement.measurement_id))),
        )


def _as_decimal(value: object) -> Decimal:
    return Decimal(str(value))
