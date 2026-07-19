from __future__ import annotations

import base64
import json
import uuid

from fastapi.testclient import TestClient

from backend.app.access_admin.dependencies import require_actor_context
from backend.app.main import create_app
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_active_plant,
    create_actor,
    grant_access,
)
from tests.backend.plant_state.conftest import ft009_database, ft009_seed  # noqa: F401
from tests.backend.plant_state.test_service import _persist, _vision_handoff


SAFE_FIELDS = {
    "state_record_id",
    "plant_id",
    "record_kind",
    "agent_id",
    "observation_key",
    "polarity",
    "severity",
    "assessment_kind",
    "direction",
    "summary",
    "confidence",
    "trust_status",
    "source_refs",
    "observed_at",
    "recorded_at",
    "confirmation_source",
    "confirmed_at",
    "version",
}


def test_plant_state_openapi_exact_protected_contract():
    schema = create_app().openapi()
    list_operation = schema["paths"]["/api/plants/{plant_id}/state-records"]["get"]
    review_operation = schema["paths"][
        "/api/plants/{plant_id}/state-records/{state_record_id}/review"
    ]["post"]
    assert {item["name"] for item in list_operation["parameters"]} >= {
        "plant_id",
        "cursor",
        "limit",
    }
    assert {"200", "401", "403", "404", "409", "422", "500"}.issubset(
        review_operation["responses"]
    )
    properties = schema["components"]["schemas"]["PlantStateRecordResponse"][
        "properties"
    ]
    assert set(properties) == SAFE_FIELDS
    for forbidden in (
        "farm_id",
        "run_id",
        "message_id",
        "confirmed_by_account_id",
        "confirmed_by_membership_id",
        "classifier_version",
        "provider",
        "model_ref",
        "authorization_scope",
    ):
        assert forbidden not in properties


def test_list_review_no_store_exact_fields_and_validation(
    ft009_database,
    ft009_seed,
):
    _farm, boss, plant = ft009_seed
    first = _persist(ft009_database, boss, _vision_handoff(boss, plant))
    _persist(
        ft009_database,
        boss,
        _vision_handoff(boss, plant, observation_key="leaf_color_change"),
    )
    app = create_app(database=ft009_database)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        unauthenticated = client.get(f"/api/plants/{plant.plant_id}/state-records")
        assert unauthenticated.status_code == 401
        assert unauthenticated.headers["cache-control"] == "no-store"

        app.dependency_overrides[require_actor_context] = lambda: boss
        listed = client.get(
            f"/api/plants/{plant.plant_id}/state-records?limit=1"
        )
        assert listed.status_code == 200
        assert listed.headers["cache-control"] == "no-store"
        assert set(listed.json()) == {"items", "next_cursor"}
        assert set(listed.json()["items"][0]) == SAFE_FIELDS
        assert listed.json()["next_cursor"]
        assert "confirmed_by_account_id" not in listed.text
        assert "message_id" not in listed.text

        reviewed = client.post(
            f"/api/plants/{plant.plant_id}/state-records/{first.state_record_id}/review",
            json={"decision": "reject", "expected_version": 1},
        )
        assert reviewed.status_code == 200
        assert reviewed.headers["cache-control"] == "no-store"
        assert reviewed.json()["trust_status"] == "rejected"
        assert reviewed.json()["version"] == 2

        invalid_cases = (
            (
                "get",
                f"/api/plants/{plant.plant_id}/state-records?limit=01",
                None,
                "PLANT_STATE_LIMIT_INVALID",
            ),
            (
                "get",
                f"/api/plants/{plant.plant_id}/state-records?unknown=1",
                None,
                "VALIDATION_FAILED",
            ),
            (
                "post",
                f"/api/plants/{plant.plant_id}/state-records/{first.state_record_id}/review",
                {"decision": "confirm", "expected_version": 2, "trust_status": "confirmed"},
                "VALIDATION_FAILED",
            ),
        )
        for method, path, payload, code in invalid_cases:
            response = getattr(client, method)(path, json=payload) if payload else getattr(client, method)(path)
            assert response.status_code == 422
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["error"]["code"] == code


def test_wrong_plant_cursor_no_enumeration_consultant_and_archive_retention(
    ft009_database,
    ft009_seed,
):
    farm, boss, plant = ft009_seed
    _persist(ft009_database, boss, _vision_handoff(boss, plant))
    _persist(
        ft009_database,
        boss,
        _vision_handoff(boss, plant, observation_key="leaf_color_change"),
    )
    other = create_active_plant(
        ft009_database,
        boss,
        plant_key=f"other_{uuid.uuid4().hex[:8]}",
    )
    consultant, membership = create_actor(ft009_database, farm, "consultant")
    grant_access(
        ft009_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    app = create_app(database=ft009_database)
    app.dependency_overrides[require_actor_context] = lambda: boss
    with TestClient(app, base_url="http://127.0.0.1") as client:
        first_page = client.get(
            f"/api/plants/{plant.plant_id}/state-records?limit=1"
        )
        cursor = first_page.json()["next_cursor"]
        wrong = client.get(
            f"/api/plants/{other.plant_id}/state-records?cursor={cursor}"
        )
        assert wrong.status_code == 422
        assert wrong.json()["error"]["code"] == "VALIDATION_FAILED"

        decoded = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        noncanonical = base64.urlsafe_b64encode(
            json.dumps(json.loads(decoded), ensure_ascii=True).encode("ascii")
        ).decode("ascii").rstrip("=")
        wrong_type_payload = json.loads(decoded)
        wrong_type_payload["recorded_at"] = 123
        wrong_type = base64.urlsafe_b64encode(
            json.dumps(wrong_type_payload, separators=(",", ":")).encode("ascii")
        ).decode("ascii").rstrip("=")
        for invalid_cursor in (
            "",
            "a",
            "not-a-cursor",
            cursor + "=",
            noncanonical,
            wrong_type,
        ):
            invalid = client.get(
                f"/api/plants/{plant.plant_id}/state-records",
                params={"cursor": invalid_cursor},
            )
            assert invalid.status_code == 422
            assert invalid.headers["cache-control"] == "no-store"
            assert invalid.json()["error"]["code"] == "VALIDATION_FAILED"
        missing = client.post(
            f"/api/plants/{plant.plant_id}/state-records/{uuid.uuid4()}/review",
            json={"decision": "reject", "expected_version": 1},
        )
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "PLANT_STATE_NOT_FOUND"

        app.dependency_overrides[require_actor_context] = lambda: consultant
        denied = client.post(
            f"/api/plants/{plant.plant_id}/state-records/{first_page.json()['items'][0]['state_record_id']}/review",
            json={"decision": "reject", "expected_version": 1},
        )
        assert denied.status_code == 404
        assert denied.json()["error"]["code"] == "AUTH_PLANT_FORBIDDEN"

        archive_plant(ft009_database, boss, plant_id=plant.plant_id)
        app.dependency_overrides[require_actor_context] = lambda: boss
        retained = client.get(f"/api/plants/{plant.plant_id}/state-records")
        assert retained.status_code == 200
        assert len(retained.json()["items"]) == 2
        archived_review = client.post(
            f"/api/plants/{plant.plant_id}/state-records/{first_page.json()['items'][0]['state_record_id']}/review",
            json={"decision": "reject", "expected_version": 1},
        )
        assert archived_review.status_code == 404
        assert archived_review.json()["error"]["code"] == "AUTH_PLANT_FORBIDDEN"


def test_list_authorization_denial_precedes_invalid_cursor_decode(
    ft009_database,
    ft009_seed,
):
    farm, _boss, plant = ft009_seed
    unauthorized, _membership = create_actor(ft009_database, farm, "engineer")
    app = create_app(database=ft009_database)
    app.dependency_overrides[require_actor_context] = lambda: unauthorized
    with TestClient(app, base_url="http://127.0.0.1") as client:
        denied = client.get(
            f"/api/plants/{plant.plant_id}/state-records",
            params={"cursor": "not-a-cursor"},
        )
    assert denied.status_code == 404
    assert denied.headers["cache-control"] == "no-store"
    assert denied.json()["error"]["code"] == "AUTH_PLANT_FORBIDDEN"


def test_plant_state_api_persistence_failure_is_redacted_no_store(
    ft009_database,
    ft009_seed,
):
    _farm, boss, plant = ft009_seed
    app = create_app(database=ft009_database)
    app.dependency_overrides[require_actor_context] = lambda: boss

    class _FailingDatabase:
        def session(self):
            raise RuntimeError("database secret must not escape")

    app.state.database = _FailingDatabase()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get(f"/api/plants/{plant.plant_id}/state-records")
    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"]["code"] == "PLANT_STATE_PERSISTENCE_FAILED"
    assert "secret" not in response.text
