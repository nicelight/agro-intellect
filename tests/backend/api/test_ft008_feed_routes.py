from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from backend.app.access_admin.dependencies import require_actor_context
from backend.app.agent_chat import PlantFeedError, PlantFeedErrorCode, PlantFeedService, UIFeedEvent
from backend.app.api.feed import CompanionAttentionPayload, CompanionDecisionPayload
from backend.app.main import create_app
from tests.backend.agent_chat.conftest import ft008_database, ft008_seed  # noqa: F401
from tests.backend.plant_operations.conftest import create_actor
from tests.backend.safety_gate.conftest import ft011_database, ft011_seed  # noqa: F401


def test_feed_openapi_is_protected_no_store_contract():
    operation = create_app().openapi()["paths"]["/api/plants/{plant_id}/feed"]["get"]
    assert {item["name"] for item in operation["parameters"]} >= {"plant_id", "cursor", "limit"}
    assert {"200", "401", "403", "404", "422", "500"}.issubset(operation["responses"])


def test_feed_companion_payload_models_expose_and_enforce_exact_constraints():
    uuid_fragment = (
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    )
    schemas = create_app().openapi()["components"]["schemas"]
    expected = {
        "CompanionAttentionPayload": {
            "attention_ref": rf"^companion_attention:{uuid_fragment}$",
            "issue_ref": rf"^companion_issue:{uuid_fragment}$",
            "summary_text": (1, 500),
        },
        "CompanionProposalPayload": {
            "proposal_ref": rf"^companion_proposal:{uuid_fragment}$",
            "issue_ref": rf"^companion_issue:{uuid_fragment}$",
            "summary_text": (1, 500),
        },
        "CompanionDecisionPayload": {
            "decision_record_ref": rf"^decision_record:{uuid_fragment}$",
            "issue_ref": rf"^companion_issue:{uuid_fragment}$",
            "proposal_ref": rf"^companion_proposal:{uuid_fragment}$",
            "decision_summary": (1, 500),
        },
    }
    for schema_name, fields in expected.items():
        properties = schemas[schema_name]["properties"]
        for field_name, constraint in fields.items():
            if isinstance(constraint, tuple):
                assert (
                    properties[field_name]["minLength"],
                    properties[field_name]["maxLength"],
                ) == constraint
            else:
                assert properties[field_name]["pattern"] == constraint

    with pytest.raises(ValidationError):
        CompanionAttentionPayload.model_validate(
            {
                "payload_kind": "companion_attention",
                "attention_ref": f"companion_attention:{uuid.uuid4()}",
                "issue_ref": f"issue:{uuid.uuid4()}",
                "summary_text": "Требуется решение.",
            }
        )
    with pytest.raises(ValidationError):
        CompanionDecisionPayload.model_validate(
            {
                "payload_kind": "companion_decision",
                "decision_record_ref": f"decision_record:{uuid.uuid4()}",
                "issue_ref": f"companion_issue:{uuid.uuid4()}",
                "proposal_ref": f"companion_proposal:{uuid.uuid4()}",
                "decision_summary": "x" * 501,
                "safety_gate_authority": "not_granted",
            }
        )


def test_feed_service_pages_literal_rows_and_allows_archived_history(ft008_database, ft008_seed):
    farm, boss, plant = ft008_seed
    text = "<script>prompt</script> https://example.test/run"
    ids = [uuid.uuid4(), uuid.uuid4()]
    with ft008_database.session() as session, session.begin():
        for index, event_id in enumerate(ids):
            message_id = uuid.uuid4()
            session.add(UIFeedEvent(ui_event_id=event_id, farm_id=farm.farm_id, plant_id=plant.plant_id, created_at=datetime(2026, 1, 1, 0, 0, index, tzinfo=timezone.utc), source_type="agent_message", source_id=str(message_id), source_refs=[f"message_envelope:{message_id}"], display_kind="agent_message", display_payload={"payload_kind": "agent_message", "agent_id": "crop_advisor", "candidate_claim_type": "observation", "quoted_text": text}, visible_to_roles=["boss", "engineer", "consultant"], visible_to_agents=False, consumable_by_agents=False))
    with ft008_database.session() as session:
        first = PlantFeedService(session).list_feed(boss, plant_id=plant.plant_id, cursor=None, limit=1)
    assert first.items[0].display_payload["quoted_text"] == text and first.next_cursor
    with ft008_database.session() as session:
        second = PlantFeedService(session).list_feed(boss, plant_id=plant.plant_id, cursor=first.next_cursor, limit=1)
    assert second.items[0].ui_event_id == ids[1]
    assert second.next_cursor is not None


@pytest.mark.parametrize("cursor", ["=", "e30", "not_base64!"])
def test_feed_cursor_is_strict(ft008_database, ft008_seed, cursor):
    _farm, boss, plant = ft008_seed
    with ft008_database.session() as session, pytest.raises(PlantFeedError) as raised:
        PlantFeedService(session).list_feed(boss, plant_id=plant.plant_id, cursor=cursor, limit=50)
    assert raised.value.code is PlantFeedErrorCode.FEED_CURSOR_INVALID


def test_feed_endpoint_auth_no_store_and_safe_error_matrix(
    ft008_database, ft008_seed
):
    farm, boss, plant = ft008_seed
    app = create_app(database=ft008_database)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        unauthenticated = client.get(f"/api/plants/{plant.plant_id}/feed")
        assert unauthenticated.status_code == 401
        assert unauthenticated.headers["cache-control"] == "no-store"
        assert unauthenticated.json()["error"]["code"] == "AUTH_SESSION_REQUIRED"

        app.dependency_overrides[require_actor_context] = lambda: boss
        ok = client.get(f"/api/plants/{plant.plant_id}/feed")
        assert ok.status_code == 200
        assert ok.headers["cache-control"] == "no-store"

        cases = (
            (f"/api/plants/{plant.plant_id}/feed?unknown=1", "VALIDATION_FAILED"),
            (f"/api/plants/{plant.plant_id}/feed?limit=01", "FEED_LIMIT_INVALID"),
            (f"/api/plants/{plant.plant_id}/feed?cursor=e30", "FEED_CURSOR_INVALID"),
            ("/api/plants/not-a-uuid/feed", "VALIDATION_FAILED"),
        )
        for path, code in cases:
            response = client.get(path)
            assert response.status_code == 422
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["error"]["code"] == code

        engineer, _membership = create_actor(ft008_database, farm, "engineer")
        app.dependency_overrides[require_actor_context] = lambda: engineer
        forbidden = client.get(f"/api/plants/{plant.plant_id}/feed")
        assert forbidden.status_code == 404
        assert forbidden.headers["cache-control"] == "no-store"
        assert forbidden.json()["error"]["code"] == "AUTH_PLANT_FORBIDDEN"


def test_feed_endpoint_persistence_error_is_no_store(ft008_database, ft008_seed):
    _farm, boss, plant = ft008_seed
    app = create_app(database=ft008_database)
    app.dependency_overrides[require_actor_context] = lambda: boss

    class FailingDatabase:
        def session(self):
            raise RuntimeError("synthetic persistence failure")

    app.state.database = FailingDatabase()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get(f"/api/plants/{plant.plant_id}/feed")
    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"]["code"] == "FEED_PERSISTENCE_FAILED"


def test_feed_response_union_returns_strict_inert_safety_status(
    ft011_database,
    ft011_seed,
):
    farm, boss, _membership, plant = ft011_seed
    decision_id = uuid.uuid4()
    message_id = uuid.uuid4()
    summary = "Действие не поддерживается безопасным процессом MVP."
    with ft011_database.session() as session, session.begin():
        session.add(
            UIFeedEvent(
                ui_event_id=decision_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                created_at=datetime(2026, 7, 20, 6, 0, tzinfo=timezone.utc),
                source_type="safety",
                source_id=str(decision_id),
                source_refs=[
                    f"message_envelope:{message_id}",
                    f"safety_classification:{message_id}",
                ],
                display_kind="safety_status",
                display_payload={
                    "payload_kind": "safety_status",
                    "decision_ref": f"safety_decision:{decision_id}",
                    "classification_ref": f"safety_classification:{message_id}",
                    "action_kind": "dosing_command",
                    "safety_status": "safety_blocked",
                    "reason_code": "unsupported_action",
                    "summary_text": summary,
                    "evidence_refs": [],
                    "approval_input_freshness": None,
                    "expires_at": None,
                },
                visible_to_roles=["boss", "engineer"],
                visible_to_agents=False,
                consumable_by_agents=False,
                agent_id=None,
                roster_version=None,
            )
        )
    app = create_app(database=ft011_database)
    app.dependency_overrides[require_actor_context] = lambda: boss
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get(f"/api/plants/{plant.plant_id}/feed")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    item = next(
        item
        for item in response.json()["items"]
        if item["display_kind"] == "safety_status"
    )
    assert item["display_kind"] == "safety_status"
    assert item["display_payload"]["summary_text"] == summary
    assert item["visible_to_agents"] is item["consumable_by_agents"] is False
    assert "candidate" not in str(item).lower()
