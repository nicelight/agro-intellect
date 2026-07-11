from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event

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
from backend.app.photo_intake import PhotoCatalogItem
from backend.app.plant_operations import DailyCheckIn
from tests.backend.plant_history.conftest import _postgres_database


JPEG_BYTES = b"\xff\xd8\xff\xe0ft006-api-history-photo"


@dataclass(frozen=True)
class ActorSeed:
    account_id: uuid.UUID
    membership_id: uuid.UUID
    token: str


@dataclass(frozen=True)
class HistoryApiSeed:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    boss_only_plant_id: uuid.UUID
    revoked_plant_id: uuid.UUID
    archived_no_grant_plant_id: uuid.UUID
    wrong_farm_plant_id: uuid.UUID
    boss: ActorSeed
    engineer: ActorSeed
    consultant: ActorSeed
    disabled: ActorSeed


@pytest.fixture
def history_api_runtime(tmp_path: Path):
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
            yield (
                client,
                database,
                seed,
                settings.local_artifact_root,
                settings.local_timeline_root,
            )
    finally:
        database.dispose()


@pytest.fixture
def postgres_history_api_runtime(tmp_path: Path):
    with _postgres_database() as database:
        settings = AppSettings.from_env().model_copy(
            update={
                "local_artifact_root": tmp_path / "artifacts",
                "local_timeline_root": tmp_path / "timeline",
            }
        )
        seed = _seed(database, include_wrong_farm_plant=False)
        app = create_app(settings=settings, database=database)
        with TestClient(app, base_url="http://127.0.0.1") as client:
            yield client, database, seed


def test_ft006_bhv001_history_routes_project_integrated_evidence(
    history_api_runtime,
):
    client, database, seed, artifact_root, timeline_root = history_api_runtime
    check_in_id, photo_id = _create_check_in_and_photo(client, seed)

    original_path, manifest_path = _photo_paths(database, artifact_root, photo_id)
    assert original_path.exists()
    assert manifest_path.exists()
    original_path.unlink()
    manifest_path.unlink()

    card = client.get(
        f"/api/plants/{seed.plant_id}/history/card",
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft006-card-active"},
    )
    assert card.status_code == 200
    assert card.headers["cache-control"] == "no-store"
    card_body = card.json()
    assert card_body["plant_id"] == str(seed.plant_id)
    assert card_body["farm_id"] == str(seed.farm_id)
    assert card_body["status"] == "active"
    assert card_body["retained_history_mode"] == "active_history"
    assert card_body["permissions"]["can_read"] is True
    assert card_body["permissions"]["can_operate"] is True
    assert card_body["latest_check_in_ref"] == {
        "source_type": "daily_checkin",
        "source_id": check_in_id,
    }
    assert card_body["latest_ph_ref"]["source_type"] == "manual_measurement"
    assert card_body["latest_ec_ref"]["source_type"] == "manual_measurement"
    assert card_body["photo_count"] == 1
    assert card_body["history_entry_count"] >= 3

    history = client.get(
        f"/api/plants/{seed.plant_id}/history?limit=100",
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft006-list-active"},
    )
    assert history.status_code == 200
    assert history.headers["cache-control"] == "no-store"
    body = history.json()
    assert body["next_cursor"] is None
    source_types = {item["source_type"] for item in body["items"]}
    assert {
        "daily_checkin",
        "manual_measurement",
        "photo_catalog_item",
    } <= source_types
    assert {item["authority_source"] for item in body["items"]} == {
        "postgresql_read_model"
    }

    photo_entry = _entry(body["items"], "photo_catalog_item", photo_id)
    assert photo_entry["artifact_refs"]["original_file_ref"].startswith("plants/")
    assert photo_entry["event_refs"]["photo_accepted"]["event_type"] == (
        "photo_accepted"
    )
    measurement_entry = next(
        item for item in body["items"] if item["source_type"] == "manual_measurement"
    )
    assert measurement_entry["event_refs"]["manual_measurement_recorded"][
        "event_type"
    ] == "manual_measurement_recorded"
    assert measurement_entry["summary"]["has_ph"] is True
    assert measurement_entry["summary"]["has_ec"] is True

    timeline_text = (timeline_root / "timeline.jsonl").read_text(encoding="utf-8")
    evidence = card.text + history.text + timeline_text
    assert "synthetic-test-token" not in evidence
    assert str(artifact_root) not in evidence
    assert str(timeline_root) not in evidence


def test_ft006_bhv002_archived_retained_history_keeps_no_operational_authority(
    history_api_runtime,
):
    client, _database, seed, _artifact_root, _timeline_root = history_api_runtime
    _create_check_in_and_photo(client, seed)

    archived = client.post(
        f"/api/plants/{seed.plant_id}/archive",
        cookies=_cookies(seed.boss),
        headers={"x-request-id": "req-ft006-archive"},
    )
    assert archived.status_code == 200
    assert archived.headers["cache-control"] == "no-store"

    for actor in (seed.boss, seed.engineer, seed.consultant):
        card = client.get(
            f"/api/plants/{seed.plant_id}/history/card",
            cookies=_cookies(actor),
        )
        assert card.status_code == 200
        assert card.headers["cache-control"] == "no-store"
        body = card.json()
        assert body["status"] == "archived"
        assert body["retained_history_mode"] == "archived_retained_history"
        assert body["permissions"]["can_read"] is True
        assert body["permissions"]["can_comment"] is True
        assert body["permissions"]["can_operate"] is False
        assert body["permissions"]["can_create_domain_tasks"] is False
        assert body["permissions"]["can_approve_actions"] is False

        history = client.get(
            f"/api/plants/{seed.plant_id}/history",
            cookies=_cookies(actor),
        )
        assert history.status_code == 200
        assert history.json()["items"]
        assert "plant_admin_audit" in {
            item["source_type"] for item in history.json()["items"]
        }

    denied_write = client.post(
        f"/api/plants/{seed.plant_id}/operations/check-ins",
        json={
            "observation_state": "observed",
            "observation_text": "Archived write attempt",
        },
        cookies=_cookies(seed.boss),
        headers={"x-request-id": "req-ft006-archived-write-denied"},
    )
    assert denied_write.status_code == 404
    assert denied_write.headers["cache-control"] == "no-store"
    assert denied_write.json()["error"]["code"] == "AUTH_PLANT_FORBIDDEN"


def test_history_denials_are_no_store_and_do_not_leak_existence(
    history_api_runtime,
):
    client, _database, seed, _artifact_root, _timeline_root = history_api_runtime
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
            f"/api/plants/{plant_id}/history/card",
            cookies=_cookies(actor),
            headers={"x-request-id": f"req-ft006-denied-{expected_code.lower()}"},
        )
        assert response.status_code == expected_status
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["error"]["code"] == expected_code
        if expected_code == "AUTH_PLANT_FORBIDDEN":
            assert str(plant_id) not in response.text


def test_history_query_validation_pagination_source_filter_and_redaction(
    history_api_runtime,
):
    client, database, seed, _artifact_root, _timeline_root = history_api_runtime
    check_in_id, _photo_id = _create_check_in_and_photo(client, seed)
    with database.session() as session, session.begin():
        check_in = session.get(DailyCheckIn, uuid.UUID(check_in_id))
        check_in.source_refs = {
            **check_in.source_refs,
            "session_id": "leaky-session",
            "absolute_path": "/home/serg/private/history.sql",
            "safe_note": "operator attached path /home/serg/private/history.sql",
            "windows_note": r"operator attached C:\Users\serg\private\history.sql",
        }

    first_page = client.get(
        f"/api/plants/{seed.plant_id}/history?limit=2",
        cookies=_cookies(seed.engineer),
    )
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert len(first_body["items"]) == 2
    assert first_body["next_cursor"] is not None

    second_page = client.get(
        f"/api/plants/{seed.plant_id}/history?limit=100"
        f"&cursor={first_body['next_cursor']}",
        cookies=_cookies(seed.engineer),
    )
    assert second_page.status_code == 200
    assert {item["history_entry_id"] for item in first_body["items"]}.isdisjoint(
        {item["history_entry_id"] for item in second_page.json()["items"]}
    )

    measurements = client.get(
        f"/api/plants/{seed.plant_id}/history?source_type=manual_measurement",
        cookies=_cookies(seed.engineer),
    )
    assert measurements.status_code == 200
    assert {item["source_type"] for item in measurements.json()["items"]} == {
        "manual_measurement"
    }

    redaction_payload = first_page.text + second_page.text + measurements.text
    assert "safe_note" in redaction_payload
    assert "leaky-session" not in redaction_payload
    assert "/home/serg" not in redaction_payload
    assert r"C:\\Users\\serg" not in redaction_payload

    validation_cases = [
        (
            f"/api/plants/{seed.plant_id}/history/card?unexpected=1",
            "VALIDATION_FAILED",
        ),
        (
            f"/api/plants/{seed.plant_id}/history?unexpected=1",
            "VALIDATION_FAILED",
        ),
        (
            f"/api/plants/{seed.plant_id}/history?limit=0",
            "HISTORY_LIMIT_INVALID",
        ),
        (
            f"/api/plants/{seed.plant_id}/history?limit=101",
            "HISTORY_LIMIT_INVALID",
        ),
        (
            f"/api/plants/{seed.plant_id}/history?limit=not-an-int",
            "HISTORY_LIMIT_INVALID",
        ),
        (
            f"/api/plants/{seed.plant_id}/history?source_type=agent_output",
            "HISTORY_SOURCE_TYPE_INVALID",
        ),
        (
            f"/api/plants/{seed.plant_id}/history?cursor=not-a-cursor",
            "HISTORY_CURSOR_INVALID",
        ),
    ]
    for path, code in validation_cases:
        response = client.get(
            path,
            cookies=_cookies(seed.engineer),
            headers={"x-request-id": f"req-ft006-{code.lower()}"},
        )
        assert response.status_code == 422
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["error"]["code"] == code


def test_postgresql_http_response_redaction_and_cursor_canonicality(
    postgres_history_api_runtime,
):
    client, database, seed = postgres_history_api_runtime
    check_in_id, photo_id = _create_check_in_and_photo(client, seed)
    safe_relative_ref = (
        f"plants/{seed.plant_id}/photos/{photo_id}/original.jpg"
    )
    complete_url = (
        "https://example.test/history:detail/section"
        "?next=/private/history&ref=source:/nested#view:/fragment"
    )
    ambiguous_url = (
        "https://example.test/evidence,source:/private/history/value.txt"
    )
    obvious_path_values = {
        "posix_note": "Inspection source /private/history/value.txt",
        "drive_note": r"Inspection source D:\private\history\value.txt",
        "unc_note": r"Inspection source \\history-host\private\value.txt",
        "file_uri_note": "Inspection source file:///private/history/value.txt",
    }
    unsafe_keys = {
        "/private/history/key",
        r"C:\private\history\key",
        r"\\history-host\private\key",
        "file:///private/history/key",
    }
    secret_bearing_keys = (
        "https://history-user:synthetic-userinfo@example.test/history",
        "trace Authorization: Bearer synthetic-bearer-material",
        "trace Basic synthetic-basic-material",
    )
    with database.session() as session, session.begin():
        check_in = session.get(DailyCheckIn, uuid.UUID(check_in_id))
        assert check_in is not None
        check_in.source_refs = {
            **check_in.source_refs,
            "safe_relative_ref": safe_relative_ref,
            "complete_url": complete_url,
            "ambiguous_url": ambiguous_url,
            **{key: "must be omitted" for key in secret_bearing_keys},
            complete_url: "preserved direct URL key",
            "nested": {
                **obvious_path_values,
                **{key: "must be omitted" for key in unsafe_keys},
                **{key: "must be omitted" for key in secret_bearing_keys},
                ambiguous_url: "preserved nested URL key",
                **{
                    f"sample_text_{index}": value
                    for index, value in enumerate(secret_bearing_keys)
                },
                "safe_url_value": complete_url,
            },
        }

    for unsafe_display_name in (
        "/private/history/card.txt",
        "Inspection source /private/history/card.txt",
        r"D:\private\history\card.txt",
        r"\\history-host\private\card.txt",
        "file:///private/history/card.txt",
    ):
        renamed = client.patch(
            f"/api/plants/{seed.plant_id}",
            json={"display_name": unsafe_display_name},
            cookies=_cookies(seed.engineer),
        )
        assert renamed.status_code == 200
        unsafe_card = client.get(
            f"/api/plants/{seed.plant_id}/history/card",
            cookies=_cookies(seed.engineer),
        )
        assert unsafe_card.status_code == 200
        assert unsafe_card.json()["display_name"] == "***"
    for safe_display_name in (complete_url, ambiguous_url):
        renamed = client.patch(
            f"/api/plants/{seed.plant_id}",
            json={"display_name": safe_display_name},
            cookies=_cookies(seed.engineer),
        )
        assert renamed.status_code == 200
        safe_card = client.get(
            f"/api/plants/{seed.plant_id}/history/card",
            cookies=_cookies(seed.engineer),
        )
        assert safe_card.status_code == 200
        assert safe_card.json()["display_name"] == safe_display_name

    card = client.get(
        f"/api/plants/{seed.plant_id}/history/card",
        cookies=_cookies(seed.engineer),
    )
    history = client.get(
        f"/api/plants/{seed.plant_id}/history",
        params={"limit": 100},
        cookies=_cookies(seed.engineer),
    )
    assert card.status_code == 200
    assert history.status_code == 200
    assert card.json()["display_name"] == ambiguous_url
    history_body = history.json()
    check_in_entry = _entry(history_body["items"], "daily_checkin", check_in_id)
    projected_refs = check_in_entry["source_refs"]["source_refs"]
    assert projected_refs["safe_relative_ref"] == safe_relative_ref
    assert projected_refs["complete_url"] == complete_url
    assert projected_refs["ambiguous_url"] == ambiguous_url
    assert projected_refs[complete_url] == "preserved direct URL key"
    assert all(key not in projected_refs for key in secret_bearing_keys)
    nested = projected_refs["nested"]
    assert {nested[name] for name in obvious_path_values} == {"***"}
    assert nested[ambiguous_url] == "preserved nested URL key"
    assert nested["safe_url_value"] == complete_url
    assert all(key not in nested for key in secret_bearing_keys)
    assert all(
        nested[f"sample_text_{index}"] != value
        and "***" in nested[f"sample_text_{index}"]
        for index, value in enumerate(secret_bearing_keys)
    )
    assert unsafe_keys.isdisjoint(nested)
    keys, strings = _mapping_keys_and_string_values([card.json(), history_body])
    assert unsafe_keys.isdisjoint(keys)
    assert safe_relative_ref in strings
    assert complete_url in strings
    assert ambiguous_url in strings
    assert complete_url in keys
    assert ambiguous_url in keys
    assert all(key not in keys for key in secret_bearing_keys)
    assert all(value not in strings for value in secret_bearing_keys)

    first_page = client.get(
        f"/api/plants/{seed.plant_id}/history",
        params={"limit": 1},
        cookies=_cookies(seed.engineer),
    )
    assert first_page.status_code == 200
    canonical_cursor = first_page.json()["next_cursor"]
    assert canonical_cursor is not None
    continued = client.get(
        f"/api/plants/{seed.plant_id}/history",
        params={"cursor": canonical_cursor},
        cookies=_cookies(seed.engineer),
    )
    assert continued.status_code == 200
    assert continued.json()["items"]

    payload = _decoded_cursor_payload(canonical_cursor)
    malformed = [
        f"!{canonical_cursor}",
        f"{canonical_cursor[:4]} {canonical_cursor[4:]}",
        f"{canonical_cursor}=",
        _encoded_cursor_payload({**payload, "v": 2}),
        _encoded_cursor_payload({**payload, "extra": True}),
        _encoded_cursor_payload(
            {key: value for key, value in payload.items() if key != "source_id"}
        ),
        _encoded_cursor_payload({**payload, "occurred_at": "not-a-timestamp"}),
        _encoded_cursor_payload({**payload, "source_type": "agent_output"}),
        _encoded_cursor_payload({**payload, "source_id": "not-a-uuid"}),
        _encoded_cursor_payload(payload, canonical_json=False),
    ]
    for index, cursor in enumerate(malformed):
        request_id = f"req-ft006-cursor-invalid-{index}"
        response = client.get(
            f"/api/plants/{seed.plant_id}/history",
            params={"cursor": cursor},
            cookies=_cookies(seed.engineer),
            headers={"x-request-id": request_id},
        )
        assert response.status_code == 422
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "error": {
                "code": "HISTORY_CURSOR_INVALID",
                "message": "History cursor is invalid.",
                "request_id": request_id,
            }
        }


def test_actor_context_stops_before_projection_reads_and_errors_are_stable(
    history_api_runtime,
    monkeypatch,
):
    client, _database, seed, _artifact_root, _timeline_root = history_api_runtime

    class ExplodingService:
        def __init__(self, *_args, **_kwargs) -> None:
            raise AssertionError("history service must not run before ActorContext")

    monkeypatch.setattr("backend.app.api.history.PlantHistoryService", ExplodingService)
    unauthenticated = client.get(f"/api/plants/{seed.plant_id}/history/card")
    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["cache-control"] == "no-store"
    assert unauthenticated.json()["error"]["code"] == "AUTH_SESSION_REQUIRED"

    class RawFailingService:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def get_card(self, *_args, **_kwargs):
            raise RuntimeError("postgresql://admin:secret@localhost/raw sql")

    monkeypatch.setattr("backend.app.api.history.PlantHistoryService", RawFailingService)
    failed = client.get(
        f"/api/plants/{seed.plant_id}/history/card",
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft006-history-persistence-failed"},
    )
    assert failed.status_code == 500
    assert failed.headers["cache-control"] == "no-store"
    assert failed.json()["error"] == {
        "code": "HISTORY_PERSISTENCE_FAILED",
        "message": "Plant history could not be read.",
        "request_id": "req-ft006-history-persistence-failed",
    }
    assert "secret" not in failed.text
    assert "raw sql" not in failed.text


def test_generated_openapi_contains_ft006_history_contracts():
    database = build_database(AppSettings(database_url="sqlite+pysqlite:///:memory:"))
    try:
        schema = create_app(database=database).openapi()
    finally:
        database.dispose()

    paths = schema["paths"]
    assert {
        "/api/plants/{plant_id}/history/card",
        "/api/plants/{plant_id}/history",
    } <= set(paths)
    assert {"get"} <= set(paths["/api/plants/{plant_id}/history/card"])
    assert {"get"} <= set(paths["/api/plants/{plant_id}/history"])

    history_get = paths["/api/plants/{plant_id}/history"]["get"]
    assert set(history_get["responses"]) >= {"200", "401", "403", "404", "422", "500"}
    query_params = {
        parameter["name"]: parameter
        for parameter in history_get["parameters"]
        if parameter["in"] == "query"
    }
    assert set(query_params) == {"cursor", "limit", "source_type"}
    assert query_params["limit"]["schema"]["default"] == 50
    assert query_params["limit"]["schema"]["minimum"] == 1
    assert query_params["limit"]["schema"]["maximum"] == 100
    assert set(query_params["source_type"]["schema"]["enum"]) == {
        "plant_admin_audit",
        "daily_checkin",
        "manual_measurement",
        "photo_catalog_item",
    }

    schemas = schema["components"]["schemas"]
    assert set(schemas["PlantHistoryCardResponse"]["properties"]) == {
        "plant_id",
        "farm_id",
        "plant_key",
        "display_name",
        "status",
        "permissions",
        "latest_check_in_ref",
        "latest_ph_ref",
        "latest_ec_ref",
        "latest_ph",
        "latest_ec_ms_cm",
        "ph_fresh_for_analysis",
        "ec_fresh_for_analysis",
        "photo_count",
        "history_entry_count",
        "retained_history_mode",
        "computed_at",
    }
    assert set(schemas["PlantHistoryEntryResponse"]["properties"]) == {
        "history_entry_id",
        "farm_id",
        "plant_id",
        "source_type",
        "source_id",
        "occurred_at",
        "recorded_at",
        "actor_ref",
        "summary",
        "source_refs",
        "event_refs",
        "artifact_refs",
        "authority_source",
    }
    assert set(schemas["PlantHistoryListResponse"]["properties"]) == {
        "items",
        "next_cursor",
    }


def _create_check_in_and_photo(
    client: TestClient,
    seed: HistoryApiSeed,
) -> tuple[str, str]:
    check_in = client.post(
        f"/api/plants/{seed.plant_id}/operations/check-ins",
        json={
            "observation_state": "observed",
            "observation_text": "History API observation",
            "measurement": {"ph": "6.50", "ec_ms_cm": "1.250"},
        },
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft006-create-check-in"},
    )
    assert check_in.status_code == 201
    check_in_id = check_in.json()["check_in_id"]
    photo = client.post(
        f"/api/plants/{seed.plant_id}/photos",
        data={
            "photo_type": "leaf_closeup",
            "check_in_id": check_in_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
        files={"file": ("photo.jpg", JPEG_BYTES, "image/jpeg")},
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft006-upload-photo"},
    )
    assert photo.status_code == 201
    return check_in_id, photo.json()["photo_id"]


def _photo_paths(database, artifact_root: Path, photo_id: str) -> tuple[Path, Path]:
    with database.session() as session:
        item = session.get(PhotoCatalogItem, uuid.UUID(photo_id))
        assert item is not None
        return artifact_root / item.original_file_ref, artifact_root / item.manifest_ref


def _entry(items: list[dict[str, object]], source_type: str, source_id: str):
    return next(
        item
        for item in items
        if item["source_type"] == source_type and item["source_id"] == source_id
    )


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


def _mapping_keys_and_string_values(value: object) -> tuple[set[str], list[str]]:
    keys: set[str] = set()
    strings: list[str] = []

    def visit(item: object) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                keys.add(str(key))
                visit(nested)
        elif isinstance(item, list | tuple):
            for nested in item:
                visit(nested)
        elif isinstance(item, str):
            strings.append(item)

    visit(value)
    return keys, strings


def _cookies(actor: ActorSeed) -> dict[str, str]:
    return {"agro_intellect_session": actor.token}


def _seed(database, *, include_wrong_farm_plant: bool = True) -> HistoryApiSeed:
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
            plant_key="boss_history_001",
            display_name="Boss History 001",
            status="active",
        )
        revoked_plant = Plant(
            farm_id=farm.farm_id,
            plant_key="revoked_history_001",
            display_name="Revoked History 001",
            status="active",
        )
        archived_no_grant_plant = Plant(
            farm_id=farm.farm_id,
            plant_key="archived_history_001",
            display_name="Archived History 001",
            status="archived",
        )
        wrong_farm_plant = Plant(
            plant_id=uuid.uuid4(),
            farm_id=uuid.uuid4(),
            plant_key="wrong_history_001",
            display_name="Wrong History 001",
            status="active",
        )
        plants = [
            plant,
            boss_only_plant,
            revoked_plant,
            archived_no_grant_plant,
        ]
        if include_wrong_farm_plant:
            plants.append(wrong_farm_plant)
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
                login_name=f"ft006-{name}",
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
        session.commit()

    return HistoryApiSeed(
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        boss_only_plant_id=boss_only_plant.plant_id,
        revoked_plant_id=revoked_plant.plant_id,
        archived_no_grant_plant_id=archived_no_grant_plant.plant_id,
        wrong_farm_plant_id=wrong_farm_plant.plant_id,
        boss=actors["boss"],
        engineer=actors["engineer"],
        consultant=actors["consultant"],
        disabled=actors["disabled"],
    )
