from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, select

from backend.app.access_admin.models import (
    Account,
    Base,
    Farm,
    FarmMembership,
    LocalSession,
    Plant,
)
from backend.app.access_admin.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
)
from backend.app.config import AppSettings
from backend.app.database import build_database
from backend.app.main import create_app
from backend.app.photo_intake import PhotoCatalogItem
import backend.app.api.photos as photos_module

TWO_HUNDRED_MIB = 209715200
EXPECTED_FIELDS = {
    "farm_id",
    "sync_status",
    "accepted_original_photo_bytes",
    "prompt_threshold_bytes",
    "prompt_eligible",
}


@dataclass(frozen=True)
class ActorSeed:
    account_id: uuid.UUID
    membership_id: uuid.UUID
    farm_id: uuid.UUID
    token: str


@dataclass(frozen=True)
class StatusSeed:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    boss: ActorSeed
    engineer: ActorSeed
    consultant: ActorSeed
    disabled: ActorSeed


@pytest.fixture
def storage_status_runtime(tmp_path: Path):
    settings = AppSettings(
        database_url="sqlite+pysqlite:///:memory:",
        local_artifact_root=tmp_path / "artifacts",
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
            yield client, database, seed
    finally:
        database.dispose()


def test_active_members_read_exact_farm_wide_status(storage_status_runtime):
    client, database, seed = storage_status_runtime
    _seed_catalog(
        database=database,
        actor=seed.boss,
        plant_id=seed.plant_id,
        total=1500,
    )
    for actor in (seed.boss, seed.engineer, seed.consultant):
        response = client.get(
            "/api/photos/storage-status",
            cookies=_cookies(actor),
            headers={"x-request-id": f"req-storage-{actor.account_id}"},
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "farm_id": str(seed.farm_id),
            "sync_status": "local_only",
            "accepted_original_photo_bytes": 1500,
            "prompt_threshold_bytes": TWO_HUNDRED_MIB,
            "prompt_eligible": False,
        }


def test_empty_farm_returns_zero_and_not_eligible(storage_status_runtime):
    client, database, seed = storage_status_runtime
    response = client.get(
        "/api/photos/storage-status",
        cookies=_cookies(seed.boss),
        headers={"x-request-id": "req-storage-empty"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["farm_id"] == str(seed.farm_id)
    assert body["accepted_original_photo_bytes"] == 0
    assert body["prompt_eligible"] is False


@pytest.mark.parametrize(
    ("total", "expected_eligible"),
    [
        (TWO_HUNDRED_MIB - 1, False),
        (TWO_HUNDRED_MIB, False),
        (TWO_HUNDRED_MIB + 1, True),
    ],
)
def test_threshold_matrix_via_protected_read(
    storage_status_runtime, total, expected_eligible
):
    client, database, seed = storage_status_runtime
    _seed_catalog(
        database=database,
        actor=seed.boss,
        plant_id=seed.plant_id,
        total=total,
    )
    response = client.get(
        "/api/photos/storage-status",
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-storage-matrix"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted_original_photo_bytes"] == total
    assert body["prompt_threshold_bytes"] == TWO_HUNDRED_MIB
    assert body["prompt_eligible"] is expected_eligible


def test_invalid_and_disabled_sessions_fail_through_existing_auth_codes(
    storage_status_runtime,
):
    client, database, seed = storage_status_runtime

    missing = client.get("/api/photos/storage-status")
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "AUTH_SESSION_REQUIRED"

    invalid = client.get(
        "/api/photos/storage-status",
        cookies={"agro_intellect_session": "not-a-real-token"},
    )
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "AUTH_SESSION_INVALID"

    disabled = client.get(
        "/api/photos/storage-status",
        cookies=_cookies(seed.disabled),
    )
    assert disabled.status_code == 403
    assert disabled.json()["error"]["code"] == "AUTH_MEMBERSHIP_DISABLED"


@pytest.mark.parametrize(
    "failure",
    [
        lambda: photos_module.PhotoIntakeError(
            photos_module.PhotoIntakeErrorCode.PHOTO_PERSISTENCE_FAILED
        ),
        lambda: RuntimeError("database unavailable"),
    ],
)
def test_aggregation_failure_returns_registered_error_without_partial_total(
    storage_status_runtime, monkeypatch, failure
):
    client, database, seed = storage_status_runtime

    def _fail(self, *, farm_id):
        raise failure()

    monkeypatch.setattr(
        photos_module.PhotoIntakeService,
        "farm_storage_pressure",
        _fail,
    )
    response = client.get(
        "/api/photos/storage-status",
        cookies=_cookies(seed.boss),
        headers={"x-request-id": "req-storage-failure"},
    )
    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"] == {
        "code": "PHOTO_STORAGE_STATUS_FAILED",
        "message": "Photo storage status could not be read.",
        "request_id": "req-storage-failure",
    }
    assert "accepted_original_photo_bytes" not in response.json()
    assert "prompt_eligible" not in response.json()


def test_status_read_is_read_only_and_unchanged_across_fresh_requests(
    storage_status_runtime,
):
    client, database, seed = storage_status_runtime
    _seed_catalog(
        database=database,
        actor=seed.boss,
        plant_id=seed.plant_id,
        total=3000,
    )
    before = _total_bytes(database)
    before_count = _count_rows(database)
    responses = [
        client.get(
            "/api/photos/storage-status",
            cookies=_cookies(actor),
            headers={"x-request-id": f"req-storage-fresh-{actor.account_id}"},
        )
        for actor in (seed.boss, seed.engineer, seed.consultant)
    ]
    assert [response.json()["accepted_original_photo_bytes"] for response in responses] == [
        3000,
        3000,
        3000,
    ]
    assert all(
        response.json()["sync_status"] == "local_only" for response in responses
    )
    assert _total_bytes(database) == before
    assert _count_rows(database) == before_count


def test_openapi_contains_exact_storage_status_contract(storage_status_runtime):
    client, database, seed = storage_status_runtime
    schema = client.app.openapi()

    paths = schema["paths"]
    assert "/api/photos/storage-status" in paths
    assert set(paths["/api/photos/storage-status"]) == {"get"}
    assert set(paths["/api/photos/storage-status"]["get"]["responses"]) >= {
        "200",
        "401",
        "403",
        "500",
    }

    schemas = schema["components"]["schemas"]
    assert set(schemas["PhotoStorageStatus"]["properties"]) == EXPECTED_FIELDS
    assert schemas["PhotoStorageStatus"]["properties"]["sync_status"] == {
        "const": "local_only",
        "title": "Sync Status",
        "type": "string",
    }

    for path in paths:
        assert "acknowledge" not in path.lower()
        assert "dismiss" not in path.lower()


def test_no_prompt_mutation_route_table_or_state(storage_status_runtime):
    client, database, seed = storage_status_runtime
    for route in client.app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", "")
        if path.startswith("/api/photos"):
            assert not (methods and methods & {"POST", "PATCH", "DELETE"}), path
        assert "acknowledge" not in path and "dismiss" not in path
    table_names = set(Base.metadata.tables)
    assert not {name for name in table_names if any(
        token in name for token in ("prompt", "acknowledg", "dismiss")
    )}
    response = client.get(
        "/api/photos/storage-status",
        cookies=_cookies(seed.boss),
    )
    assert set(response.json()) == EXPECTED_FIELDS


def _seed_catalog(*, database, actor, plant_id, total):
    chunk = 20 * 1024 * 1024
    sizes = []
    remaining = total
    while remaining > chunk:
        sizes.append(chunk)
        remaining -= chunk
    sizes.append(remaining)
    rows = _catalog_items(actor=actor, plant_id=plant_id, sizes=sizes)
    with database.session() as session:
        session.add_all(rows)
        session.commit()


def _catalog_items(*, actor, plant_id, sizes):
    base = datetime(2026, 7, 11, 8, 0, tzinfo=timezone.utc)
    rows = []
    for index, size in enumerate(sizes):
        photo_id = uuid.uuid4()
        uploaded_at = base + timedelta(minutes=index)
        rows.append(
            PhotoCatalogItem(
                photo_id=photo_id,
                farm_id=actor.farm_id,
                plant_id=plant_id,
                uploaded_by_account_id=actor.account_id,
                uploaded_by_membership_id=actor.membership_id,
                photo_type="whole_plant",
                captured_at=uploaded_at,
                uploaded_at=uploaded_at,
                content_type="image/jpeg",
                size_bytes=size,
                sha256="a" * 64,
                original_file_ref=(
                    f"plants/{plant_id}/photos/{photo_id}/original.jpg"
                ),
                manifest_ref=(
                    f"plants/{plant_id}/photos/{photo_id}/"
                    "manifest.initial_capture.json"
                ),
                source_refs={},
                event_refs={},
                local_only=True,
                can_train_on=False,
            )
        )
    return rows


def _total_bytes(database) -> int:
    from sqlalchemy import func

    with database.session() as session:
        return session.scalar(
            select(func.coalesce(func.sum(PhotoCatalogItem.size_bytes), 0))
        )


def _count_rows(database) -> int:
    from sqlalchemy import func

    with database.session() as session:
        return session.scalar(select(func.count(PhotoCatalogItem.photo_id)))


def _cookies(actor: ActorSeed) -> dict[str, str]:
    return {"agro_intellect_session": actor.token}


def _seed(database) -> StatusSeed:
    now = datetime.now(timezone.utc)
    farm = Farm(farm_key="local_farm", display_name="Storage Status Farm")
    with database.session() as session:
        session.add(farm)
        session.flush()
        plant = Plant(
            farm_id=farm.farm_id,
            plant_key="storage_plant_001",
            display_name="Storage Plant 001",
            status="active",
        )
        session.add(plant)
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
                login_name=f"ft015-{name}",
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
                farm.farm_id,
                token,
            )
            memberships[name] = membership
        session.commit()

    return StatusSeed(
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        boss=actors["boss"],
        engineer=actors["engineer"],
        consultant=actors["consultant"],
        disabled=actors["disabled"],
    )
