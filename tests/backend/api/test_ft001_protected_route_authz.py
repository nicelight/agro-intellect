from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from fastapi import Depends
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event

from backend.app.access_admin.dependencies import (
    AuthorizedPlantRequest,
    require_actor_context,
    require_plant_permission,
)
from backend.app.access_admin.actor_context import ActorContext
from backend.app.access_admin.models import Account, Base, FarmMembership, LocalSession
from backend.app.access_admin.permissions import (
    GrantStatus,
    OperationKind,
    PlantAccessSnapshot,
    PlantGrantSnapshot,
    PlantSnapshot,
    PlantStatus,
)
from backend.app.access_admin.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
)
from backend.app.config import AppSettings
from backend.app.database import build_database
from backend.app.main import create_app


@pytest.fixture
def protected_runtime():
    settings = AppSettings(database_url="sqlite+pysqlite:///:memory:")
    database = build_database(settings)
    engine = database.engine()

    def install_sqlite_contract_functions(dbapi_connection, _record):
        dbapi_connection.create_function(
            "btrim",
            1,
            lambda value: value.strip() if isinstance(value, str) else value,
        )

    event.listen(engine, "connect", install_sqlite_contract_functions)
    Base.metadata.create_all(engine)
    app = create_app(settings=settings, database=database)
    business_calls: list[str] = []

    @app.get("/api/protected")
    def protected_route(actor: ActorContext = Depends(require_actor_context)):
        business_calls.append("protected")
        return {
            "account_id": actor.account_id,
            "farm_id": actor.farm_id,
            "role_preset": actor.role_preset,
        }

    plant_dependency = require_plant_permission(OperationKind.NORMAL_READ)

    @app.get("/api/plants/{plant_id}/protected")
    def protected_plant_route(
        plant: AuthorizedPlantRequest = Depends(plant_dependency),
    ):
        business_calls.append("plant")
        return {
            "plant_id": plant.permission.plant_id,
            "can_read": plant.permission.can_read,
        }

    try:
        yield app, database, business_calls
    finally:
        database.dispose()


def _seed_session(
    database,
    *,
    account_status: str = "active",
    membership_status: str | None = "active",
    expires_delta: timedelta = timedelta(days=1),
    role_preset: str = "boss",
):
    raw_token = generate_session_token()
    now = datetime.now(timezone.utc)
    with database.session() as database_session:
        account = Account(
            login_name=f"user-{uuid.uuid4().hex}",
            display_name="Protected User",
            account_status=account_status,
            password_hash=hash_password("test-only-password"),
        )
        database_session.add(account)
        database_session.flush()
        membership = None
        if membership_status is not None:
            membership = FarmMembership(
                account_id=account.account_id,
                farm_id=uuid.uuid4(),
                role_preset=role_preset,
                membership_status=membership_status,
            )
            database_session.add(membership)
            database_session.flush()
        database_session.add(
            LocalSession(
                account_id=account.account_id,
                token_hash=hash_session_token(raw_token),
                created_at=now,
                expires_at=now + expires_delta,
                auth_method="local_password",
            )
        )
        database_session.commit()
    return raw_token, account, membership


@pytest.mark.parametrize(
    ("case", "expected_status", "expected_code"),
    [
        ("missing", 401, "AUTH_SESSION_REQUIRED"),
        ("invalid", 401, "AUTH_SESSION_INVALID"),
        ("bearer", 401, "AUTH_SESSION_INVALID"),
        ("expired", 401, "AUTH_SESSION_EXPIRED"),
        ("account_disabled", 403, "AUTH_ACCOUNT_DISABLED"),
        ("membership_required", 403, "AUTH_MEMBERSHIP_REQUIRED"),
        ("membership_disabled", 403, "AUTH_MEMBERSHIP_DISABLED"),
    ],
)
def test_protected_dependency_fails_before_business_logic(
    protected_runtime,
    case: str,
    expected_status: int,
    expected_code: str,
):
    app, database, business_calls = protected_runtime
    headers = {"x-request-id": f"req-{case}"}
    raw_token = None
    if case == "invalid":
        raw_token = generate_session_token()
    elif case == "bearer":
        headers["authorization"] = "Bearer synthetic-disabled-credential"
    elif case == "expired":
        raw_token, _account, _membership = _seed_session(
            database,
            expires_delta=timedelta(days=-1),
        )
    elif case == "account_disabled":
        raw_token, _account, _membership = _seed_session(
            database,
            account_status="disabled",
        )
    elif case == "membership_required":
        raw_token, _account, _membership = _seed_session(
            database,
            membership_status=None,
        )
    elif case == "membership_disabled":
        raw_token, _account, _membership = _seed_session(
            database,
            membership_status="disabled",
        )
    if raw_token is not None:
        headers["cookie"] = f"agro_intellect_session={raw_token}"

    with TestClient(
        app,
        base_url="http://127.0.0.1",
        client=("127.0.0.1", 50000),
    ) as client:
        response = client.get("/api/protected", headers=headers)

    assert response.status_code == expected_status
    assert response.json() == {
        "error": {
            "code": expected_code,
            "message": response.json()["error"]["message"],
            "request_id": f"req-{case}",
        }
    }
    assert business_calls == []
    if raw_token is not None:
        assert raw_token not in response.text
    if case == "bearer":
        assert "synthetic-disabled-credential" not in response.text


def test_valid_protected_route_returns_safe_actor_summary(protected_runtime):
    app, database, business_calls = protected_runtime
    raw_token, account, membership = _seed_session(database)

    with TestClient(
        app,
        base_url="http://127.0.0.1",
        client=("127.0.0.1", 50000),
    ) as client:
        response = client.get(
            "/api/protected",
            headers={"cookie": f"agro_intellect_session={raw_token}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "account_id": str(account.account_id),
        "farm_id": str(membership.farm_id),
        "role_preset": "boss",
    }
    assert business_calls == ["protected"]
    assert raw_token not in response.text
    assert all(
        forbidden not in response.text
        for forbidden in ("session_id", "token_hash", "password_hash")
    )


def test_valid_plant_dependency_allows_only_resolved_scope(protected_runtime):
    app, database, business_calls = protected_runtime
    raw_token, _account, membership = _seed_session(
        database,
        role_preset="engineer",
    )
    plant_id = uuid.uuid4()
    grant_id = uuid.uuid4()
    app.state.plant_access_snapshot_provider = lambda **_kwargs: PlantAccessSnapshot(
        plant=PlantSnapshot(
            plant_id=plant_id,
            farm_id=membership.farm_id,
            status=PlantStatus.ACTIVE,
        ),
        grant=PlantGrantSnapshot(
            grant_id=grant_id,
            membership_id=membership.membership_id,
            farm_id=membership.farm_id,
            plant_id=plant_id,
            status=GrantStatus.ACTIVE,
        ),
    )

    with TestClient(
        app,
        base_url="http://127.0.0.1",
        client=("127.0.0.1", 50000),
    ) as client:
        response = client.get(
            f"/api/plants/{plant_id}/protected",
            headers={"cookie": f"agro_intellect_session={raw_token}"},
        )

    assert response.status_code == 200
    assert response.json() == {"plant_id": str(plant_id), "can_read": True}
    assert business_calls == ["plant"]
    assert raw_token not in response.text


@pytest.mark.parametrize("denial", ["missing", "revoked", "archived"])
def test_plant_denial_is_generic_and_no_existence_leak(
    protected_runtime,
    denial: str,
):
    app, database, business_calls = protected_runtime
    raw_token, _account, membership = _seed_session(
        database,
        role_preset="engineer",
    )
    plant_id = uuid.uuid4()
    grant = None
    plant_status = PlantStatus.ARCHIVED if denial == "archived" else PlantStatus.ACTIVE
    if denial != "missing":
        grant = PlantGrantSnapshot(
            grant_id=uuid.uuid4(),
            membership_id=membership.membership_id,
            farm_id=membership.farm_id,
            plant_id=plant_id,
            status=(
                GrantStatus.REVOKED if denial == "revoked" else GrantStatus.ACTIVE
            ),
        )
    app.state.plant_access_snapshot_provider = lambda **_kwargs: PlantAccessSnapshot(
        plant=PlantSnapshot(
            plant_id=plant_id,
            farm_id=membership.farm_id,
            status=plant_status,
        ),
        grant=grant,
    )

    with TestClient(
        app,
        base_url="http://127.0.0.1",
        client=("127.0.0.1", 50000),
    ) as client:
        response = client.get(
            f"/api/plants/{plant_id}/protected",
            headers={
                "cookie": f"agro_intellect_session={raw_token}",
                "x-request-id": "req-plant-denied",
            },
        )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "AUTH_PLANT_FORBIDDEN",
            "message": "Plant is not available.",
            "request_id": "req-plant-denied",
        }
    }
    assert str(plant_id) not in response.text
    assert business_calls == []
