from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import event, select
import pytest

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


@dataclass(frozen=True)
class ActorSeed:
    membership_id: uuid.UUID
    token: str


@dataclass(frozen=True)
class IntegratedSeed:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    boss: ActorSeed
    engineer: ActorSeed
    consultant: ActorSeed


@pytest.fixture
def integrated_api_runtime():
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


def test_engineer_integrated_create_select_rename_and_management_denial(
    integrated_api_runtime,
):
    client, _database, seed = integrated_api_runtime

    health = client.get("/health")
    ready = client.get("/ready")
    assert health.json() == {"status": "ok"}
    assert ready.json() == {"status": "ready"}

    created = client.post(
        "/api/plants",
        json={"plant_key": "lettuce_001", "display_name": " Lettuce "},
        cookies=_cookies(seed.engineer),
    )
    assert created.status_code == 201
    body = created.json()
    plant_id = body["plant_id"]
    assert body["plant_key"] == "lettuce_001"
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

    listed = client.get("/api/plants", cookies=_cookies(seed.engineer))
    assert listed.status_code == 200
    assert [item["plant_key"] for item in listed.json()["items"]] == [
        "lettuce_001",
        "tomato_001",
    ]

    detail = client.get(f"/api/plants/{plant_id}", cookies=_cookies(seed.engineer))
    assert detail.status_code == 200
    assert detail.json()["permissions"]["grant_id"] == body["permissions"]["grant_id"]

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
    assert archive.status_code == 404
    assert access.status_code == 404
    assert archive.json()["error"]["code"] == "AUTH_PLANT_FORBIDDEN"

    consultant_items = client.get(
        "/api/plants",
        cookies=_cookies(seed.consultant),
    ).json()["items"]
    assert [item["plant_key"] for item in consultant_items] == ["tomato_001"]
    consultant_permission = consultant_items[0]["permissions"]
    assert consultant_permission["can_read"] is True
    assert consultant_permission["can_comment"] is True
    assert consultant_permission["can_operate"] is False
    assert consultant_permission["can_create_domain_tasks"] is False
    assert consultant_permission["can_approve_actions"] is False

    consultant_rename = client.patch(
        f"/api/plants/{seed.plant_id}",
        json={"display_name": "Consultant Rename"},
        cookies=_cookies(seed.consultant),
    )
    assert consultant_rename.status_code == 404
    assert consultant_rename.json()["error"]["code"] == "AUTH_PLANT_FORBIDDEN"


def test_boss_integrated_archive_grant_restore_preserves_current_permissions(
    integrated_api_runtime,
):
    client, _database, seed = integrated_api_runtime

    initial = client.get(
        f"/api/plants/{seed.plant_id}",
        cookies=_cookies(seed.engineer),
    )
    assert initial.status_code == 200
    original_grant_id = initial.json()["permissions"]["grant_id"]
    assert original_grant_id is not None

    archived = client.post(
        f"/api/plants/{seed.plant_id}/archive",
        cookies=_cookies(seed.boss),
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert archived.json()["permissions"]["can_read"] is False

    archived_engineer = client.get(
        f"/api/plants/{seed.plant_id}",
        cookies=_cookies(seed.engineer),
    )
    assert archived_engineer.status_code == 404
    assert client.get("/api/plants", cookies=_cookies(seed.engineer)).json() == {
        "items": []
    }

    updated_grant = client.put(
        f"/api/plants/{seed.plant_id}/access/{seed.engineer.membership_id}",
        json={"plant_approve_actions": True},
        cookies=_cookies(seed.boss),
    )
    assert updated_grant.status_code == 200
    assert updated_grant.json()["grant_id"] == original_grant_id
    assert updated_grant.json()["plant_approve_actions"] is True

    still_archived = client.get(
        f"/api/plants/{seed.plant_id}",
        cookies=_cookies(seed.engineer),
    )
    assert still_archived.status_code == 404

    restored = client.post(
        f"/api/plants/{seed.plant_id}/restore",
        cookies=_cookies(seed.boss),
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"

    restored_engineer = client.get(
        f"/api/plants/{seed.plant_id}",
        cookies=_cookies(seed.engineer),
    )
    assert restored_engineer.status_code == 200
    restored_permissions = restored_engineer.json()["permissions"]
    assert restored_permissions["grant_id"] == original_grant_id
    assert restored_permissions["can_read"] is True
    assert restored_permissions["can_operate"] is True
    assert restored_permissions["can_manage_access"] is False
    assert restored_permissions["can_approve_actions"] is True


def _cookies(actor: ActorSeed) -> dict[str, str]:
    return {"agro_intellect_session": actor.token}


def _seed(database) -> IntegratedSeed:
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
        for name, role in (
            ("boss", "boss"),
            ("engineer", "engineer"),
            ("consultant", "consultant"),
        ):
            account = Account(
                login_name=f"integrated-{name}",
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
                membership_status="active",
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
    return IntegratedSeed(
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        boss=actors["boss"],
        engineer=actors["engineer"],
        consultant=actors["consultant"],
    )
