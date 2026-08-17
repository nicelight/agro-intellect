"""Route/auth/pagination/OpenAPI/no-store/safe-failure/no-mutation tests for
GET /api/plants/{plant_id}/dataset-candidates (FT-016-AC-009 / REQ-021).
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, func, inspect, select, text

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
from backend.app.dataset_governance import DatasetCandidate
from backend.app.main import create_app

SESSION_COOKIE = "agro_intellect_session"
NOW = datetime(2026, 8, 17, 10, 0, tzinfo=timezone.utc)

EXPECTED_ITEM_FIELDS = {
    "candidate_id",
    "plant_id",
    "source_kind",
    "source_ref",
    "candidate_status",
    "quality_tier",
    "split",
    "confirmation_source",
    "evidence_refs",
    "curator_decision",
    "corrected",
    "follow_up_seen",
    "can_train_on",
    "record_version",
    "created_at",
    "updated_at",
}

FORBIDDEN_ITEM_FIELDS = {
    "farm_id",
    "candidate_origin",
    "curator_notes_ref",
    "curator_run_id",
    "curator_command_sha256",
    "curator_recorded_at",
    "event_refs",
}


@dataclass(frozen=True)
class ActorSeed:
    account_id: uuid.UUID
    membership_id: uuid.UUID
    token: str


@dataclass(frozen=True)
class DatasetApiSeed:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    boss_only_plant_id: uuid.UUID
    revoked_plant_id: uuid.UUID
    archived_no_grant_plant_id: uuid.UUID
    archived_granted_plant_id: uuid.UUID
    wrong_farm_plant_id: uuid.UUID
    boss: ActorSeed
    engineer: ActorSeed
    consultant: ActorSeed
    disabled: ActorSeed
    candidate_rows: list
    archived_candidate_ids: list


@pytest.fixture
def dataset_api_runtime(tmp_path):
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


def test_bhv001_dataset_candidates_projection_and_no_store(dataset_api_runtime):
    client, database, seed = dataset_api_runtime
    response = client.get(
        f"/api/plants/{seed.plant_id}/dataset-candidates",
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft016-dataset-active"},
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["schema_version"] == 1
    assert body["next_cursor"] is None
    assert len(body["items"]) == len(seed.candidate_rows)

    by_id = {item["candidate_id"]: item for item in body["items"]}
    for row in seed.candidate_rows:
        item = by_id[str(row.candidate_id)]
        assert set(item) == EXPECTED_ITEM_FIELDS
        assert FORBIDDEN_ITEM_FIELDS.isdisjoint(item)
        assert item["plant_id"] == str(seed.plant_id)
        assert item["source_kind"] == row.source_kind
        assert item["source_ref"] == str(row.source_ref)
        assert item["candidate_status"] == row.candidate_status
        assert item["quality_tier"] == row.quality_tier
        assert item["split"] == row.split
        assert item["confirmation_source"] == row.confirmation_source
        assert item["curator_decision"] == row.curator_decision
        assert item["corrected"] == row.corrected
        assert item["follow_up_seen"] == row.follow_up_seen
        assert item["can_train_on"] == row.can_train_on
        assert item["record_version"] == row.record_version
        assert item["evidence_refs"] == row.evidence_refs
        assert "created_at" in item and "updated_at" in item

    # Ordered expected from the DB authority: (updated_at DESC, candidate_id DESC).
    expected = [str(c.candidate_id) for c in sorted(
        seed.candidate_rows,
        key=lambda c: (c.updated_at, c.candidate_id),
        reverse=True,
    )]
    assert [item["candidate_id"] for item in body["items"]] == expected

    confirmed_rows = [r for r in seed.candidate_rows if r.candidate_status == "confirmed"]
    assert {by_id[str(r.candidate_id)]["can_train_on"] for r in confirmed_rows} == {
        False,
        True,
    }
    # Serialized projection must not contain internal/secret material.
    payload_text = response.text
    assert "curator_command_sha256" not in payload_text
    assert "event_refs" not in payload_text
    assert "farm_id" not in payload_text


def test_bhv002_stable_complete_pagination(dataset_api_runtime):
    client, database, seed = dataset_api_runtime
    seen: list[str] = []
    cursor = None
    pages = 0
    while True:
        params = {"limit": 2}
        if cursor is not None:
            params["cursor"] = cursor
        response = client.get(
            f"/api/plants/{seed.plant_id}/dataset-candidates",
            params=params,
            cookies=_cookies(seed.boss),
            headers={"x-request-id": f"req-ft016-page-{pages}"},
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        page = response.json()
        ids = [item["candidate_id"] for item in page["items"]]
        seen.extend(ids)
        pages += 1
        if page["next_cursor"] is None:
            break
        cursor = page["next_cursor"]
        assert len(ids) == 2
    assert sorted(seen) == sorted(
        str(c.candidate_id) for c in seed.candidate_rows
    )
    assert len(seen) == len(seed.candidate_rows)
    assert len(set(seen)) == len(seed.candidate_rows)
    expected_desc = [str(c.candidate_id) for c in sorted(
        seed.candidate_rows,
        key=lambda c: (c.updated_at, c.candidate_id),
        reverse=True,
    )]
    assert seen == expected_desc


def test_bhv003_archived_retained_history_reads(dataset_api_runtime):
    client, _database, seed = dataset_api_runtime
    for name, actor in (
        ("boss", seed.boss),
        ("engineer", seed.engineer),
        ("consultant", seed.consultant),
    ):
        response = client.get(
            f"/api/plants/{seed.archived_granted_plant_id}/dataset-candidates",
            cookies=_cookies(actor),
            headers={"x-request-id": f"req-ft016-archived-{name}"},
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        body = response.json()
        assert {item["candidate_id"] for item in body["items"]} == {
            str(candidate_id) for candidate_id in seed.archived_candidate_ids
        }


def test_bhv004_auth_matrix_no_enumeration(dataset_api_runtime):
    client, _database, seed = dataset_api_runtime
    cases = [
        (seed.engineer, seed.boss_only_plant_id, 404, "AUTH_PLANT_FORBIDDEN"),
        (seed.engineer, seed.revoked_plant_id, 404, "AUTH_PLANT_FORBIDDEN"),
        (
            seed.engineer,
            seed.archived_no_grant_plant_id,
            404,
            "AUTH_PLANT_FORBIDDEN",
        ),
        (seed.engineer, seed.wrong_farm_plant_id, 404, "AUTH_PLANT_FORBIDDEN"),
        (seed.engineer, uuid.uuid4(), 404, "AUTH_PLANT_FORBIDDEN"),
        (seed.disabled, seed.plant_id, 403, "AUTH_MEMBERSHIP_DISABLED"),
    ]
    for actor, plant_id, expected_status, expected_code in cases:
        response = client.get(
            f"/api/plants/{plant_id}/dataset-candidates",
            cookies=_cookies(actor),
            headers={"x-request-id": f"req-ft016-deny-{expected_code.lower()}"},
        )
        assert response.status_code == expected_status
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["error"]["code"] == expected_code
        if expected_code == "AUTH_PLANT_FORBIDDEN":
            assert str(plant_id) not in response.text

    unauthenticated = client.get(
        f"/api/plants/{seed.plant_id}/dataset-candidates",
        headers={"x-request-id": "req-ft016-no-auth"},
    )
    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["cache-control"] == "no-store"
    assert unauthenticated.json()["error"]["code"] == "AUTH_SESSION_REQUIRED"


def test_bhv005_query_validation_and_stable_errors(dataset_api_runtime):
    client, _database, seed = dataset_api_runtime
    base = f"/api/plants/{seed.plant_id}/dataset-candidates"

    limit_cases = [
        ({"limit": "0"}, "DATASET_LIMIT_INVALID"),
        ({"limit": "101"}, "DATASET_LIMIT_INVALID"),
        ({"limit": "not-an-int"}, "DATASET_LIMIT_INVALID"),
        ({"limit": ""}, "DATASET_LIMIT_INVALID"),
    ]
    for params, code in limit_cases:
        response = client.get(
            base,
            params=params,
            cookies=_cookies(seed.engineer),
            headers={"x-request-id": f"req-ft016-{code.lower()}"},
        )
        assert response.status_code == 422
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["error"]["code"] == code

    validation_cases = [
        ({"unexpected": "1"}, "VALIDATION_FAILED"),
        ([("cursor", "a"), ("cursor", "b")], "VALIDATION_FAILED"),
        ([("limit", "1"), ("limit", "2")], "VALIDATION_FAILED"),
    ]
    for params, code in validation_cases:
        response = client.get(
            base,
            params=params,
            cookies=_cookies(seed.engineer),
            headers={"x-request-id": f"req-ft016-{code.lower()}"},
        )
        assert response.status_code == 422
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["error"]["code"] == code

    good_page = client.get(
        f"{base}?limit=1",
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft016-good-page"},
    )
    assert good_page.status_code == 200
    cursor = good_page.json()["next_cursor"]
    assert cursor is not None
    payload = _decoded_cursor_payload(cursor)

    malformed_cursors = [
        "",
        "not-a-cursor",
        f"!{cursor}",
        f"{cursor[:4]} {cursor[4:]}",
        f"{cursor}=",
        _encoded_cursor_payload({**payload, "v": 2}),
        _encoded_cursor_payload({**payload, "extra": True}),
        _encoded_cursor_payload(
            {k: v for k, v in payload.items() if k != "candidate_id"}
        ),
        _encoded_cursor_payload({**payload, "updated_at": "nope"}),
        _encoded_cursor_payload({**payload, "candidate_id": "not-a-uuid"}),
        _encoded_cursor_payload({**payload, "plant_id": str(uuid.uuid4())}),
        _encoded_cursor_payload(payload, canonical_json=False),
    ]
    for index, bad_cursor in enumerate(malformed_cursors):
        params = {"cursor": bad_cursor}
        response = client.get(
            base,
            params=params,
            cookies=_cookies(seed.engineer),
            headers={"x-request-id": f"req-ft016-cursor-invalid-{index}"},
        )
        assert response.status_code == 422
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["error"]["code"] == "DATASET_CURSOR_INVALID"
        assert "secret" not in response.text


def test_bhv006_safe_failure_and_actor_context_first(dataset_api_runtime, monkeypatch):
    client, _database, seed = dataset_api_runtime

    class ExplodingService:
        def __init__(self, *_args, **_kwargs) -> None:
            raise AssertionError("Dataset service must not run before ActorContext")

    monkeypatch.setattr(
        "backend.app.api.dataset_governance.DatasetGovernanceService",
        ExplodingService,
    )
    unauthenticated = client.get(
        f"/api/plants/{seed.plant_id}/dataset-candidates",
        headers={"x-request-id": "req-ft016-before-auth"},
    )
    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["cache-control"] == "no-store"
    assert unauthenticated.json()["error"]["code"] == "AUTH_SESSION_REQUIRED"

    class RawFailingService:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def list_dataset_candidates(self, *args, **kwargs):
            raise RuntimeError("postgresql://admin:secret@localhost/raw database leak")

    monkeypatch.setattr(
        "backend.app.api.dataset_governance.DatasetGovernanceService",
        RawFailingService,
    )
    failed = client.get(
        f"/api/plants/{seed.plant_id}/dataset-candidates",
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft016-read-failed"},
    )
    assert failed.status_code == 500
    assert failed.headers["cache-control"] == "no-store"
    assert failed.json()["error"] == {
        "code": "DATASET_READ_FAILED",
        "message": "Dataset candidates could not be read.",
        "request_id": "req-ft016-read-failed",
    }
    assert "secret" not in failed.text
    assert "raw database leak" not in failed.text


def test_bhv007_openapi_shape_and_no_mutation_routes():
    database = build_database(AppSettings(database_url="sqlite+pysqlite:///:memory:"))
    try:
        schema = create_app(database=database).openapi()
    finally:
        database.dispose()

    paths = schema["paths"]
    dataset_path = "/api/plants/{plant_id}/dataset-candidates"
    assert dataset_path in paths
    assert set(paths[dataset_path]) == {"get"}

    dataset_paths = {
        path: set(methods)
        for path, methods in paths.items()
        if "candidate" in path or "dataset" in path
    }
    assert dataset_paths == {dataset_path: {"get"}}

    get_operation = paths[dataset_path]["get"]
    assert set(get_operation["responses"]) >= {
        "200",
        "401",
        "403",
        "404",
        "422",
        "500",
    }
    query_params = {
        parameter["name"]: parameter
        for parameter in get_operation["parameters"]
        if parameter["in"] == "query"
    }
    assert set(query_params) == {"cursor", "limit"}
    assert query_params["limit"]["schema"]["default"] == 50
    assert query_params["limit"]["schema"]["minimum"] == 1
    assert query_params["limit"]["schema"]["maximum"] == 100

    schemas = schema["components"]["schemas"]
    list_props = set(schemas["DatasetCandidateListResponse"]["properties"])
    assert list_props == {"schema_version", "items", "next_cursor"}
    item_props = set(schemas["DatasetCandidateItemResponse"]["properties"])
    assert item_props == EXPECTED_ITEM_FIELDS
    evidence_props = set(schemas["EvidenceRefV1"]["properties"])
    assert evidence_props == {"kind", "ref"}


def test_bhv008_reads_create_zero_writes(dataset_api_runtime, monkeypatch):
    client, database, seed = dataset_api_runtime

    def snapshot():
        inspector = inspect(database.engine())
        snap = {}
        with database.session() as session:
            for table_name in sorted(inspector.get_table_names()):
                count = session.execute(
                    select(func.count()).select_from(text(f'"{table_name}"'))
                ).scalar()
                rows = session.execute(
                    text(f'SELECT * FROM "{table_name}" ORDER BY 1')
                ).mappings().all()
                snap[table_name] = (
                    count,
                    [tuple(sorted(item.items())) for item in rows],
                )
        return snap

    before = snapshot()
    base = f"/api/plants/{seed.plant_id}/dataset-candidates"

    response = client.get(
        base,
        params={"limit": 2},
        cookies=_cookies(seed.engineer),
    )
    assert response.status_code == 200
    cursor = response.json()["next_cursor"]
    response = client.get(
        base,
        params={"limit": 2, "cursor": cursor},
        cookies=_cookies(seed.engineer),
    )
    assert response.status_code == 200

    for plant_id in (seed.boss_only_plant_id, uuid.uuid4()):
        denied = client.get(
            f"/api/plants/{plant_id}/dataset-candidates",
            cookies=_cookies(seed.engineer),
        )
        assert denied.status_code == 404

    assert snapshot() == before

    import backend.app.api.dataset_governance as route_module

    class RawFailingService:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def list_dataset_candidates(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(route_module, "DatasetGovernanceService", RawFailingService)
    failed = client.get(
        base,
        cookies=_cookies(seed.engineer),
    )
    assert failed.status_code == 500
    rerun = client.get(
        base,
        cookies=_cookies(seed.engineer),
    )
    assert rerun.status_code == 500
    monkeypatch.undo()

    assert snapshot() == before


def _cookies(actor: ActorSeed) -> dict[str, str]:
    return {SESSION_COOKIE: actor.token}


def _decoded_cursor_payload(cursor: str) -> dict[str, object]:
    padded = cursor + ("=" * (-len(cursor) % 4))
    decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
    payload = json.loads(decoded.decode("utf-8"))
    assert isinstance(payload, dict)
    return payload


def _encoded_cursor_payload(
    payload: dict[str, object],
    *,
    canonical_json: bool = True,
) -> str:
    separators = (",", ":") if canonical_json else (", ", ": ")
    raw = json.dumps(payload, separators=separators, sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _seed(database) -> DatasetApiSeed:
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
        boss_only_plant = Plant(
            farm_id=farm.farm_id,
            plant_key="boss_dataset_001",
            display_name="Boss Dataset 001",
            status="active",
        )
        revoked_plant = Plant(
            farm_id=farm.farm_id,
            plant_key="revoked_dataset_001",
            display_name="Revoked Dataset 001",
            status="active",
        )
        archived_no_grant_plant = Plant(
            farm_id=farm.farm_id,
            plant_key="archived_dataset_001",
            display_name="Archived Dataset 001",
            status="archived",
        )
        archived_granted_plant = Plant(
            farm_id=farm.farm_id,
            plant_key="archived_dataset_002",
            display_name="Archived Dataset 002",
            status="archived",
        )
        wrong_farm_plant = Plant(
            plant_id=uuid.uuid4(),
            farm_id=uuid.uuid4(),
            plant_key="wrong_dataset_001",
            display_name="Wrong Dataset 001",
            status="active",
        )
        plants = [
            plant,
            boss_only_plant,
            revoked_plant,
            archived_no_grant_plant,
            archived_granted_plant,
            wrong_farm_plant,
        ]
        session.add_all(plants)
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
                login_name=f"ft016-{name}",
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

        for name in ("engineer", "consultant"):
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
                    membership_id=memberships[name].membership_id,
                    plant_id=archived_granted_plant.plant_id,
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

        candidate_rows = []
        for index in range(7):
            confirmed = index in {0, 2}
            row = DatasetCandidate(
                candidate_id=uuid.uuid4(),
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                candidate_status="confirmed" if confirmed else "candidate",
                candidate_origin="raw",
                quality_tier="standard",
                split=None,
                confirmation_source="human_review" if confirmed else None,
                evidence_refs=[
                    {"kind": "photo", "ref": str(uuid.uuid4())},
                    {"kind": "observation", "ref": str(uuid.uuid4())},
                ],
                source_kind=(
                    "photo_catalog_item" if index % 2 == 0 else "daily_check_in"
                ),
                source_ref=uuid.uuid4(),
                curator_decision=("deferred" if index == 1 else None),
                curator_notes_ref=("internal://notes" if index == 1 else None),
                curator_run_id=(uuid.uuid4() if index == 1 else None),
                curator_command_sha256=("b" * 64 if index == 1 else None),
                curator_recorded_at=(NOW + timedelta(minutes=index) if index == 1 else None),
                corrected=(index == 3),
                follow_up_seen=(index in {2, 4}),
                can_train_on=(confirmed and index == 0),
                record_version=index + 1,
                event_refs=[{"kind": "timeline", "ref": str(uuid.uuid4())}],
                created_at=NOW + timedelta(minutes=index),
                updated_at=NOW + timedelta(minutes=index),
            )
            session.add(row)
            candidate_rows.append(row)

        archived_candidate_ids = []
        for index in range(2):
            row = DatasetCandidate(
                candidate_id=uuid.uuid4(),
                farm_id=farm.farm_id,
                plant_id=archived_granted_plant.plant_id,
                candidate_status="confirmed",
                candidate_origin="raw",
                quality_tier="standard",
                split=None,
                confirmation_source="expert_review",
                evidence_refs=[{"kind": "measurement", "ref": str(uuid.uuid4())}],
                source_kind="manual_measurement",
                source_ref=uuid.uuid4(),
                curator_decision=None,
                curator_notes_ref=None,
                curator_run_id=None,
                curator_command_sha256=None,
                curator_recorded_at=None,
                corrected=False,
                follow_up_seen=False,
                can_train_on=True,
                record_version=1,
                event_refs=[],
                created_at=NOW,
                updated_at=NOW + timedelta(minutes=index),
            )
            session.add(row)
            archived_candidate_ids.append(row.candidate_id)
        session.commit()

        # Detach the appended ORM objects so later reads see the persisted values.
        session.expunge_all()
        candidate_rows = [
            session.get(DatasetCandidate, row.candidate_id) for row in candidate_rows
        ]

    return DatasetApiSeed(
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        boss_only_plant_id=boss_only_plant.plant_id,
        revoked_plant_id=revoked_plant.plant_id,
        archived_no_grant_plant_id=archived_no_grant_plant.plant_id,
        archived_granted_plant_id=archived_granted_plant.plant_id,
        wrong_farm_plant_id=wrong_farm_plant.plant_id,
        boss=actors["boss"],
        engineer=actors["engineer"],
        consultant=actors["consultant"],
        disabled=actors["disabled"],
        candidate_rows=candidate_rows,
        archived_candidate_ids=archived_candidate_ids,
    )