from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.app.access_admin.dependencies import require_actor_context
from backend.app.access_admin.farm_service import FarmService
from backend.app.main import create_app
from backend.app.task_follow_up import Approval, Outcome, Task
from tests.backend.plant_operations.conftest import create_actor
from tests.backend.task_follow_up.conftest import ft012_database, ft012_seed  # noqa: F401
from tests.backend.task_follow_up.test_domain_loop import _pending_decision


CANONICAL_UUID_PATTERN = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def test_openapi_exposes_exact_strict_ft012_paths_and_no_arbitrary_fields():
    schema = create_app().openapi()
    paths = {
        "/api/plants/{plant_id}/tasks",
        "/api/plants/{plant_id}/approvals",
        "/api/plants/{plant_id}/safety-decisions/{safety_decision_id}/approval",
        "/api/plants/{plant_id}/tasks/{task_id}/complete",
        "/api/plants/{plant_id}/tasks/{task_id}/outcome",
    }
    assert paths <= set(schema["paths"])
    assert {item["name"] for item in schema["paths"]["/api/plants/{plant_id}/tasks"]["get"]["parameters"]} >= {"plant_id", "status", "kind", "limit"}
    assert {item["name"] for item in schema["paths"]["/api/plants/{plant_id}/approvals"]["get"]["parameters"]} >= {"plant_id", "status", "limit"}
    for path in paths:
        for operation in schema["paths"][path].values():
            if isinstance(operation, dict) and "responses" in operation:
                assert "200" in operation["responses"]
                for parameter in operation.get("parameters", []):
                    if parameter["in"] == "path":
                        assert parameter["schema"]["format"] == "uuid"
                        assert parameter["schema"]["pattern"] == CANONICAL_UUID_PATTERN
    serialized = str({path: schema["paths"][path] for path in paths})
    assert all(forbidden not in serialized for forbidden in (
        "target_value", "quantity", "dosage", "device_command",
        "provider_payload", "authorization_scope", "request_fingerprint",
        "metadata",
    ))

    approval_schema = schema["components"]["schemas"]["ApprovalViewV1"]
    decided_by = approval_schema["properties"]["decided_by"]["anyOf"][0]
    assert decided_by["discriminator"]["propertyName"] == "permission_source"
    assert len(decided_by["oneOf"]) == 2
    boss_schema = schema["components"]["schemas"]["BossApprovalActorViewV1"]
    grant_schema = schema["components"]["schemas"][
        "PlantAccessGrantApprovalActorViewV1"
    ]
    assert "grant_id" not in boss_schema["properties"]
    assert "grant_id" in grant_schema["required"]


def test_http_requires_lowercase_canonical_uuid_for_every_ft012_path_id(
    ft012_database, ft012_seed,
):
    _farm, boss, _membership, plant = ft012_seed
    app = create_app(database=ft012_database)
    app.dependency_overrides[require_actor_context] = lambda: boss
    canonical = "abcdefab-cdef-4abc-8def-abcdefabcdef"
    uppercase = canonical.upper()
    compact = canonical.replace("-", "")
    complete_body = {"schema_version": 1, "request_id": str(uuid.uuid4())}
    outcome_body = {
        "schema_version": 1,
        "request_id": str(uuid.uuid4()),
        "value": "no_data",
        "evidence_refs": [],
    }
    with TestClient(app, base_url="http://127.0.0.1") as client:
        canonical_response = client.get(f"/api/plants/{plant.plant_id}/tasks")
        assert canonical_response.status_code == 200

        invalid_responses = (
            client.get(f"/api/plants/{uppercase}/tasks"),
            client.get(f"/api/plants/{compact}/approvals"),
            client.post(
                f"/api/plants/{uppercase}/safety-decisions/{canonical}/approval",
                json={**complete_body, "expected_version": 1, "decision": "rejected"},
            ),
            client.post(
                f"/api/plants/{plant.plant_id}/safety-decisions/{uppercase}/approval",
                json={**complete_body, "expected_version": 1, "decision": "rejected"},
            ),
            client.post(
                f"/api/plants/{compact}/tasks/{canonical}/complete",
                json=complete_body,
            ),
            client.post(
                f"/api/plants/{plant.plant_id}/tasks/{compact}/complete",
                json=complete_body,
            ),
            client.post(
                f"/api/plants/{uppercase}/tasks/{canonical}/outcome",
                json=outcome_body,
            ),
            client.post(
                f"/api/plants/{plant.plant_id}/tasks/{uppercase}/outcome",
                json=outcome_body,
            ),
        )
        for invalid in invalid_responses:
            assert invalid.status_code == 422
            assert invalid.headers["cache-control"] == "no-store"
            assert invalid.json()["error"] == {
                "code": "VALIDATION_FAILED",
                "message": "Request validation failed.",
                "request_id": invalid.json()["error"]["request_id"],
            }


def test_http_rejects_percent_encoded_uuid_bytes_before_dependency_or_binding(
    ft012_database, ft012_seed,
):
    _farm, boss, _membership, plant = ft012_seed
    dependency_calls = 0

    def actor_dependency():
        nonlocal dependency_calls
        dependency_calls += 1
        return boss

    def encoded(value: uuid.UUID) -> str:
        text = str(value)
        return f"%{ord(text[0]):02X}{text[1:]}"

    app = create_app(database=ft012_database)
    app.dependency_overrides[require_actor_context] = actor_dependency
    fixed = uuid.uuid4()
    encoded_plant = encoded(plant.plant_id)
    encoded_fixed = encoded(fixed)
    complete_body = {"schema_version": 1, "request_id": str(uuid.uuid4())}
    approval_body = {
        **complete_body,
        "expected_version": 1,
        "decision": "rejected",
    }
    outcome_body = {
        "schema_version": 1,
        "request_id": str(uuid.uuid4()),
        "value": "no_data",
        "evidence_refs": [],
    }
    cases = (
        ("get", f"/api/plants/{encoded_plant}/tasks", None),
        ("get", f"/api/plants/{encoded_plant}/approvals", None),
        (
            "post",
            f"/api/plants/{encoded_plant}/safety-decisions/{fixed}/approval",
            approval_body,
        ),
        (
            "post",
            f"/api/plants/{plant.plant_id}/safety-decisions/{encoded_fixed}/approval",
            approval_body,
        ),
        (
            "post",
            f"/api/plants/{encoded_plant}/tasks/{fixed}/complete",
            complete_body,
        ),
        (
            "post",
            f"/api/plants/{plant.plant_id}/tasks/{encoded_fixed}/complete",
            complete_body,
        ),
        (
            "post",
            f"/api/plants/{encoded_plant}/tasks/{fixed}/outcome",
            outcome_body,
        ),
        (
            "post",
            f"/api/plants/{plant.plant_id}/tasks/{encoded_fixed}/outcome",
            outcome_body,
        ),
    )

    with TestClient(app, base_url="http://127.0.0.1") as client:
        for method, path, body in cases:
            response = getattr(client, method)(
                path,
                **({"json": body} if body is not None else {}),
            )
            assert response.status_code == 422
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["error"] == {
                "code": "VALIDATION_FAILED",
                "message": "Request validation failed.",
                "request_id": response.json()["error"]["request_id"],
            }
    assert dependency_calls == 0


def test_http_complete_approval_action_followup_outcome_and_redaction(
    ft012_database, ft012_seed, tmp_path,
):
    farm, boss, _membership, plant = ft012_seed
    now = datetime.now(timezone.utc)
    decision_id, _ph, _ec = _pending_decision(
        ft012_database, farm, boss, plant,
        instant=now - timedelta(minutes=5),
        expires_at=now + timedelta(hours=1),
    )
    settings = ft012_database.settings.model_copy(
        update={"local_timeline_root": tmp_path / "timeline"}
    )
    app = create_app(settings=settings, database=ft012_database)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        unauthenticated = client.get(f"/api/plants/{plant.plant_id}/tasks")
        assert unauthenticated.status_code == 401
        assert unauthenticated.headers["cache-control"] == "no-store"
        app.dependency_overrides[require_actor_context] = lambda: boss

        approved = client.post(
            f"/api/plants/{plant.plant_id}/safety-decisions/{decision_id}/approval",
            json={
                "schema_version": 1, "request_id": str(uuid.uuid4()),
                "expected_version": 1, "decision": "approved",
            },
        )
        assert approved.status_code == 200
        assert approved.headers["cache-control"] == "no-store"
        body = approved.json()
        assert set(body) == {"schema_version", "approval", "action_task", "result"}
        assert body["approval"]["status"] == "approved"
        assert body["approval"]["decided_by"] == {
            "account_id": str(boss.account_id),
            "membership_id": str(boss.membership_id),
            "role_preset": "boss",
            "permission_source": "boss_role",
        }
        assert body["action_task"]["kind"] == "action"
        assert all(token not in approved.text for token in (
            "request_fingerprint", "session_id", "auth_provenance",
            "candidate_output", "provider", "target_value", "device_command",
        ))

        action_id = body["action_task"]["task_id"]
        completed = client.post(
            f"/api/plants/{plant.plant_id}/tasks/{action_id}/complete",
            json={"schema_version": 1, "request_id": str(uuid.uuid4())},
        )
        assert completed.status_code == 200
        follow_up = completed.json()["follow_up_task"]
        assert follow_up["kind"] == "follow_up"
        assert follow_up["status"] == "open"

        outcome = client.post(
            f"/api/plants/{plant.plant_id}/tasks/{follow_up['task_id']}/outcome",
            json={
                "schema_version": 1, "request_id": str(uuid.uuid4()),
                "value": "no_data", "evidence_refs": [],
            },
        )
        assert outcome.status_code == 200
        assert outcome.json()["outcome"]["value"] == "no_data"
        assert outcome.json()["task"]["status"] == "completed"

        tasks = client.get(f"/api/plants/{plant.plant_id}/tasks?limit=10")
        approvals = client.get(f"/api/plants/{plant.plant_id}/approvals?status=approved")
        assert tasks.status_code == approvals.status_code == 200
        assert tasks.headers["cache-control"] == approvals.headers["cache-control"] == "no-store"
        assert len(tasks.json()["items"]) == 2
        assert len(approvals.json()["items"]) == 1
        assert "request_id" not in tasks.text and "request_id" not in approvals.text

        invalid = client.post(
            f"/api/plants/{plant.plant_id}/tasks/{action_id}/complete",
            json={"schema_version": 1, "request_id": str(uuid.uuid4()), "target_value": 6.0},
        )
        assert invalid.status_code == 422
        assert invalid.headers["cache-control"] == "no-store"
        bad_query = client.get(f"/api/plants/{plant.plant_id}/tasks?unknown=secret")
        assert bad_query.status_code == 400
        assert bad_query.json()["error"]["code"] == "TASK_REQUEST_INVALID"
        assert "secret" not in bad_query.text

    with ft012_database.session() as session:
        assert session.scalar(select(func.count(Approval.approval_id))) == 1
        assert session.scalar(select(func.count(Task.task_id))) == 2
        assert session.scalar(select(func.count(Outcome.outcome_id))) == 1


def test_http_engineer_decided_by_requires_current_grant_id(
    ft012_database, ft012_seed, tmp_path,
):
    farm, boss, _membership, plant = ft012_seed
    engineer, engineer_membership = create_actor(ft012_database, farm, "engineer")
    with ft012_database.session() as session:
        grant = FarmService(session).grant_access(
            boss,
            plant_id=plant.plant_id,
            membership_id=engineer_membership.membership_id,
            plant_approve_actions=True,
        ).entity
    now = datetime.now(timezone.utc)
    decision_id, _ph, _ec = _pending_decision(
        ft012_database,
        farm,
        boss,
        plant,
        instant=now - timedelta(minutes=5),
        expires_at=now + timedelta(hours=1),
    )
    settings = ft012_database.settings.model_copy(
        update={"local_timeline_root": tmp_path / "timeline"}
    )
    app = create_app(settings=settings, database=ft012_database)
    app.dependency_overrides[require_actor_context] = lambda: engineer
    with TestClient(app, base_url="http://127.0.0.1") as client:
        rejected = client.post(
            f"/api/plants/{plant.plant_id}/safety-decisions/{decision_id}/approval",
            json={
                "schema_version": 1,
                "request_id": str(uuid.uuid4()),
                "expected_version": 1,
                "decision": "rejected",
            },
        )
    assert rejected.status_code == 200
    assert rejected.json()["approval"]["decided_by"] == {
        "account_id": str(engineer.account_id),
        "membership_id": str(engineer.membership_id),
        "role_preset": "engineer",
        "permission_source": "plant_access_grant",
        "grant_id": str(grant.grant_id),
    }


def test_http_no_existence_leak_and_evidence_policy(ft012_database, ft012_seed):
    _farm, boss, _membership, plant = ft012_seed
    app = create_app(database=ft012_database)
    app.dependency_overrides[require_actor_context] = lambda: boss
    with TestClient(app, base_url="http://127.0.0.1") as client:
        missing = client.post(
            f"/api/plants/{plant.plant_id}/tasks/{uuid.uuid4()}/complete",
            json={"schema_version": 1, "request_id": str(uuid.uuid4())},
        )
        assert missing.status_code == 404
        assert missing.json()["error"] == {
            "code": "TASK_SCOPE_NOT_FOUND",
            "message": "Task scope is not available.",
            "request_id": missing.json()["error"]["request_id"],
        }
        invalid = client.post(
            f"/api/plants/{plant.plant_id}/tasks/{uuid.uuid4()}/outcome",
            json={
                "schema_version": 1, "request_id": str(uuid.uuid4()),
                "value": "improved", "evidence_refs": [],
            },
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "TASK_EVIDENCE_REQUIRED"
