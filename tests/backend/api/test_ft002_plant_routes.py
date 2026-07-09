from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, select

from backend.app.access_admin.models import (
    Account,
    AdminAuditRecord,
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
from backend.app.access_admin.farm_service import (
    FarmCommandError,
    FarmCommandErrorCode,
)
from backend.app.config import AppSettings
from backend.app.database import build_database
from backend.app.main import create_app


@dataclass(frozen=True)
class ActorSeed:
    membership_id: uuid.UUID
    token: str


@dataclass(frozen=True)
class ApiSeed:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    boss: ActorSeed
    engineer: ActorSeed
    consultant: ActorSeed
    disabled: ActorSeed


@pytest.fixture
def api_runtime():
    settings = AppSettings(database_url="sqlite+pysqlite:///:memory:")
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


def test_boss_farm_plant_lifecycle_and_no_store(api_runtime):
    client, database, seed = api_runtime
    farm = client.get("/api/farm", cookies=_cookies(seed.boss))
    assert farm.status_code == 200
    assert farm.headers["cache-control"] == "no-store"
    assert farm.json()["farm_key"] == "local_farm"

    renamed = client.patch(
        "/api/farm",
        json={"display_name": "  Main Farm  "},
        cookies=_cookies(seed.boss),
    )
    assert renamed.status_code == 200
    assert renamed.json()["display_name"] == "Main Farm"

    created = client.post(
        "/api/plants",
        json={"plant_key": "cucumber_001", "display_name": "Cucumber"},
        cookies=_cookies(seed.boss),
    )
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["permissions"]["source"] == "boss_role"
    assert created_body["permissions"]["grant_id"] is None
    plant_id = created_body["plant_id"]

    archived = client.post(
        f"/api/plants/{plant_id}/archive",
        cookies=_cookies(seed.boss),
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert archived.json()["permissions"]["can_read"] is False
    assert archived.json()["permissions"]["can_manage_access"] is True
    archived_retry = client.post(
        f"/api/plants/{plant_id}/archive",
        cookies=_cookies(seed.boss),
    )
    assert archived_retry.status_code == 200
    assert archived_retry.json()["status"] == "archived"

    denied = client.get(
        f"/api/plants/{plant_id}",
        cookies=_cookies(seed.boss),
        headers={"x-request-id": "req-archived"},
    )
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "AUTH_PLANT_FORBIDDEN"
    assert plant_id not in denied.text

    restored = client.post(
        f"/api/plants/{plant_id}/restore",
        cookies=_cookies(seed.boss),
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"
    restored_retry = client.post(
        f"/api/plants/{plant_id}/restore",
        cookies=_cookies(seed.boss),
    )
    assert restored_retry.status_code == 200
    assert restored_retry.json()["status"] == "active"

    with database.session() as session:
        actions = list(
            session.scalars(
                select(AdminAuditRecord.action_type).where(
                    AdminAuditRecord.target_id == uuid.UUID(plant_id)
                )
            )
        )
    assert actions == ["plant_created", "plant_archived", "plant_restored"]


def test_engineer_create_get_rename_but_cannot_manage(api_runtime):
    client, _database, seed = api_runtime
    created = client.post(
        "/api/plants",
        json={"plant_key": "lettuce_001", "display_name": " Lettuce "},
        cookies=_cookies(seed.engineer),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["display_name"] == "Lettuce"
    assert body["permissions"] == {
        "can_read": True,
        "can_comment": True,
        "can_operate": True,
        "can_create_domain_tasks": True,
        "can_manage_access": False,
        "can_approve_actions": False,
        "source": "plant_access_grant",
        "grant_id": body["permissions"]["grant_id"],
    }
    assert body["permissions"]["grant_id"] is not None

    plant_id = body["plant_id"]
    renamed = client.patch(
        f"/api/plants/{plant_id}",
        json={"display_name": "Green Lettuce"},
        cookies=_cookies(seed.engineer),
    )
    assert renamed.status_code == 200
    assert renamed.json()["display_name"] == "Green Lettuce"

    archive = client.post(
        f"/api/plants/{plant_id}/archive",
        cookies=_cookies(seed.engineer),
    )
    access = client.get(
        f"/api/plants/{plant_id}/access",
        cookies=_cookies(seed.engineer),
    )
    assert (archive.status_code, access.status_code) == (404, 404)
    assert archive.json()["error"]["code"] == "AUTH_PLANT_FORBIDDEN"


def test_list_filters_by_persisted_grants_and_archived_status(api_runtime):
    client, database, seed = api_runtime
    boss_items = client.get("/api/plants", cookies=_cookies(seed.boss)).json()["items"]
    engineer_items = client.get(
        "/api/plants", cookies=_cookies(seed.engineer)
    ).json()["items"]
    consultant_items = client.get(
        "/api/plants", cookies=_cookies(seed.consultant)
    ).json()["items"]
    assert [item["plant_key"] for item in boss_items] == ["tomato_001"]
    assert [item["plant_key"] for item in engineer_items] == ["tomato_001"]
    assert [item["plant_key"] for item in consultant_items] == ["tomato_001"]
    assert consultant_items[0]["permissions"]["can_operate"] is False

    with database.session() as session:
        grant = session.scalar(
            select(PlantAccessGrant).where(
                PlantAccessGrant.membership_id == seed.engineer.membership_id
            )
        )
        grant.status = "revoked"
        session.commit()
    assert client.get(
        "/api/plants", cookies=_cookies(seed.engineer)
    ).json() == {"items": []}
    revoked_detail = client.get(
        f"/api/plants/{seed.plant_id}",
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-revoked"},
    )
    assert revoked_detail.status_code == 404
    assert revoked_detail.json()["error"] == {
        "code": "AUTH_PLANT_FORBIDDEN",
        "message": "Plant is not available.",
        "request_id": "req-revoked",
    }
    assert str(seed.plant_id) not in revoked_detail.text

    with database.session() as session:
        plant = session.get(Plant, seed.plant_id)
        plant.status = "archived"
        session.commit()
    assert client.get("/api/plants", cookies=_cookies(seed.boss)).json() == {
        "items": []
    }


def test_boss_grant_admin_while_archived_preserves_identity(api_runtime):
    client, database, seed = api_runtime
    archived = client.post(
        f"/api/plants/{seed.plant_id}/archive",
        cookies=_cookies(seed.boss),
    )
    assert archived.status_code == 200

    with database.session() as session:
        original = session.scalar(
            select(PlantAccessGrant).where(
                PlantAccessGrant.membership_id == seed.engineer.membership_id
            )
        )
        original_id = original.grant_id

    revoked = client.post(
        f"/api/plants/{seed.plant_id}/access/{seed.engineer.membership_id}/revoke",
        cookies=_cookies(seed.boss),
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    regranted = client.put(
        f"/api/plants/{seed.plant_id}/access/{seed.engineer.membership_id}",
        json={"plant_approve_actions": True},
        cookies=_cookies(seed.boss),
    )
    assert regranted.status_code == 200
    assert regranted.json()["grant_id"] == str(original_id)
    assert regranted.json()["plant_approve_actions"] is True

    denied = client.get(
        f"/api/plants/{seed.plant_id}",
        cookies=_cookies(seed.engineer),
    )
    assert denied.status_code == 404
    restored = client.post(
        f"/api/plants/{seed.plant_id}/restore",
        cookies=_cookies(seed.boss),
    )
    assert restored.status_code == 200
    engineer = client.get(
        f"/api/plants/{seed.plant_id}",
        cookies=_cookies(seed.engineer),
    )
    assert engineer.status_code == 200
    assert engineer.json()["permissions"]["can_approve_actions"] is True


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"plant_key": "Bad-Key", "display_name": "Bad"}, "PLANT_KEY_INVALID"),
        (
            {"plant_key": "tomato_001", "display_name": "Duplicate"},
            "PLANT_KEY_CONFLICT",
        ),
        (
            {"plant_key": "valid_001", "display_name": " ", "extra": True},
            "VALIDATION_FAILED",
        ),
    ],
)
def test_create_uses_stable_validation_and_conflict_errors(api_runtime, payload, code):
    client, _database, seed = api_runtime
    response = client.post("/api/plants", json=payload, cookies=_cookies(seed.boss))
    assert response.status_code in {409, 422}
    assert response.json()["error"]["code"] == code
    assert response.headers["cache-control"] == "no-store"


def test_grant_target_rules_and_disabled_actor_fail_before_mutation(api_runtime):
    client, database, seed = api_runtime
    consultant_approval = client.put(
        f"/api/plants/{seed.plant_id}/access/{seed.consultant.membership_id}",
        json={"plant_approve_actions": True},
        cookies=_cookies(seed.boss),
    )
    assert consultant_approval.status_code == 422
    assert (
        consultant_approval.json()["error"]["code"]
        == "PLANT_GRANT_APPROVAL_FORBIDDEN"
    )

    disabled = client.post(
        "/api/plants",
        json={"plant_key": "denied_001", "display_name": "Denied"},
        cookies=_cookies(seed.disabled),
    )
    assert disabled.status_code == 403
    assert disabled.json()["error"]["code"] == "AUTH_MEMBERSHIP_DISABLED"
    with database.session() as session:
        assert session.scalar(
            select(Plant).where(Plant.plant_key == "denied_001")
        ) is None


def test_snapshot_failure_is_redacted_and_fails_closed(api_runtime):
    client, _database, seed = api_runtime

    def broken_provider(**_kwargs):
        raise RuntimeError("postgresql://admin:secret-password@localhost/private")

    client.app.state.plant_access_snapshot_provider = broken_provider
    response = client.get(
        f"/api/plants/{seed.plant_id}",
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-provider-failed"},
    )
    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "AUTH_PLANT_FORBIDDEN",
        "message": "Plant is not available.",
        "request_id": "req-provider-failed",
    }
    assert "secret-password" not in response.text


def test_generic_create_persistence_failure_is_not_key_conflict(
    api_runtime,
    monkeypatch,
):
    client, database, seed = api_runtime

    class FailingFarmService:
        def __init__(self, _session) -> None:
            pass

        def create_plant(self, *_args, **_kwargs):
            raise FarmCommandError(FarmCommandErrorCode.PERSISTENCE_FAILED)

    monkeypatch.setattr(
        "backend.app.api.plants.FarmService",
        FailingFarmService,
    )
    response = client.post(
        "/api/plants",
        json={"plant_key": "failure_001", "display_name": "Failure"},
        cookies=_cookies(seed.boss),
        headers={"x-request-id": "req-persistence-failed"},
    )
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "PLANT_PERSISTENCE_FAILED",
            "message": "Plant request could not be completed.",
            "request_id": "req-persistence-failed",
        }
    }
    assert response.headers["cache-control"] == "no-store"
    assert "PLANT_KEY_CONFLICT" not in response.text
    with database.session() as session:
        assert session.scalar(
            select(Plant).where(Plant.plant_key == "failure_001")
        ) is None


def test_farm_persistence_failure_uses_farm_specific_error(
    api_runtime,
    monkeypatch,
):
    client, database, seed = api_runtime

    class FailingFarmService:
        def __init__(self, _session) -> None:
            pass

        def change_farm_display_name(self, *_args, **_kwargs):
            raise FarmCommandError(FarmCommandErrorCode.PERSISTENCE_FAILED)

    monkeypatch.setattr(
        "backend.app.api.plants.FarmService",
        FailingFarmService,
    )
    response = client.patch(
        "/api/farm",
        json={"display_name": "Failed Rename"},
        cookies=_cookies(seed.boss),
        headers={"x-request-id": "req-farm-persistence-failed"},
    )
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "FARM_PERSISTENCE_FAILED",
            "message": "Farm request could not be completed.",
            "request_id": "req-farm-persistence-failed",
        }
    }
    assert response.headers["cache-control"] == "no-store"
    assert "PLANT_PERSISTENCE_FAILED" not in response.text
    with database.session() as session:
        farm = session.get(Farm, seed.farm_id)
        assert farm.display_name == "Local Farm"


def _cookies(actor: ActorSeed) -> dict[str, str]:
    return {"agro_intellect_session": actor.token}


def _seed(database) -> ApiSeed:
    now = datetime.now(timezone.utc)
    farm = Farm(farm_key="local_farm", display_name="Local Farm")
    plant = Plant(
        farm_id=farm.farm_id,
        plant_key="tomato_001",
        display_name="Tomato 001",
        status="active",
    )
    with database.session() as session:
        session.add(farm)
        session.flush()
        plant.farm_id = farm.farm_id
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
                login_name=name,
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
            actors[name] = ActorSeed(membership.membership_id, token)
            memberships[name] = membership
        for name in ("engineer", "consultant"):
            session.add(
                PlantAccessGrant(
                    membership_id=memberships[name].membership_id,
                    plant_id=plant.plant_id,
                    status="active",
                    plant_approve_actions=False,
                )
            )
        session.commit()
    return ApiSeed(
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        boss=actors["boss"],
        engineer=actors["engineer"],
        consultant=actors["consultant"],
        disabled=actors["disabled"],
    )
