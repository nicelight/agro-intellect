from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.app.access_admin.dependencies import (
    install_protected_route_error_handler,
    require_actor_context,
)
from backend.app.access_admin.errors import install_error_handlers
from backend.app.api import companion as companion_api
from backend.app.companion_governance import (
    CompanionGovernanceService,
    CompanionHumanAttention,
    CompanionProposal,
    DecisionRecord,
)
from backend.app.task_follow_up import (
    Task,
    TaskFollowUpError,
    TaskFollowUpErrorCode,
    TaskFollowUpService,
)
from tests.backend.companion_governance.conftest import (
    FT013_NOW,
    TimelineRecorder,
    ft013_database,
    ft013_seed,
    make_proposal_command,
    seed_companion_classification,
)


_DECISION_PATH = "/api/plants/{plant_id}/companion/proposals/{proposal_id}/decision"
_CLOSE_PATH = "/api/plants/{plant_id}/companion/issues/{issue_id}/close"


def _app(database, actor) -> FastAPI:
    app = FastAPI()
    app.add_middleware(companion_api.FT013RawPathCanonicalityMiddleware)
    app.state.database = database
    install_error_handlers(app)
    install_protected_route_error_handler(app)
    app.include_router(companion_api.router)
    app.dependency_overrides[require_actor_context] = lambda: actor
    return app


def _seed_proposal(
    database,
    farm,
    boss,
    plant,
    *,
    effect: str = "discussion_only",
):
    message_id = seed_companion_classification(
        database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        effect=effect,
    )
    with database.session() as session:
        return CompanionGovernanceService(
            session,
            timeline_appender=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).persist_companion_proposal(
            make_proposal_command(
                boss,
                plant_id=plant.plant_id,
                message_id=message_id,
                effect=effect,
            )
        )


def test_decision_and_close_routes_return_strict_no_store_results(
    ft013_database,
    ft013_seed,
    monkeypatch,
):
    farm, boss, _membership, plant = ft013_seed
    persisted = _seed_proposal(ft013_database, farm, boss, plant)
    timeline = TimelineRecorder()
    monkeypatch.setattr(
        companion_api,
        "CompanionGovernanceService",
        lambda session: CompanionGovernanceService(
            session,
            timeline_appender=timeline,
            clock=lambda: FT013_NOW,
        ),
    )
    app = _app(ft013_database, boss)
    decision_request = uuid.uuid4()
    decision_path = (
        f"/api/plants/{plant.plant_id}/companion/proposals/"
        f"{persisted.proposal_id}/decision"
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            decision_path,
            json={
                "schema_version": 1,
                "request_id": str(decision_request),
                "expected_version": 1,
                "decision": "approved",
                "decision_summary": "Обсуждение подтверждено.",
                "issue_resolution": "resolved",
            },
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        value = response.json()
        assert set(value) == {
            "schema_version",
            "result",
            "decision_record",
            "workflow_task_ref",
            "issue",
            "conclusion",
        }
        assert value["result"] == "created"
        assert value["workflow_task_ref"] is None
        assert value["decision_record"]["decision"] == "approved"
        assert value["decision_record"]["safety_gate_authority"] == "not_granted"
        assert value["issue"]["status"] == "resolved"
        assert value["conclusion"]["conclusion_status"] == "decided"

        duplicate = client.post(
            decision_path,
            json={
                "schema_version": 1,
                "request_id": str(decision_request),
                "expected_version": 1,
                "decision": "approved",
                "decision_summary": "Обсуждение подтверждено.",
                "issue_resolution": "resolved",
            },
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["result"] == "duplicate"

        close_path = (
            f"/api/plants/{plant.plant_id}/companion/issues/"
            f"{persisted.issue_id}/close"
        )
        closed = client.post(
            close_path,
            json={
                "schema_version": 1,
                "request_id": str(uuid.uuid4()),
                "expected_version": value["issue"]["record_version"],
            },
        )
        assert closed.status_code == 200
        assert closed.headers["cache-control"] == "no-store"
        assert closed.json()["result"] == "closed"
        assert closed.json()["issue"]["status"] == "closed"


def test_decision_route_rejects_unknown_fields_query_and_non_v4_request(
    ft013_database,
    ft013_seed,
    monkeypatch,
):
    farm, boss, _membership, plant = ft013_seed
    persisted = _seed_proposal(ft013_database, farm, boss, plant)
    monkeypatch.setattr(
        companion_api,
        "CompanionGovernanceService",
        lambda session: CompanionGovernanceService(
            session,
            timeline_appender=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ),
    )
    app = _app(ft013_database, boss)
    path = (
        f"/api/plants/{plant.plant_id}/companion/proposals/"
        f"{persisted.proposal_id}/decision"
    )
    valid = {
        "schema_version": 1,
        "request_id": str(uuid.uuid4()),
        "expected_version": 1,
        "decision": "approved",
        "decision_summary": "Решение.",
        "issue_resolution": "keep_open",
    }
    with TestClient(app, base_url="http://127.0.0.1") as client:
        query = client.post(f"{path}?unexpected=1", json=valid)
        assert query.status_code == 422
        assert query.json()["error"]["code"] == "VALIDATION_FAILED"
        unknown = client.post(path, json={**valid, "effect": "action"})
        assert unknown.status_code == 422
        non_v4 = client.post(
            path,
            json={**valid, "request_id": str(uuid.uuid1())},
        )
        assert non_v4.status_code == 422


def test_impossible_nested_task_error_returns_redacted_internal_failure(
    ft013_database,
    ft013_seed,
    monkeypatch,
):
    farm, boss, _membership, plant = ft013_seed
    persisted = _seed_proposal(
        ft013_database,
        farm,
        boss,
        plant,
        effect="check",
    )

    def impossible_task_error(*_args, **_kwargs):
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)

    monkeypatch.setattr(
        TaskFollowUpService,
        "create_ordinary_task",
        impossible_task_error,
    )
    monkeypatch.setattr(
        companion_api,
        "CompanionGovernanceService",
        lambda session: CompanionGovernanceService(
            session,
            timeline_appender=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ),
    )
    app = _app(ft013_database, boss)
    path = (
        f"/api/plants/{plant.plant_id}/companion/proposals/"
        f"{persisted.proposal_id}/decision"
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            path,
            json={
                "schema_version": 1,
                "request_id": str(uuid.uuid4()),
                "expected_version": 1,
                "decision": "approved",
                "decision_summary": "Решение.",
                "issue_resolution": "keep_open",
            },
        )

    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"]["code"] == "COMPANION_INTERNAL_ERROR"
    assert response.json()["error"]["message"] == (
        "Companion governance request failed."
    )
    assert "TASK_REQUEST_INVALID" not in response.text
    with ft013_database.session() as session:
        proposal = session.get(CompanionProposal, persisted.proposal_id)
        attention = session.get(
            CompanionHumanAttention,
            persisted.attention_id,
        )
        assert proposal is not None and proposal.state == "pending"
        assert attention is not None and attention.status == "active"
        assert session.scalar(
            select(func.count(DecisionRecord.decision_record_id))
        ) == 0
        assert session.scalar(select(func.count(Task.task_id))) == 0


def test_openapi_exposes_exact_decision_and_close_request_fields():
    app = FastAPI()
    app.include_router(companion_api.router)
    schema = app.openapi()
    assert set(schema["paths"][_DECISION_PATH]) == {"post"}
    assert set(schema["paths"][_CLOSE_PATH]) == {"post"}
    decision = schema["components"]["schemas"]["CompanionDecisionRequestV1"]
    close = schema["components"]["schemas"]["CompanionIssueCloseRequestV1"]
    attention = schema["components"]["schemas"]["CompanionAttentionViewV1"]
    assert set(decision["properties"]) == {
        "schema_version",
        "request_id",
        "expected_version",
        "decision",
        "decision_summary",
        "issue_resolution",
    }
    assert set(close["properties"]) == {
        "schema_version",
        "request_id",
        "expected_version",
    }
    assert "current_proposal_ref" in attention["required"]
    assert "anyOf" not in attention["properties"]["current_proposal_ref"]
