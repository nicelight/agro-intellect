from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from backend.app.access_admin.dependencies import require_actor_context
from backend.app.agent_runtime import ModelExecution, ProviderExecutorBindings
from backend.app.companion_governance import (
    CompanionHumanAttention,
    CompanionIssue,
    CompanionProposal,
)
from backend.app.main import create_app
from backend.app.safety_gate import SafetyClassification
from backend.app.task_follow_up import Task
from tests.backend.companion_governance.conftest import (  # noqa: F401
    ft013_database,
    ft013_seed,
)


class _Executor:
    def __init__(self, factory, model_ref):
        self.factory = factory
        self.model_ref = model_ref
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return ModelExecution(
            model_ref=self.model_ref,
            result=self.factory(request),
        )


class _FailingExecutor:
    model_ref = "test_provider:companion_v1"

    def execute(self, _request):
        raise TimeoutError("credential=must-not-leak")


def _proposal(request):
    return {
        "schema_version": 1,
        "runtime_decision": "speak",
        "issue_summary": "Проверить текущее состояние растения.",
        "attention_summary": "Требуется решение оператора.",
        "proposal_summary": "Выполнить контрольную проверку.",
        "proposal_text": "Проверить листья и записать наблюдение.",
        "rationale_text": None,
        "proposed_effect": "check",
        "task_display_text": "Проверить листья.",
        "suggested_resolution": "keep_open",
        "confidence": 0.9,
        "source_refs": list(request.source_refs),
        "reason_code": None,
    }


def _safety(_request):
    return {
        "schema_version": 1,
        "candidate_classification": "safe_task_request",
        "safe_task_kind": "check",
        "physical_action_kind": None,
    }


def _counts(database):
    with database.session() as session:
        return (
            session.scalar(select(func.count(CompanionIssue.issue_id))),
            session.scalar(select(func.count(CompanionHumanAttention.attention_id))),
            session.scalar(select(func.count(CompanionProposal.proposal_id))),
            session.scalar(select(func.count(SafetyClassification.message_id))),
            session.scalar(select(func.count(Task.task_id))),
        )


def test_explicit_run_route_invokes_two_spies_once_and_duplicate_invokes_none(
    ft013_database,
    ft013_seed,
    tmp_path,
):
    _farm, actor, _membership, plant = ft013_seed
    companion = _Executor(_proposal, "test_provider:companion_v1")
    safety = _Executor(_safety, "test_provider:safety_v1")
    settings = ft013_database.settings.model_copy(
        update={"local_timeline_root": tmp_path / "timeline"}
    )
    app = create_app(
        settings=settings,
        database=ft013_database,
        provider_bindings=ProviderExecutorBindings(
            companion=companion,
            safety_gate=safety,
        ),
    )
    app.dependency_overrides[require_actor_context] = lambda: actor
    request_id = uuid.uuid4()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        created = client.post(
            f"/api/plants/{plant.plant_id}/companion/runs",
            json={
                "schema_version": 1,
                "request_id": str(request_id),
                "issue_id": None,
                "expected_issue_version": None,
            },
        )
        duplicate = client.post(
            f"/api/plants/{plant.plant_id}/companion/runs",
            json={
                "schema_version": 1,
                "request_id": str(request_id),
                "issue_id": None,
                "expected_issue_version": None,
            },
        )
        issue_id = created.json()["issue_ref"].split(":", 1)[1]
        conflict = client.post(
            f"/api/plants/{plant.plant_id}/companion/runs",
            json={
                "schema_version": 1,
                "request_id": str(request_id),
                "issue_id": issue_id,
                "expected_issue_version": 1,
            },
        )

    assert created.status_code == duplicate.status_code == 200
    assert created.headers["cache-control"] == "no-store"
    assert created.json()["route_status"] == "proposal_created"
    assert created.json()["model_ref"] == "test_provider:companion_v1"
    assert duplicate.json() == {
        **created.json(),
        "route_status": "proposal_duplicate",
        "model_ref": None,
    }
    assert len(companion.requests) == len(safety.requests) == 1
    assert conflict.status_code == 409
    assert conflict.headers["cache-control"] == "no-store"
    assert conflict.json()["error"]["code"] == "COMPANION_VERSION_CONFLICT"
    assert _counts(ft013_database) == (1, 1, 1, 1, 0)


def test_run_route_is_strict_unbound_and_redacted(
    ft013_database,
    ft013_seed,
    tmp_path,
):
    _farm, actor, _membership, plant = ft013_seed
    settings = ft013_database.settings.model_copy(
        update={"local_timeline_root": tmp_path / "timeline"}
    )
    app = create_app(settings=settings, database=ft013_database)
    app.dependency_overrides[require_actor_context] = lambda: actor
    path = f"/api/plants/{plant.plant_id}/companion/runs"
    base = {
        "schema_version": 1,
        "request_id": str(uuid.uuid4()),
        "issue_id": None,
        "expected_issue_version": None,
    }
    with TestClient(app, base_url="http://127.0.0.1") as client:
        unbound = client.post(path, json=base)
        unknown = client.post(path, json={**base, "prompt": "secret"})
        invalid_pair = client.post(
            path,
            json={**base, "issue_id": str(uuid.uuid4())},
        )
        bad_query = client.post(f"{path}?provider=fake", json=base)
        uppercase_path = client.post(
            f"/api/plants/{str(plant.plant_id).upper()}/companion/runs",
            json=base,
        )

    assert unbound.status_code == 503
    assert unbound.json()["error"]["code"] == "COMPANION_RUNTIME_NOT_CONFIGURED"
    assert all(secret not in unbound.text.lower() for secret in ("prompt", "provider", "credential"))
    for response in (unknown, invalid_pair):
        assert response.status_code == 422
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["error"]["code"] == "VALIDATION_FAILED"
    assert bad_query.status_code == 422
    assert bad_query.json()["error"]["code"] == "VALIDATION_FAILED"
    assert uppercase_path.status_code == 422
    assert uppercase_path.json()["error"]["code"] == "VALIDATION_FAILED"
    assert _counts(ft013_database) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize(
    ("companion", "safety", "status_code", "code", "route_status", "reason_code"),
    [
        (
            _FailingExecutor(),
            _Executor(_safety, "test_provider:safety_v1"),
            502,
            "COMPANION_PROVIDER_FAILED",
            None,
            None,
        ),
        (
            _Executor(lambda _request: {"schema_version": 1}, "test_provider:invalid"),
            _Executor(_safety, "test_provider:safety_v1"),
            502,
            "COMPANION_OUTPUT_INVALID",
            None,
            None,
        ),
        (
            _Executor(_proposal, "test_provider:companion_v1"),
            _Executor(
                lambda _request: {
                    "schema_version": 1,
                    "candidate_classification": "physical_action",
                    "safe_task_kind": None,
                    "physical_action_kind": "ph_adjustment",
                },
                "test_provider:safety_v1",
            ),
            200,
            None,
            "not_governable",
            "physical_action_not_allowed",
        ),
        (
            _Executor(_proposal, "test_provider:companion_v1"),
            None,
            200,
            None,
            "not_governable",
            "classification_uncertain",
        ),
    ],
)
def test_run_route_maps_provider_and_classifier_outcomes_without_governance(
    ft013_database,
    ft013_seed,
    tmp_path,
    companion,
    safety,
    status_code,
    code,
    route_status,
    reason_code,
):
    _farm, actor, _membership, plant = ft013_seed
    settings = ft013_database.settings.model_copy(
        update={"local_timeline_root": tmp_path / "timeline"}
    )
    app = create_app(
        settings=settings,
        database=ft013_database,
        provider_bindings=ProviderExecutorBindings(
            companion=companion,
            safety_gate=safety,
        ),
    )
    app.dependency_overrides[require_actor_context] = lambda: actor
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            f"/api/plants/{plant.plant_id}/companion/runs",
            json={
                "schema_version": 1,
                "request_id": str(uuid.uuid4()),
                "issue_id": None,
                "expected_issue_version": None,
            },
        )

    assert response.status_code == status_code
    assert response.headers["cache-control"] == "no-store"
    if code is not None:
        assert response.json()["error"]["code"] == code
        assert "credential" not in response.text.lower()
    else:
        assert response.json()["route_status"] == route_status
        assert response.json()["reason_code"] == reason_code
        assert all(response.json()[name] is None for name in (
            "issue_ref",
            "attention_ref",
            "proposal_ref",
        ))
    assert _counts(ft013_database)[:3] == (0, 0, 0)
