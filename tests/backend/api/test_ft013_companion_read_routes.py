from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.access_admin.dependencies import (
    install_protected_route_error_handler,
    require_actor_context,
)
from backend.app.access_admin.errors import install_error_handlers
from backend.app.companion_governance import (
    CompanionGovernanceService,
    CompanionHumanAttention,
    CompanionIssue,
    CompanionProposal,
    DecisionRecord,
)
from backend.app.api.companion import (
    FT013RawPathCanonicalityMiddleware,
    router as companion_router,
)
from backend.app.main import create_app
from backend.app.safety_gate import SafetyClassification
from tests.backend.companion_governance.conftest import (  # noqa: F401
    ft013_database,
    ft013_seed,
)
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    grant_access,
)


_LIST_PATH = "/api/plants/{plant_id}/companion/issues"
_DETAIL_PATH = "/api/plants/{plant_id}/companion/issues/{issue_id}"
_DECISION_PATH = "/api/plants/{plant_id}/companion/proposals/{proposal_id}/decision"
_CLOSE_PATH = "/api/plants/{plant_id}/companion/issues/{issue_id}/close"
_UUID_PATTERN = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def _isolated_app(database=None) -> FastAPI:
    app = FastAPI()
    app.add_middleware(FT013RawPathCanonicalityMiddleware)
    app.state.database = database
    install_error_handlers(app)
    install_protected_route_error_handler(app)
    app.include_router(companion_router)
    return app


def _event_ref(event_type: str) -> dict[str, object]:
    event_id = uuid.uuid4()
    return {
        "timeline_event_id": str(event_id),
        "timeline_ref": f"timeline.jsonl#{event_id}",
        "event_type": event_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _seed_open_issue(database, farm, plant, *, focused: bool = True):
    issue_id = uuid.uuid4()
    attention_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    message_id = uuid.uuid4()
    run_id = uuid.uuid4()
    now = datetime(2026, 7, 24, 6, 0, tzinfo=timezone.utc)
    source_refs = [
        f"plant:{plant.plant_id}",
        f"message_envelope:{message_id}",
        f"safety_classification:{message_id}",
    ]
    with database.session() as session, session.begin():
        session.add(
            SafetyClassification(
                message_id=message_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                origin_agent_id="companion",
                classifier_version="safety_gate_v1",
                classification="safe_information",
                safe_task_kind=None,
                reason_code="non_physical_information",
                physical_action_kind=None,
                provider_status="completed",
                model_ref=None,
                input_sha256="a" * 64,
                result_sha256="b" * 64,
                created_at=now,
            )
        )
        issue = CompanionIssue(
            issue_id=issue_id,
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
            status="open",
            is_focused=focused,
            summary_text="Контроль состояния корневой зоны.",
            record_version=1,
            created_by_run_id=run_id,
            created_at=now,
            opened_event_ref=_event_ref("companion_issue_opened"),
        )
        session.add(issue)
        session.flush()
        session.add(
            CompanionHumanAttention(
                attention_id=attention_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                issue_id=issue_id,
                attention_sequence=1,
                status="active",
                summary_text="Требуется решение оператора.",
                record_version=1,
                created_at=now,
            )
        )
        session.add(
            CompanionProposal(
                proposal_id=proposal_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                issue_id=issue_id,
                attention_id=attention_id,
                proposal_sequence=1,
                state="pending",
                record_version=1,
                proposal_summary="Проверить корневую зону.",
                proposal_text="<b>Осмотреть корни вручную</b>",
                rationale_text="Есть признаки изменения состояния.",
                proposed_effect="discussion_only",
                task_display_text=None,
                suggested_resolution="keep_open",
                source_run_id=run_id,
                source_message_id=message_id,
                source_classification_message_id=message_id,
                source_refs=source_refs,
                run_request_fingerprint="c" * 64,
                created_at=now,
                created_event_ref=_event_ref("companion_proposal_created"),
            )
        )
    return issue_id, attention_id, proposal_id


def _seed_resolved_issue(database, farm, plant) -> uuid.UUID:
    issue_id = uuid.uuid4()
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with database.session() as session, session.begin():
        session.add(
            CompanionIssue(
                issue_id=issue_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                status="resolved",
                is_focused=False,
                summary_text="Историческая решённая проблема.",
                record_version=2,
                created_by_run_id=uuid.uuid4(),
                created_at=created_at,
                resolved_at=created_at + timedelta(hours=1),
                opened_event_ref=_event_ref("companion_issue_opened"),
                resolved_event_ref=_event_ref("companion_issue_resolved"),
            )
        )
    return issue_id


def _seed_inconsistent_open_issue(database, farm, plant) -> uuid.UUID:
    issue_id = uuid.uuid4()
    with database.session() as session, session.begin():
        session.add(
            CompanionIssue(
                issue_id=issue_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                status="open",
                is_focused=False,
                summary_text="Неполный authority graph.",
                record_version=1,
                created_by_run_id=uuid.uuid4(),
                created_at=datetime.now(timezone.utc),
                opened_event_ref=_event_ref("companion_issue_opened"),
            )
        )
    return issue_id


def test_openapi_is_exact_governance_boundary_without_production_registration():
    schema = _isolated_app().openapi()
    assert set(schema["paths"]) == {
        _LIST_PATH,
        _DETAIL_PATH,
        _DECISION_PATH,
        _CLOSE_PATH,
    }
    assert set(schema["paths"][_LIST_PATH]) == {"get"}
    assert set(schema["paths"][_DETAIL_PATH]) == {"get"}
    assert set(schema["paths"][_DECISION_PATH]) == {"post"}
    assert set(schema["paths"][_CLOSE_PATH]) == {"post"}
    list_operation = schema["paths"][_LIST_PATH]["get"]
    assert {item["name"] for item in list_operation["parameters"]} == {
        "plant_id",
        "status",
        "cursor",
        "limit",
    }
    for path in (_LIST_PATH, _DETAIL_PATH):
        operation = schema["paths"][path]["get"]
        assert {"200", "401", "403", "404", "409", "422", "500"} <= set(
            operation["responses"]
        )
        for parameter in operation["parameters"]:
            if parameter["in"] == "path":
                assert parameter["schema"]["format"] == "uuid"
                assert parameter["schema"]["pattern"] == _UUID_PATTERN
    issue_schema = schema["components"]["schemas"]["IssueSummaryV1"]
    assert set(issue_schema["properties"]) == {
        "issue_id",
        "issue_ref",
        "status",
        "is_focused",
        "summary_text",
        "record_version",
        "created_at",
        "resolved_at",
        "closed_at",
    }
    serialized = str(schema)
    assert all(
        forbidden not in serialized
        for forbidden in (
            "provider_payload",
            "authorization_scope",
            "request_fingerprint",
            "device_command",
            "action_task",
        )
    )
    production_paths = create_app().openapi()["paths"]
    assert _LIST_PATH not in production_paths
    assert _DETAIL_PATH not in production_paths
    assert _DECISION_PATH not in production_paths
    assert _CLOSE_PATH not in production_paths


def test_list_and_detail_return_exact_authority_views_and_status_rank_cursor(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    issue_id, attention_id, proposal_id = _seed_open_issue(
        ft013_database,
        farm,
        plant,
    )
    resolved_id = _seed_resolved_issue(ft013_database, farm, plant)
    app = _isolated_app(ft013_database)
    app.dependency_overrides[require_actor_context] = lambda: boss
    with TestClient(app, base_url="http://127.0.0.1") as client:
        first = client.get(
            f"/api/plants/{plant.plant_id}/companion/issues?limit=1"
        )
        assert first.status_code == 200
        assert first.headers["cache-control"] == "no-store"
        page = first.json()
        assert set(page) == {
            "schema_version",
            "plant_id",
            "focused_issue_ref",
            "items",
            "next_cursor",
        }
        assert [item["issue_id"] for item in page["items"]] == [str(issue_id)]
        assert page["focused_issue_ref"] == f"companion_issue:{issue_id}"
        assert page["next_cursor"]

        second = client.get(
            f"/api/plants/{plant.plant_id}/companion/issues",
            params={"cursor": page["next_cursor"]},
        )
        assert second.status_code == 200
        assert [item["issue_id"] for item in second.json()["items"]] == [
            str(resolved_id)
        ]
        mismatch = client.get(
            f"/api/plants/{plant.plant_id}/companion/issues",
            params={"status": "resolved", "cursor": page["next_cursor"]},
        )
        assert mismatch.status_code == 422
        assert mismatch.json()["error"]["code"] == "VALIDATION_FAILED"

        detail = client.get(
            f"/api/plants/{plant.plant_id}/companion/issues/{issue_id}"
        )
        assert detail.status_code == 200
        assert detail.headers["cache-control"] == "no-store"
        body = detail.json()
        assert set(body) == {
            "schema_version",
            "issue",
            "attention",
            "proposals",
            "decision_records",
            "conclusion",
        }
        assert body["attention"]["attention_id"] == str(attention_id)
        assert body["attention"]["current_proposal_ref"] == (
            f"companion_proposal:{proposal_id}"
        )
        assert [item["proposal_id"] for item in body["proposals"]] == [
            str(proposal_id)
        ]
        assert body["proposals"][0]["proposal_text"] == (
            "<b>Осмотреть корни вручную</b>"
        )
        assert body["decision_records"] == []
        assert body["conclusion"] == {
            "schema_version": 1,
            "issue_id": str(issue_id),
            "issue_status": "open",
            "is_focused": True,
            "conclusion_status": "awaiting_human",
            "current_attention_ref": f"companion_attention:{attention_id}",
            "current_proposal_ref": f"companion_proposal:{proposal_id}",
            "latest_decision_record_ref": None,
            "decision": None,
            "decision_summary": None,
            "allowed_workflow_effect": None,
            "decided_at": None,
            "safety_gate_authority": "not_granted",
        }
        assert all(
            forbidden not in detail.text
            for forbidden in (
                "session_id",
                "run_request_fingerprint",
                "provider_status",
                "model_ref",
                "authorization_scope",
            )
        )


def test_read_access_matrix_archive_retention_and_no_existence_leak(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    issue_id, _attention_id, _proposal_id = _seed_open_issue(
        ft013_database,
        farm,
        plant,
    )
    engineer, engineer_membership = create_actor(ft013_database, farm, "engineer")
    consultant, consultant_membership = create_actor(
        ft013_database,
        farm,
        "consultant",
    )
    grant_access(
        ft013_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    grant_access(
        ft013_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )
    ungranted_engineer, _membership = create_actor(
        ft013_database,
        farm,
        "engineer",
    )
    wrong_farm_actor = copy.copy(boss)
    object.__setattr__(wrong_farm_actor, "farm_id", uuid.uuid4())
    app = _isolated_app(ft013_database)
    path = f"/api/plants/{plant.plant_id}/companion/issues/{issue_id}"
    with TestClient(app, base_url="http://127.0.0.1") as client:
        unauthenticated = client.get(path)
        assert unauthenticated.status_code == 401
        assert unauthenticated.headers["cache-control"] == "no-store"

        for actor in (boss, engineer, consultant):
            with ft013_database.session() as session:
                CompanionGovernanceService(session).get_issue_detail(
                    actor,
                    plant_id=plant.plant_id,
                    issue_id=issue_id,
                )
            app.dependency_overrides[require_actor_context] = lambda actor=actor: actor
            response = client.get(path)
            assert response.status_code == 200, (
                actor.role_preset,
                response.text,
            )
            assert response.headers["cache-control"] == "no-store"

        for actor in (ungranted_engineer, wrong_farm_actor):
            app.dependency_overrides[require_actor_context] = lambda actor=actor: actor
            response = client.get(path)
            assert response.status_code == 404
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["error"]["code"] == "COMPANION_SCOPE_NOT_FOUND"
            assert str(issue_id) not in response.text

        archive_plant(ft013_database, boss, plant_id=plant.plant_id)
        for actor in (boss, engineer, consultant):
            app.dependency_overrides[require_actor_context] = lambda actor=actor: actor
            retained = client.get(path)
            assert retained.status_code == 200
            assert retained.json()["issue"]["issue_id"] == str(issue_id)


def test_path_query_and_read_failures_are_strict_safe_no_store(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    issue_id, _attention_id, _proposal_id = _seed_open_issue(
        ft013_database,
        farm,
        plant,
    )
    inconsistent_id = _seed_inconsistent_open_issue(ft013_database, farm, plant)
    dependency_calls = 0

    def actor_dependency():
        nonlocal dependency_calls
        dependency_calls += 1
        return boss

    app = _isolated_app(ft013_database)
    app.dependency_overrides[require_actor_context] = actor_dependency
    canonical = "abcdefab-cdef-4abc-8def-abcdefabcdef"
    encoded = f"%{ord(canonical[0]):02X}{canonical[1:]}"
    with TestClient(app, base_url="http://127.0.0.1") as client:
        raw_invalid = (
            f"/api/plants/{canonical.upper()}/companion/issues",
            f"/api/plants/{canonical.replace('-', '')}/companion/issues",
            f"/api/plants/{encoded}/companion/issues",
            f"/api/plants/{plant.plant_id}/companion/issues/{canonical.upper()}",
            f"/api/plants/{plant.plant_id}/companion/issues/{encoded}",
        )
        for path in raw_invalid:
            response = client.get(path)
            assert response.status_code == 422
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["error"]["code"] == "VALIDATION_FAILED"
        assert dependency_calls == 0

        invalid_queries = (
            f"/api/plants/{plant.plant_id}/companion/issues?unknown=1",
            f"/api/plants/{plant.plant_id}/companion/issues?status=open&status=closed",
            f"/api/plants/{plant.plant_id}/companion/issues?status=unknown",
            f"/api/plants/{plant.plant_id}/companion/issues?limit=01",
            f"/api/plants/{plant.plant_id}/companion/issues?cursor=e30",
            f"/api/plants/{plant.plant_id}/companion/issues/{issue_id}?unknown=1",
        )
        for path in invalid_queries:
            response = client.get(path)
            assert response.status_code == 422
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["error"]["code"] == "VALIDATION_FAILED"

        missing = client.get(
            f"/api/plants/{plant.plant_id}/companion/issues/{uuid.uuid4()}"
        )
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "COMPANION_SCOPE_NOT_FOUND"

        inconsistent = client.get(
            f"/api/plants/{plant.plant_id}/companion/issues/{inconsistent_id}"
        )
        assert inconsistent.status_code == 500
        assert inconsistent.json()["error"]["code"] == (
            "COMPANION_READ_INCONSISTENT"
        )

    class FailingDatabase:
        def session(self):
            raise RuntimeError("synthetic persistence failure")

    app.state.database = FailingDatabase()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        failed = client.get(
            f"/api/plants/{plant.plant_id}/companion/issues"
        )
    assert failed.status_code == 500
    assert failed.headers["cache-control"] == "no-store"
    assert failed.json()["error"]["code"] == "COMPANION_PERSISTENCE_FAILED"


def test_detail_rejects_proposal_attention_edge_to_another_issue(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    issue_id, _attention_id, proposal_id = _seed_open_issue(
        ft013_database,
        farm,
        plant,
    )
    _other_issue_id, other_attention_id, _other_proposal_id = _seed_open_issue(
        ft013_database,
        farm,
        plant,
        focused=False,
    )
    with ft013_database.session() as session, session.begin():
        proposal = session.get(CompanionProposal, proposal_id)
        proposal.attention_id = other_attention_id

    app = _isolated_app(ft013_database)
    app.dependency_overrides[require_actor_context] = lambda: boss
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get(
            f"/api/plants/{plant.plant_id}/companion/issues/{issue_id}"
        )

    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"]["code"] == "COMPANION_READ_INCONSISTENT"


def test_detail_rejects_any_decision_record_before_w2_owns_its_semantics(
    ft013_database,
    ft013_seed,
):
    farm, boss, membership, plant = ft013_seed
    issue_id, attention_id, proposal_id = _seed_open_issue(
        ft013_database,
        farm,
        plant,
    )
    with ft013_database.session() as session, session.begin():
        proposal = session.get(CompanionProposal, proposal_id)
        decision_record_id = uuid.uuid4()
        session.add(
            DecisionRecord(
                decision_record_id=decision_record_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                issue_id=issue_id,
                proposal_id=proposal_id,
                attention_id=attention_id,
                decision="approved",
                decision_summary="Решение появилось до W2.",
                allowed_workflow_effect="discussion_only",
                issue_resolution="keep_open",
                workflow_effect_ref=None,
                decider_account_id=boss.account_id,
                decider_membership_id=membership.membership_id,
                decider_role_preset="boss",
                decider_permission_source="boss_role",
                decider_grant_id=None,
                request_id=uuid.uuid4(),
                request_fingerprint="d" * 64,
                decided_at=proposal.created_at + timedelta(seconds=1),
                source_refs=[
                    f"companion_issue:{issue_id}",
                    f"companion_attention:{attention_id}",
                    f"companion_proposal:{proposal_id}",
                    (
                        "safety_classification:"
                        f"{proposal.source_classification_message_id}"
                    ),
                    f"plant:{plant.plant_id}",
                ],
                decision_event_ref=_event_ref("companion_decision_recorded"),
                safety_gate_authority="not_granted",
            )
        )

    app = _isolated_app(ft013_database)
    app.dependency_overrides[require_actor_context] = lambda: boss
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get(
            f"/api/plants/{plant.plant_id}/companion/issues/{issue_id}"
        )

    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"]["code"] == "COMPANION_READ_INCONSISTENT"
