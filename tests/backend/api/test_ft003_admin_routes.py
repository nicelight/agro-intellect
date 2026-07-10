from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, func, select

from backend.app.access_admin.admin_service import (
    AdminCommandError,
    AdminCommandErrorCode,
)
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
    verify_password,
)
from backend.app.config import AppSettings
from backend.app.database import build_database
from backend.app.main import create_app


@dataclass(frozen=True)
class ActorSeed:
    account_id: uuid.UUID
    membership_id: uuid.UUID
    token: str


@dataclass(frozen=True)
class ApiSeed:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    boss: ActorSeed
    engineer: ActorSeed
    consultant: ActorSeed


@pytest.fixture
def admin_runtime():
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


def test_boss_creates_engineer_with_safe_response_and_audit(admin_runtime):
    client, database, seed = admin_runtime
    response = client.post(
        "/api/admin/accounts",
        json={
            "login_name": " engineer_two ",
            "display_name": " Engineer Two ",
            "password": "initial-secret",
            "role_preset": "engineer",
        },
        cookies=_cookies(seed.boss),
    )

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["login_name"] == "engineer_two"
    assert body["display_name"] == "Engineer Two"
    assert body["account_status"] == "active"
    assert body["membership"]["role_preset"] == "engineer"
    assert "initial-secret" not in response.text
    assert "password" not in response.text
    assert "password_hash" not in response.text

    with database.session() as session:
        account = session.scalar(
            select(Account).where(Account.login_name == "engineer_two")
        )
        audit = session.scalar(
            select(AdminAuditRecord).where(
                AdminAuditRecord.action_type == "account_created",
                AdminAuditRecord.target_id == account.account_id,
            )
        )
        assert verify_password("initial-secret", account.password_hash)
        assert account.password_hash not in response.text
        assert audit.after_summary["login_name"] == "engineer_two"
        assert audit.after_summary["membership"]["role_preset"] == "engineer"
        assert "initial-secret" not in str(audit.after_summary)
        assert "password_hash" not in str(audit.after_summary)
        assert session.scalar(select(func.count(AdminAuditRecord.admin_audit_id))) == 1


def test_admin_lists_accounts_plants_and_audit_with_cursor(admin_runtime):
    client, database, seed = admin_runtime
    with database.session() as session:
        session.add(
            AdminAuditRecord(
                farm_id=seed.farm_id,
                actor_kind="account",
                actor_account_id=seed.boss.account_id,
                actor_membership_id=seed.boss.membership_id,
                actor_role_preset="boss",
                action_type="plant_access_granted",
                target_type="plant_access_grant",
                target_id=uuid.uuid4(),
                plant_id=seed.plant_id,
                request_id="req-seed-audit-1",
                before_summary={},
                after_summary={"safe": "grant"},
                source_refs=[],
            )
        )
        session.add(
            AdminAuditRecord(
                farm_id=seed.farm_id,
                actor_kind="account",
                actor_account_id=seed.boss.account_id,
                actor_membership_id=seed.boss.membership_id,
                actor_role_preset="boss",
                action_type="plant_approve_actions_changed",
                target_type="plant_access_grant",
                target_id=uuid.uuid4(),
                plant_id=seed.plant_id,
                request_id="req-seed-audit-2",
                before_summary={"plant_approve_actions": False},
                after_summary={"plant_approve_actions": True},
                source_refs=[],
            )
        )
        session.commit()

    accounts = client.get(
        "/api/admin/accounts?role_preset=engineer",
        cookies=_cookies(seed.boss),
    )
    assert accounts.status_code == 200
    assert [item["login_name"] for item in accounts.json()["items"]] == ["engineer"]
    assert {"created_at", "updated_at"} <= set(accounts.json()["items"][0])

    plants = client.get("/api/admin/plants", cookies=_cookies(seed.boss))
    assert plants.status_code == 200
    assert plants.json()["items"] == [
        {
            "plant_id": str(seed.plant_id),
            "farm_id": str(seed.farm_id),
            "plant_key": "tomato_001",
            "display_name": "Tomato 001",
            "status": "active",
            "created_at": plants.json()["items"][0]["created_at"],
            "updated_at": plants.json()["items"][0]["updated_at"],
            "grant_counts": {
                "active": 2,
                "revoked": 0,
                "approve_actions_enabled": 1,
            },
        }
    ]

    first_page = client.get(
        "/api/admin/audit?limit=1&target_type=plant_access_grant",
        cookies=_cookies(seed.boss),
    )
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert len(first_body["items"]) == 1
    assert first_body["next_cursor"]
    assert "password" not in first_page.text

    second_page = client.get(
        f"/api/admin/audit?limit=1&target_type=plant_access_grant"
        f"&cursor={first_body['next_cursor']}",
        cookies=_cookies(seed.boss),
    )
    assert second_page.status_code == 200
    assert len(second_page.json()["items"]) == 1
    assert second_page.json()["items"][0]["admin_audit_id"] != (
        first_body["items"][0]["admin_audit_id"]
    )

    invalid_cursor = client.get(
        "/api/admin/audit?cursor=not-a-valid-cursor",
        cookies=_cookies(seed.boss),
        headers={"x-request-id": "req-bad-cursor"},
    )
    assert invalid_cursor.status_code == 422
    assert invalid_cursor.json()["error"] == {
        "code": "ADMIN_AUDIT_CURSOR_INVALID",
        "message": "Audit cursor is invalid.",
        "request_id": "req-bad-cursor",
    }


def test_audit_cursor_reaches_matching_records_beyond_first_hundred(admin_runtime):
    client, database, seed = admin_runtime
    base_time = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    with database.session() as session:
        for index in range(121):
            session.add(
                AdminAuditRecord(
                    farm_id=seed.farm_id,
                    actor_kind="account",
                    actor_account_id=seed.boss.account_id,
                    actor_membership_id=seed.boss.membership_id,
                    actor_role_preset="boss",
                    action_type="plant_access_granted",
                    target_type="plant_access_grant",
                    target_id=uuid.uuid4(),
                    plant_id=seed.plant_id,
                    request_id=f"req-bulk-{index:03d}",
                    before_summary={},
                    after_summary={"index": index},
                    source_refs=[],
                    created_at=base_time - timedelta(seconds=index),
                )
            )
        session.commit()

    first = client.get(
        "/api/admin/audit?limit=50&target_type=plant_access_grant",
        cookies=_cookies(seed.boss),
    )
    assert first.status_code == 200
    first_body = first.json()
    assert len(first_body["items"]) == 50
    assert first_body["items"][0]["request_id"] == "req-bulk-000"
    assert first_body["items"][-1]["request_id"] == "req-bulk-049"
    assert first_body["next_cursor"]

    second = client.get(
        f"/api/admin/audit?limit=50&target_type=plant_access_grant"
        f"&cursor={first_body['next_cursor']}",
        cookies=_cookies(seed.boss),
    )
    assert second.status_code == 200
    second_body = second.json()
    assert len(second_body["items"]) == 50
    assert second_body["items"][0]["request_id"] == "req-bulk-050"
    assert second_body["items"][-1]["request_id"] == "req-bulk-099"
    assert second_body["next_cursor"]

    third = client.get(
        f"/api/admin/audit?limit=50&target_type=plant_access_grant"
        f"&cursor={second_body['next_cursor']}",
        cookies=_cookies(seed.boss),
    )
    assert third.status_code == 200
    third_body = third.json()
    assert len(third_body["items"]) == 21
    assert third_body["items"][0]["request_id"] == "req-bulk-100"
    assert third_body["items"][-1]["request_id"] == "req-bulk-120"
    assert third_body["next_cursor"] is None


def test_non_boss_denial_and_last_boss_guard_write_no_audit(admin_runtime):
    client, database, seed = admin_runtime
    denied = client.get(
        "/api/admin/accounts",
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-non-boss"},
    )
    assert denied.status_code == 403
    assert denied.json()["error"] == {
        "code": "AUTH_FORBIDDEN",
        "message": "Request is not allowed.",
        "request_id": "req-non-boss",
    }

    no_body_disable = client.post(
        f"/api/admin/accounts/{seed.engineer.account_id}/disable",
        cookies=_cookies(seed.boss),
    )
    assert no_body_disable.status_code == 200
    assert no_body_disable.headers["cache-control"] == "no-store"
    assert no_body_disable.json()["account_status"] == "disabled"
    assert "password" not in no_body_disable.text

    baseline_audits = _audit_count(database)
    disable = client.post(
        f"/api/admin/accounts/{seed.boss.account_id}/disable",
        json={"reason": "owner request"},
        cookies=_cookies(seed.boss),
        headers={"x-request-id": "req-last-disable"},
    )
    demote = client.patch(
        f"/api/admin/memberships/{seed.boss.membership_id}/role",
        json={"role_preset": "engineer"},
        cookies=_cookies(seed.boss),
        headers={"x-request-id": "req-last-demote"},
    )
    assert disable.status_code == 409
    assert demote.status_code == 409
    assert disable.json()["error"]["code"] == "ADMIN_LAST_BOSS_CONFLICT"
    assert demote.json()["error"]["code"] == "ADMIN_LAST_BOSS_CONFLICT"
    assert _audit_count(database) == baseline_audits

    with database.session() as session:
        membership = session.get(FarmMembership, seed.boss.membership_id)
        account = session.get(Account, seed.boss.account_id)
        assert membership.role_preset == "boss"
        assert membership.membership_status == "active"
        assert account.account_status == "active"


def test_duplicate_and_generic_persistence_failures_are_distinct(
    admin_runtime,
    monkeypatch,
):
    client, database, seed = admin_runtime
    duplicate = client.post(
        "/api/admin/accounts",
        json={
            "login_name": " engineer ",
            "display_name": "Duplicate",
            "password": "other-secret",
            "role_preset": "engineer",
        },
        cookies=_cookies(seed.boss),
        headers={"x-request-id": "req-duplicate"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"] == {
        "code": "ADMIN_ACCOUNT_CONFLICT",
        "message": "Account login is already in use.",
        "request_id": "req-duplicate",
    }
    assert "other-secret" not in duplicate.text
    assert _account_exists(database, "duplicate") is False

    class FailingAdminService:
        def __init__(self, _session) -> None:
            pass

        def create_account(self, *_args, **_kwargs):
            raise AdminCommandError(AdminCommandErrorCode.PERSISTENCE_FAILED)

    monkeypatch.setattr("backend.app.api.admin.AdminService", FailingAdminService)
    generic = client.post(
        "/api/admin/accounts",
        json={
            "login_name": "new_engineer",
            "display_name": "New Engineer",
            "password": "generic-secret",
            "role_preset": "engineer",
        },
        cookies=_cookies(seed.boss),
        headers={"x-request-id": "req-generic"},
    )
    assert generic.status_code == 500
    assert generic.json()["error"] == {
        "code": "ADMIN_PERSISTENCE_FAILED",
        "message": "Admin request could not be completed.",
        "request_id": "req-generic",
    }
    assert "generic-secret" not in generic.text
    assert "ADMIN_ACCOUNT_CONFLICT" not in generic.text
    assert _account_exists(database, "new_engineer") is False


def _cookies(actor: ActorSeed) -> dict[str, str]:
    return {"agro_intellect_session": actor.token}


def _audit_count(database) -> int:
    with database.session() as session:
        return int(session.scalar(select(func.count(AdminAuditRecord.admin_audit_id))))


def _account_exists(database, login_name: str) -> bool:
    with database.session() as session:
        return session.scalar(
            select(Account.account_id).where(Account.login_name == login_name)
        ) is not None


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
        for name, role in (
            ("boss", "boss"),
            ("engineer", "engineer"),
            ("consultant", "consultant"),
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
            actors[name] = ActorSeed(
                account_id=account.account_id,
                membership_id=membership.membership_id,
                token=token,
            )
            memberships[name] = membership
        session.add(
            PlantAccessGrant(
                membership_id=memberships["engineer"].membership_id,
                plant_id=plant.plant_id,
                status="active",
                plant_approve_actions=True,
            )
        )
        session.add(
            PlantAccessGrant(
                membership_id=memberships["consultant"].membership_id,
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
    )
