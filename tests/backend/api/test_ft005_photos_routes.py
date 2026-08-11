from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
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
from backend.app.photo_intake import (
    MAX_UPLOAD_BYTES,
    PhotoCatalogItem,
    PhotoIntakeError,
    PhotoIntakeErrorCode,
)
from backend.app.plant_operations import DailyCheckIn, ManualMeasurement


_REGISTERED_MODELS = (DailyCheckIn, ManualMeasurement)
JPEG_BYTES = b"\xff\xd8\xff\xe0ft005-api-jpeg"
PNG_BYTES = b"\x89PNG\r\n\x1a\nft005-api-png"
WEBP_BYTES = b"RIFF\x14\x00\x00\x00WEBPVP8 ft005"


@dataclass(frozen=True)
class ActorSeed:
    account_id: uuid.UUID
    membership_id: uuid.UUID
    token: str


@dataclass(frozen=True)
class PhotoApiSeed:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    boss_only_plant_id: uuid.UUID
    revoked_plant_id: uuid.UUID
    archived_plant_id: uuid.UUID
    boss: ActorSeed
    engineer: ActorSeed
    consultant: ActorSeed
    disabled: ActorSeed


@pytest.fixture
def photo_api_runtime(tmp_path: Path):
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


def test_ft005_bhv001_engineer_uploads_and_catalog_reads_from_db(
    photo_api_runtime,
):
    client, database, seed, artifact_root, timeline_root = photo_api_runtime
    check_in = client.post(
        f"/api/plants/{seed.plant_id}/operations/check-ins",
        json={
            "observation_state": "observed",
            "observation_text": "Photo intake check-in",
            "measurement": {"ph": "6.50"},
        },
        cookies=_cookies(seed.engineer),
    )
    assert check_in.status_code == 201
    check_in_id = check_in.json()["check_in_id"]

    captured_at = datetime.now(timezone.utc).replace(microsecond=0)
    response = _upload(
        client,
        seed.plant_id,
        seed.engineer,
        data={
            "photo_type": "leaf_closeup",
            "captured_at": captured_at.isoformat(),
            "check_in_id": check_in_id,
        },
        filename="../../leaky-name.jpg",
        request_id="req-ft005-bhv001",
    )
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    photo_id = uuid.UUID(body["photo_id"])
    assert body["farm_id"] == str(seed.farm_id)
    assert body["plant_id"] == str(seed.plant_id)
    assert body["photo_type"] == "leaf_closeup"
    assert body["check_in_id"] == check_in_id
    assert body["content_type"] == "image/jpeg"
    assert body["size_bytes"] == len(JPEG_BYTES)
    assert body["sha256"] == hashlib.sha256(JPEG_BYTES).hexdigest()
    assert body["original_file_ref"] == (
        f"plants/{seed.plant_id}/photos/{photo_id}/original.jpg"
    )
    assert body["manifest_ref"] == (
        f"plants/{seed.plant_id}/photos/{photo_id}/manifest.initial_capture.json"
    )
    assert body["event_refs"]["photo_accepted"]["event_type"] == "photo_accepted"
    assert body["source_refs"]["check_in_id"] == check_in_id
    assert body["local_only"] is True
    assert body["can_train_on"] is False

    original_path = artifact_root / body["original_file_ref"]
    manifest_path = artifact_root / body["manifest_ref"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    timeline_text = (timeline_root / "timeline.jsonl").read_text(encoding="utf-8")
    assert original_path.read_bytes() == JPEG_BYTES
    assert manifest["photo"]["photo_id"] == body["photo_id"]
    assert manifest["file"]["sha256"] == body["sha256"]
    assert "photo_accepted" in timeline_text
    serialized_evidence = response.text + timeline_text + json.dumps(manifest)
    assert "leaky-name" not in serialized_evidence
    assert str(artifact_root) not in serialized_evidence

    original_path.unlink()
    manifest_path.unlink()
    listed = client.get(
        f"/api/plants/{seed.plant_id}/photos",
        cookies=_cookies(seed.engineer),
    )
    detail = client.get(
        f"/api/plants/{seed.plant_id}/photos/{photo_id}",
        cookies=_cookies(seed.boss),
    )
    assert listed.status_code == 200
    assert listed.headers["cache-control"] == "no-store"
    assert listed.json()["items"][0]["photo_id"] == body["photo_id"]
    assert listed.json()["next_cursor"] is None
    assert detail.status_code == 200
    assert detail.headers["cache-control"] == "no-store"
    assert detail.json()["photo_id"] == body["photo_id"]
    assert _photo_count(database) == 1


def test_catalog_http_keyset_enumerates_every_row_and_terminates(
    photo_api_runtime,
):
    client, database, seed, _artifact_root, _timeline_root = photo_api_runtime
    photo_ids = [
        uuid.UUID(
            _upload(
                client,
                seed.plant_id,
                seed.engineer,
                request_id=f"req-ft005-page-seed-{index}",
            ).json()["photo_id"]
        )
        for index in range(4)
    ]
    ordered_ids = sorted(photo_ids)
    base = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)
    expected = [ordered_ids[2], ordered_ids[0], ordered_ids[1], ordered_ids[3]]
    uploaded_at_by_id = {
        expected[0]: base + timedelta(minutes=2),
        expected[1]: base + timedelta(minutes=1),
        expected[2]: base + timedelta(minutes=1),
        expected[3]: base,
    }
    with database.session() as session:
        rows = session.scalars(
            select(PhotoCatalogItem).where(PhotoCatalogItem.photo_id.in_(photo_ids))
        )
        for row in rows:
            row.uploaded_at = uploaded_at_by_id[row.photo_id]
        session.commit()

    enumerated = []
    cursors = []
    cursor = None
    while True:
        params = {"limit": 1}
        if cursor is not None:
            params["cursor"] = cursor
        response = client.get(
            f"/api/plants/{seed.plant_id}/photos",
            params=params,
            cookies=_cookies(seed.engineer),
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        page = response.json()
        assert len(page["items"]) == 1
        enumerated.append(uuid.UUID(page["items"][0]["photo_id"]))
        cursor = page["next_cursor"]
        if cursor is None:
            break
        assert "=" not in cursor
        assert cursor not in cursors
        cursors.append(cursor)

    assert enumerated == expected
    assert len(enumerated) == len(set(enumerated)) == len(photo_ids)
    assert len(cursors) == len(photo_ids) - 1


def test_catalog_http_rejects_invalid_cursors_after_authorization(
    photo_api_runtime,
):
    client, _database, seed, _artifact_root, _timeline_root = photo_api_runtime
    for index in range(2):
        response = _upload(
            client,
            seed.plant_id,
            seed.engineer,
            request_id=f"req-ft005-cursor-seed-{index}",
        )
        assert response.status_code == 201
    first_page = client.get(
        f"/api/plants/{seed.plant_id}/photos",
        params={"limit": 1},
        cookies=_cookies(seed.engineer),
    )
    assert first_page.status_code == 200
    valid_cursor = first_page.json()["next_cursor"]
    assert valid_cursor is not None
    payload = _decode_catalog_cursor_payload(valid_cursor)

    invalid_cursors = [
        "",
        "not+base64url",
        valid_cursor + "=",
        _raw_catalog_cursor(payload, canonical=False),
        _raw_catalog_cursor({**payload, "v": 2}),
        _raw_catalog_cursor({key: value for key, value in payload.items() if key != "photo_id"}),
        _raw_catalog_cursor({**payload, "uploaded_at": "not-a-timestamp"}),
        _raw_catalog_cursor({**payload, "photo_id": "not-a-uuid"}),
        _raw_catalog_cursor({**payload, "plant_id": str(seed.boss_only_plant_id)}),
    ]
    for index, cursor in enumerate(invalid_cursors):
        response = client.get(
            f"/api/plants/{seed.plant_id}/photos",
            params={"cursor": cursor, "limit": 1},
            cookies=_cookies(seed.engineer),
            headers={"x-request-id": f"req-ft005-bad-cursor-{index}"},
        )
        assert response.status_code == 422
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["error"] == {
            "code": "VALIDATION_FAILED",
            "message": "Request validation failed.",
            "request_id": f"req-ft005-bad-cursor-{index}",
        }

    unauthorized = client.get(
        f"/api/plants/{seed.boss_only_plant_id}/photos",
        params={"cursor": "not+base64url", "limit": 1},
        cookies=_cookies(seed.engineer),
    )
    assert unauthorized.status_code == 404
    assert unauthorized.json()["error"]["code"] == "AUTH_PLANT_FORBIDDEN"


@pytest.mark.parametrize(
    ("content", "content_type", "extension"),
    [
        (JPEG_BYTES, "image/jpeg", "jpg"),
        (PNG_BYTES, "image/png", "png"),
        (WEBP_BYTES, "image/webp", "webp"),
    ],
)
def test_boss_upload_accepts_supported_content_types(
    photo_api_runtime,
    content,
    content_type,
    extension,
):
    client, _database, seed, _artifact_root, _timeline_root = photo_api_runtime
    response = _upload(
        client,
        seed.plant_id,
        seed.boss,
        content=content,
        content_type=content_type,
        data={"photo_type": "whole_plant"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == content_type
    assert body["original_file_ref"].endswith(f"/original.{extension}")
    assert body["local_only"] is True
    assert body["can_train_on"] is False


def test_upload_validation_errors_do_not_accept_artifacts(photo_api_runtime):
    client, database, seed, artifact_root, timeline_root = photo_api_runtime
    cases = [
        (
            client.post(
                f"/api/plants/{seed.plant_id}/photos",
                files={"photo_type": (None, "leaf_closeup")},
                cookies=_cookies(seed.engineer),
                headers={"x-request-id": "req-ft005-missing-file"},
            ),
            422,
            "UPLOAD_FILE_REQUIRED",
        ),
        (
            _upload(
                client,
                seed.plant_id,
                seed.engineer,
                content=b"plain text",
                content_type="text/plain",
                request_id="req-ft005-unsupported",
            ),
            415,
            "UNSUPPORTED_MEDIA_TYPE",
        ),
        (
            _upload(
                client,
                seed.plant_id,
                seed.engineer,
                data={"photo_type": "bad_type"},
                request_id="req-ft005-bad-type",
            ),
            422,
            "PHOTO_TYPE_INVALID",
        ),
        (
            _upload(
                client,
                seed.plant_id,
                seed.engineer,
                content=b"x" * (MAX_UPLOAD_BYTES + 1),
                request_id="req-ft005-too-large",
            ),
            413,
            "UPLOAD_TOO_LARGE",
        ),
        (
            _upload(
                client,
                seed.plant_id,
                seed.engineer,
                data={"photo_type": "leaf_closeup", "check_in_id": "not-a-uuid"},
                request_id="req-ft005-bad-check-in-format",
            ),
            422,
            "VALIDATION_FAILED",
        ),
        (
            _upload(
                client,
                seed.plant_id,
                seed.engineer,
                data={"photo_type": "leaf_closeup", "check_in_id": str(uuid.uuid4())},
                request_id="req-ft005-bad-check-in-owner",
            ),
            404,
            "AUTH_PLANT_FORBIDDEN",
        ),
    ]
    for response, expected_status, expected_code in cases:
        assert response.status_code == expected_status
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["error"]["code"] == expected_code
        assert "secret" not in response.text

    assert _photo_count(database) == 0
    assert not _has_files(artifact_root)
    assert not (timeline_root / "timeline.jsonl").exists()


@pytest.mark.parametrize(
    ("actor_name", "plant_attr", "expected_status", "expected_code"),
    [
        ("consultant", "plant_id", 404, "AUTH_PLANT_FORBIDDEN"),
        ("engineer", "boss_only_plant_id", 404, "AUTH_PLANT_FORBIDDEN"),
        ("engineer", "revoked_plant_id", 404, "AUTH_PLANT_FORBIDDEN"),
        ("disabled", "plant_id", 403, "AUTH_MEMBERSHIP_DISABLED"),
        ("boss", "archived_plant_id", 404, "AUTH_PLANT_FORBIDDEN"),
    ],
)
def test_upload_denials_are_no_leak_and_write_nothing(
    photo_api_runtime,
    actor_name,
    plant_attr,
    expected_status,
    expected_code,
):
    client, database, seed, artifact_root, timeline_root = photo_api_runtime
    actor = getattr(seed, actor_name)
    plant_id = getattr(seed, plant_attr)

    response = _upload(
        client,
        plant_id,
        actor,
        request_id=f"req-ft005-denied-{actor_name}",
    )
    assert response.status_code == expected_status
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"]["code"] == expected_code
    if expected_code == "AUTH_PLANT_FORBIDDEN":
        assert str(plant_id) not in response.text

    assert _photo_count(database) == 0
    assert not _has_files(artifact_root)
    assert not (timeline_root / "timeline.jsonl").exists()


def test_catalog_read_denials_and_photo_not_found_are_no_leak(photo_api_runtime):
    client, _database, seed, _artifact_root, _timeline_root = photo_api_runtime
    for actor, plant_id, expected_status, expected_code in (
        (seed.engineer, seed.boss_only_plant_id, 404, "AUTH_PLANT_FORBIDDEN"),
        (seed.boss, seed.archived_plant_id, 404, "AUTH_PLANT_FORBIDDEN"),
        (seed.disabled, seed.plant_id, 403, "AUTH_MEMBERSHIP_DISABLED"),
    ):
        response = client.get(
            f"/api/plants/{plant_id}/photos",
            cookies=_cookies(actor),
        )
        assert response.status_code == expected_status
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["error"]["code"] == expected_code
        if expected_code == "AUTH_PLANT_FORBIDDEN":
            assert str(plant_id) not in response.text

    missing = client.get(
        f"/api/plants/{seed.plant_id}/photos/{uuid.uuid4()}",
        cookies=_cookies(seed.engineer),
        headers={"x-request-id": "req-ft005-photo-missing"},
    )
    assert missing.status_code == 404
    assert missing.headers["cache-control"] == "no-store"
    assert missing.json()["error"] == {
        "code": "PHOTO_NOT_FOUND",
        "message": "Photo is not available.",
        "request_id": "req-ft005-photo-missing",
    }


def test_timeline_and_checksum_failures_are_safe_and_do_not_claim_success(
    photo_api_runtime,
    monkeypatch,
):
    client, database, seed, artifact_root, timeline_root = photo_api_runtime

    class FailingTimelineAppender:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def __call__(self, _event):
            raise RuntimeError("token=hidden")

    monkeypatch.setattr(
        "backend.app.api.photos.TimelineJsonlAppender",
        FailingTimelineAppender,
    )
    timeline_failed = _upload(
        client,
        seed.plant_id,
        seed.engineer,
        request_id="req-ft005-timeline-failed",
    )
    assert timeline_failed.status_code == 500
    assert timeline_failed.json()["error"] == {
        "code": "TIMELINE_APPEND_FAILED",
        "message": "Photo audit trail could not be recorded.",
        "request_id": "req-ft005-timeline-failed",
    }
    assert "hidden" not in timeline_failed.text
    assert _photo_count(database) == 0
    assert not _has_files(artifact_root)
    assert not (timeline_root / "timeline.jsonl").exists()

    class ChecksumFailingService:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def accept_photo(self, *_args, **_kwargs):
            raise PhotoIntakeError(PhotoIntakeErrorCode.PHOTO_CHECKSUM_MISMATCH)

    monkeypatch.setattr(
        "backend.app.api.photos.PhotoIntakeService",
        ChecksumFailingService,
    )
    checksum_failed = _upload(
        client,
        seed.plant_id,
        seed.engineer,
        request_id="req-ft005-checksum-failed",
    )
    assert checksum_failed.status_code == 500
    assert checksum_failed.json()["error"] == {
        "code": "PHOTO_CHECKSUM_MISMATCH",
        "message": "Photo checksum could not be verified.",
        "request_id": "req-ft005-checksum-failed",
    }
    assert _photo_count(database) == 0

    class DatasetAuditFailingService:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def accept_photo(self, *_args, **_kwargs):
            raise PhotoIntakeError(PhotoIntakeErrorCode.PHOTO_DATASET_AUDIT_FAILED)

    monkeypatch.setattr(
        "backend.app.api.photos.PhotoIntakeService",
        DatasetAuditFailingService,
    )
    dataset_audit_failed = _upload(
        client,
        seed.plant_id,
        seed.engineer,
        request_id="req-ft005-dataset-audit-failed",
    )
    assert dataset_audit_failed.status_code == 500
    assert dataset_audit_failed.headers["cache-control"] == "no-store"
    assert dataset_audit_failed.json()["error"] == {
        "code": "PHOTO_DATASET_AUDIT_FAILED",
        "message": "Photo dataset audit could not be recorded.",
        "request_id": "req-ft005-dataset-audit-failed",
    }
    assert _photo_count(database) == 0
    assert not _has_files(artifact_root)


def test_generated_openapi_contains_ft005_photo_contracts():
    database = build_database(AppSettings(database_url="sqlite+pysqlite:///:memory:"))
    try:
        schema = create_app(database=database).openapi()
    finally:
        database.dispose()

    paths = schema["paths"]
    assert {
        "/api/plants/{plant_id}/photos",
        "/api/plants/{plant_id}/photos/{photo_id}",
    } <= set(paths)
    assert {"post", "get"} <= set(paths["/api/plants/{plant_id}/photos"])
    assert {"get"} <= set(paths["/api/plants/{plant_id}/photos/{photo_id}"])
    assert (
        "multipart/form-data"
        in paths["/api/plants/{plant_id}/photos"]["post"]["requestBody"]["content"]
    )
    assert set(paths["/api/plants/{plant_id}/photos"]["post"]["responses"]) >= {
        "201",
        "401",
        "403",
        "404",
        "413",
        "415",
        "422",
        "500",
    }

    schemas = schema["components"]["schemas"]
    assert set(schemas["PhotoCatalogSummary"]["properties"]) == {
        "photo_id",
        "farm_id",
        "plant_id",
        "photo_type",
        "captured_at",
        "uploaded_at",
        "content_type",
        "size_bytes",
        "sha256",
        "original_file_ref",
        "manifest_ref",
        "check_in_id",
        "source_refs",
        "event_refs",
        "local_only",
        "can_train_on",
    }
    assert set(schemas["PhotoCatalogList"]["properties"]) == {"items", "next_cursor"}


def _upload(
    client: TestClient,
    plant_id: uuid.UUID,
    actor: ActorSeed,
    *,
    content: bytes = JPEG_BYTES,
    content_type: str = "image/jpeg",
    data: dict[str, str] | None = None,
    filename: str = "photo.jpg",
    request_id: str = "req-ft005-upload",
):
    return client.post(
        f"/api/plants/{plant_id}/photos",
        data=data or {"photo_type": "leaf_closeup"},
        files={"file": (filename, content, content_type)},
        cookies=_cookies(actor),
        headers={"x-request-id": request_id},
    )


def _cookies(actor: ActorSeed) -> dict[str, str]:
    return {"agro_intellect_session": actor.token}


def _raw_catalog_cursor(payload: dict[str, object], *, canonical: bool = True) -> str:
    raw = json.dumps(
        payload,
        separators=((",", ":") if canonical else None),
        sort_keys=canonical,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_catalog_cursor_payload(cursor: str) -> dict[str, object]:
    raw = base64.urlsafe_b64decode(cursor + ("=" * (-len(cursor) % 4)))
    payload = json.loads(raw.decode("utf-8"))
    assert isinstance(payload, dict)
    return payload


def _photo_count(database) -> int:
    with database.session() as session:
        return session.scalar(select(func.count(PhotoCatalogItem.photo_id)))


def _has_files(root: Path) -> bool:
    return root.exists() and any(path.is_file() for path in root.rglob("*"))


def _seed(database) -> PhotoApiSeed:
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
            plant_key="boss_photo_001",
            display_name="Boss Photo 001",
            status="active",
        )
        revoked_plant = Plant(
            farm_id=farm.farm_id,
            plant_key="revoked_photo_001",
            display_name="Revoked Photo 001",
            status="active",
        )
        archived_plant = Plant(
            farm_id=farm.farm_id,
            plant_key="archived_photo_001",
            display_name="Archived Photo 001",
            status="archived",
        )
        session.add_all([plant, boss_only_plant, revoked_plant, archived_plant])
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
                login_name=f"ft005-{name}",
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

    return PhotoApiSeed(
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        boss_only_plant_id=boss_only_plant.plant_id,
        revoked_plant_id=revoked_plant.plant_id,
        archived_plant_id=archived_plant.plant_id,
        boss=actors["boss"],
        engineer=actors["engineer"],
        consultant=actors["consultant"],
        disabled=actors["disabled"],
    )
