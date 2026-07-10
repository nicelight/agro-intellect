from __future__ import annotations

from collections import Counter
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import event, func, select

from backend.app.access_admin.admin_service import AdminService
from backend.app.access_admin.farm_bootstrap import bootstrap_canonical_farm
from backend.app.access_admin.models import (
    Account,
    AdminAuditRecord,
    Base,
    Farm,
    FarmMembership,
    Plant,
    PlantAccessGrant,
)
from backend.app.access_admin.security import verify_password
from backend.app.config import AppSettings
from backend.app.database import build_database
from backend.app.main import create_app


SESSION_COOKIE = "agro_intellect_session"
BOSS_BOOTSTRAP_PASSWORD = "test-only-boss-bootstrap-secret"
ENGINEER_INITIAL_PASSWORD = "test-only-engineer-initial-secret"


def test_ft003_first_boss_to_engineer_grant_audit_integrated_flow():
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
    try:
        with database.session() as session:
            farm_bootstrap = bootstrap_canonical_farm(session)
        assert farm_bootstrap.farm_created is True
        assert farm_bootstrap.plant_created is True

        with database.session() as session:
            first_boss = AdminService(session).bootstrap_first_boss(
                login_name=" boss ",
                display_name=" Local Boss ",
                password=BOSS_BOOTSTRAP_PASSWORD,
            )

        with database.session() as session:
            assert session.scalar(select(func.count(Farm.farm_id))) == 1
            assert session.scalar(select(func.count(Plant.plant_id))) == 1
            canonical_plant = session.scalar(
                select(Plant).where(Plant.plant_key == "tomato_001")
            )
            boss_account = session.get(Account, first_boss.account.account_id)
            boss_membership = session.get(
                FarmMembership, first_boss.membership.membership_id
            )
            assert canonical_plant is not None
            assert canonical_plant.status == "active"
            assert boss_account is not None
            assert boss_membership is not None
            assert boss_account.login_name == "boss"
            assert boss_membership.role_preset == "boss"
            assert verify_password(BOSS_BOOTSTRAP_PASSWORD, boss_account.password_hash)
            assert session.scalar(select(func.count(AdminAuditRecord.admin_audit_id))) == 3

        app = create_app(settings=settings, database=database)
        with TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("127.0.0.1", 50000),
        ) as client:
            boss_login = client.post(
                "/api/session/login",
                json={"login_name": "boss", "password": BOSS_BOOTSTRAP_PASSWORD},
                headers={"x-request-id": "req-boss-login"},
            )
            assert boss_login.status_code == 200
            assert boss_login.headers["cache-control"] == "no-store"
            assert boss_login.json()["role_preset"] == "boss"
            assert BOSS_BOOTSTRAP_PASSWORD not in boss_login.text
            boss_cookie = boss_login.cookies.get(SESSION_COOKIE)
            assert boss_cookie

            engineer_created = client.post(
                "/api/admin/accounts",
                json={
                    "login_name": " engineer ",
                    "display_name": " Engineer ",
                    "password": ENGINEER_INITIAL_PASSWORD,
                    "role_preset": "engineer",
                },
                cookies={SESSION_COOKIE: boss_cookie},
                headers={"x-request-id": "req-create-engineer"},
            )
            assert engineer_created.status_code == 201
            assert engineer_created.headers["cache-control"] == "no-store"
            engineer_body = engineer_created.json()
            engineer_membership_id = engineer_body["membership"]["membership_id"]
            engineer_membership_uuid = uuid.UUID(engineer_membership_id)
            assert engineer_body["login_name"] == "engineer"
            assert engineer_body["membership"]["role_preset"] == "engineer"
            _assert_secret_excluded(engineer_created.text)

            client.cookies.clear()
            engineer_login = client.post(
                "/api/session/login",
                json={
                    "login_name": "engineer",
                    "password": ENGINEER_INITIAL_PASSWORD,
                },
                headers={"x-request-id": "req-engineer-login"},
            )
            assert engineer_login.status_code == 200
            assert engineer_login.headers["cache-control"] == "no-store"
            assert engineer_login.json()["role_preset"] == "engineer"
            engineer_cookie = engineer_login.cookies.get(SESSION_COOKIE)
            assert engineer_cookie
            _assert_secret_excluded(engineer_login.text)

            engineer_denied = client.get(
                "/api/admin/audit",
                cookies={SESSION_COOKIE: engineer_cookie},
                headers={"x-request-id": "req-engineer-admin-denied"},
            )
            assert engineer_denied.status_code == 403
            assert engineer_denied.json()["error"] == {
                "code": "AUTH_FORBIDDEN",
                "message": "Request is not allowed.",
                "request_id": "req-engineer-admin-denied",
            }
            _assert_secret_excluded(engineer_denied.text)

            grant = client.put(
                f"/api/plants/{canonical_plant.plant_id}/access/{engineer_membership_id}",
                json={"plant_approve_actions": True},
                cookies={SESSION_COOKIE: boss_cookie},
                headers={"x-request-id": "req-grant-tomato"},
            )
            assert grant.status_code == 201
            assert grant.headers["cache-control"] == "no-store"
            assert grant.json()["plant_id"] == str(canonical_plant.plant_id)
            assert grant.json()["membership_id"] == engineer_membership_id
            assert grant.json()["status"] == "active"
            assert grant.json()["plant_approve_actions"] is True
            _assert_secret_excluded(grant.text)

            engineer_plants = client.get(
                "/api/plants",
                cookies={SESSION_COOKIE: engineer_cookie},
                headers={"x-request-id": "req-engineer-plants"},
            )
            assert engineer_plants.status_code == 200
            assert engineer_plants.headers["cache-control"] == "no-store"
            assert [item["plant_key"] for item in engineer_plants.json()["items"]] == [
                "tomato_001"
            ]
            assert engineer_plants.json()["items"][0]["permissions"][
                "can_approve_actions"
            ] is True

            baseline_audits = _audit_count(database)
            last_boss_disable = client.post(
                f"/api/admin/accounts/{first_boss.account.account_id}/disable",
                cookies={SESSION_COOKIE: boss_cookie},
                headers={"x-request-id": "req-last-boss-disable"},
            )
            last_boss_demote = client.patch(
                f"/api/admin/memberships/{first_boss.membership.membership_id}/role",
                json={"role_preset": "engineer"},
                cookies={SESSION_COOKIE: boss_cookie},
                headers={"x-request-id": "req-last-boss-demote"},
            )
            assert last_boss_disable.status_code == 409
            assert last_boss_demote.status_code == 409
            assert (
                last_boss_disable.json()["error"]["code"]
                == "ADMIN_LAST_BOSS_CONFLICT"
            )
            assert (
                last_boss_demote.json()["error"]["code"]
                == "ADMIN_LAST_BOSS_CONFLICT"
            )
            assert _audit_count(database) == baseline_audits
            _assert_secret_excluded(last_boss_disable.text)
            _assert_secret_excluded(last_boss_demote.text)

            audit = client.get(
                "/api/admin/audit?limit=20",
                cookies={SESSION_COOKIE: boss_cookie},
                headers={"x-request-id": "req-admin-audit"},
            )
            assert audit.status_code == 200
            assert audit.headers["cache-control"] == "no-store"
            audit_body = audit.json()
            actions = Counter(item["action_type"] for item in audit_body["items"])
            assert actions["farm_created"] == 1
            assert actions["plant_created"] == 1
            assert actions["account_created"] == 2
            assert actions["plant_access_granted"] == 1
            _assert_secret_excluded(audit.text)

        with database.session() as session:
            boss_membership = session.get(
                FarmMembership, first_boss.membership.membership_id
            )
            boss_account = session.get(Account, first_boss.account.account_id)
            engineer_account = session.scalar(
                select(Account).where(Account.login_name == "engineer")
            )
            grant_row = session.scalar(
                select(PlantAccessGrant).where(
                    PlantAccessGrant.membership_id == engineer_membership_uuid
                )
            )
            audits = list(session.scalars(select(AdminAuditRecord)))
            assert boss_membership is not None
            assert boss_membership.role_preset == "boss"
            assert boss_account is not None
            assert boss_account.account_status == "active"
            assert engineer_account is not None
            assert verify_password(
                ENGINEER_INITIAL_PASSWORD, engineer_account.password_hash
            )
            assert grant_row is not None
            assert grant_row.plant_id == canonical_plant.plant_id
            assert grant_row.status == "active"
            assert grant_row.plant_approve_actions is True
            assert all(_audit_is_safe(record) for record in audits)
    finally:
        database.dispose()


def _audit_count(database) -> int:
    with database.session() as session:
        return int(session.scalar(select(func.count(AdminAuditRecord.admin_audit_id))))


def _assert_secret_excluded(text: str) -> None:
    forbidden = (
        BOSS_BOOTSTRAP_PASSWORD,
        ENGINEER_INITIAL_PASSWORD,
        "password_hash",
        "token_hash",
        "authorization",
        "cookie",
    )
    lowered = text.lower()
    assert all(secret not in text for secret in forbidden[:2])
    assert all(fragment not in lowered for fragment in forbidden[2:])


def _audit_is_safe(record: AdminAuditRecord) -> bool:
    combined = " ".join(
        [
            str(record.before_summary),
            str(record.after_summary),
            str(record.source_refs),
        ]
    ).lower()
    forbidden = (
        BOSS_BOOTSTRAP_PASSWORD,
        ENGINEER_INITIAL_PASSWORD,
        "password_hash",
        "token_hash",
        "authorization",
        "cookie",
    )
    return all(secret not in combined for secret in forbidden[:2]) and all(
        fragment not in combined for fragment in forbidden[2:]
    )
