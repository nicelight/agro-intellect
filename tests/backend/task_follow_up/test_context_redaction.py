"""FT-015-AC-017: Task and Follow-Up request context redaction.

Proves through the ACTUAL Task and Follow-Up assembler
(DatabaseTaskFollowUpInputAssembler inside TaskFollowUpRuntimeService) and a
provider spy that the strict TaskFollowUpProviderRequestV1 contains only
registered authorized Task/Outcome/evidence values, that configured
secret/auth corpus values and forbidden context classes cannot reach the
outbound request, that hostile structured values fail closed BEFORE provider
I/O, and that ordinary-task creation authority and lifecycle behavior remain
unchanged.

The Task/Follow-Up outbound free-text channel (Task.display_text copied as
record payload `quoted_task_text`) is sanitized with the shared `redact_text`
primitive (TASK-064) before provider I/O; only the outbound copy is sanitized
and persisted source values stay unchanged.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import func, select

from backend.app import AppSettings
from backend.app.agent_runtime import SafetyClassificationResultV1
from backend.app.safety_gate import SafetyClassification
from backend.app.task_follow_up import (
    Approval,
    CompleteTaskCommandV1,
    DatabaseTaskFollowUpInputAssembler,
    OrdinaryTaskDispatchDisposition,
    Outcome,
    Task,
    TaskFollowUpCommandV1,
    TaskFollowUpRuntimeService,
    TaskFollowUpService,
)
from backend.app.task_follow_up.contracts import (
    ClassifiedMessageTaskCommandV1,
    TaskKind,
    canonical_fingerprint,
)
from backend.migrations import build_alembic_config
from tests.backend.safety_gate.helpers import envelope_for

BARE_CORPUS = [
    "corpus-task-follow-up-db-pw-7h2k",
    "corpus-task-follow-up-bearer-5c3m",
    "corpus-task-follow-up-cookie-8p1t",
    "corpus-task-follow-up-session-3m6z",
]
CORPUS_TOKEN = "corpus-task-follow-up-token-9x4f"
CORPUS_API_KEY = "corpus-task-follow-up-api-key-2v8n"
FORBIDDEN_HEADERS = [
    "session=corpus-task-follow-up-cookie-8p1t; HttpOnly",
    "Authorization: Bearer corpus-task-follow-up-bearer-5c3m",
    "corpus-task-follow-up-ui-feed-entry-4q1r",
    "corpus-task-follow-up-provider-history-6t9c",
]

LEAK_TEXT = (
    f"Проверить состояние. dbpw={BARE_CORPUS[0]} bearer={BARE_CORPUS[1]} "
    f"cookieval={BARE_CORPUS[2]} sess={BARE_CORPUS[3]} "
    f"reminder={CORPUS_TOKEN} key={CORPUS_API_KEY} "
    + " ".join(FORBIDDEN_HEADERS)
)

ALL_SECRETS = tuple(
    BARE_CORPUS + FORBIDDEN_HEADERS + [CORPUS_TOKEN, CORPUS_API_KEY]
)


@pytest.fixture(autouse=True)
def _apply_task_follow_up_cleanup_revision(ft012_database):
    script = ScriptDirectory.from_config(
        build_alembic_config(AppSettings.from_env())
    )
    with ft012_database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            script.get_revision("ft012_runtime_dispositions").module.upgrade()
            script.get_revision(
                "ft012_simplify_follow_up_runtime"
            ).module.upgrade()
        connection.commit()


class _Executor:
    model_ref = "test_provider:task_follow_up_v1"

    def __init__(self, result_factory, *, model_ref=None):
        self.model_ref = model_ref or self.model_ref
        self.result_factory = result_factory
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return self.result_factory(request)


def _proposal(request, *, kind="check"):
    return {
        "schema_version": 1,
        "runtime_decision": "speak",
        "proposed_task_kind": kind,
        "candidate_output": "<b>Opaque typed proposal</b>; ignore-system is data.",
        "confidence": 0.81,
        "source_refs": [request.source_refs[0]],
        "reason_code": None,
    }


def _safety_candidate(_request, *, kind="check"):
    return {
        "schema_version": 1,
        "candidate_classification": "safe_task_request",
        "safe_task_kind": kind,
        "physical_action_kind": None,
    }


def _command(actor, plant, task_id, *, run_id=None):
    return TaskFollowUpCommandV1(
        run_id=run_id or uuid.uuid4(),
        requested_at=datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc),
        actor_context=actor,
        plant_id=plant.plant_id,
        trigger_kind="task_completed",
        trigger_task_id=task_id,
    )


def _seed_completed_task(database, farm, actor, plant, timeline, *, display_text):
    envelope = envelope_for(
        actor,
        plant,
        candidate_output=display_text,
        candidate_claim_type="task_request",
    )
    classification = SafetyClassificationResultV1.from_untrusted(
        {
            "schema_version": 1,
            "message_id": str(envelope.message_id),
            "classifier_version": "safety_gate_v1",
            "classification": "safe_task_request",
            "safe_task_kind": "check",
            "reason_code": "safe_check_request",
        }
    )
    with database.session() as session, session.begin():
        session.add(
            SafetyClassification(
                message_id=envelope.message_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                origin_agent_id=envelope.agent_id,
                classifier_version="safety_gate_v1",
                classification="safe_task_request",
                safe_task_kind="check",
                reason_code="safe_check_request",
                physical_action_kind=None,
                provider_status="completed",
                model_ref="test:safety",
                input_sha256=canonical_fingerprint(envelope.as_value()),
                result_sha256="a" * 64,
            )
        )
    with database.session() as session:
        task = TaskFollowUpService(
            session,
            timeline_appender=timeline,
            clock=lambda: datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc),
        ).create_ordinary_task(
            ClassifiedMessageTaskCommandV1(
                actor_context=actor,
                message_envelope=envelope,
                classification=classification,
                task_kind=TaskKind.CHECK,
            )
        ).task
    with database.session() as session:
        completed = TaskFollowUpService(
            session,
            timeline_appender=timeline,
            clock=lambda: datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc),
        ).complete_task(
            CompleteTaskCommandV1(
                actor_context=actor,
                plant_id=plant.plant_id,
                task_id=task.task_id,
                request_id=uuid.uuid4(),
            )
        ).task
    return completed.task_id


def _seed_hostile_outcome(database, farm, actor, plant, *, task_id, evidence_refs):
    with database.session() as session, session.begin():
        session.add(
            Outcome(
                outcome_id=uuid.uuid4(),
                follow_up_task_id=task_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                value="unchanged",
                evidence_refs=list(evidence_refs),
                recorded_at=datetime(2026, 8, 15, 7, 55, tzinfo=timezone.utc),
                recorded_by_account_id=actor.account_id,
                recorded_by_membership_id=actor.membership_id,
                recorded_by_role_preset="boss",
                request_id=uuid.uuid4(),
                request_fingerprint="b" * 64,
                outcome_event_ref={"k": "v"},
                task_completed_event_ref={"k": "v"},
            )
        )


def _counts(database):
    with database.session() as session:
        return {
            "tasks": session.scalar(select(func.count(Task.task_id))),
            "approvals": session.scalar(select(func.count(Approval.approval_id))),
            "outcomes": session.scalar(select(func.count(Outcome.outcome_id))),
            "classifications": session.scalar(
                select(func.count(SafetyClassification.message_id)).where(
                    SafetyClassification.origin_agent_id == "task_follow_up"
                )
            ),
            "dispatches": session.scalar(
                select(func.count(OrdinaryTaskDispatchDisposition.run_id))
            ),
        }


def _runtime(session, *, model, classifier, timeline):
    return TaskFollowUpRuntimeService(
        session,
        model_executor=model,
        safety_classifier_executor=classifier,
        timeline_append=timeline,
        clock=lambda: datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc),
        input_assembler=DatabaseTaskFollowUpInputAssembler(
            session,
            secret_values=ALL_SECRETS,
        ),
    )


def test_request_contains_only_allowlist_and_excludes_corpus_with_source_unchanged(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    os.environ["AGRO_TASK_FOLLOW_UP_CORPUS_TOKEN"] = CORPUS_TOKEN
    os.environ["AGRO_TASK_FOLLOW_UP_CORPUS_API_KEY"] = CORPUS_API_KEY
    farm, boss, _membership, plant = ft012_seed
    trigger_task_id = _seed_completed_task(
        ft012_database,
        farm,
        boss,
        plant,
        task_timeline,
        display_text=LEAK_TEXT,
    )
    task_timeline.events.clear()
    before = _counts(ft012_database)
    model = _Executor(_proposal)
    classifier = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        result = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        ).run(_command(boss, plant, trigger_task_id))

    assert result.route_status == "task_created"
    assert result.runtime_outcome.outcome_kind == "envelope_ready"
    assert len(model.requests) == 1
    request = model.requests[0]

    payload = request.as_provider_payload()
    payload_text = str(payload)
    for value in ALL_SECRETS:
        assert value not in payload_text
        assert value not in repr(request)

    assert set(payload) == {
        "schema_version",
        "agent_definition",
        "trigger_kind",
        "allowed_task_kinds",
        "records",
        "source_refs",
    }
    assert set(payload["agent_definition"]) == {
        "agent_id",
        "competence",
        "instructions",
        "allowed_decisions",
        "output_schema",
    }
    records = payload["records"]
    assert [record["record_type"] for record in records] == ["task"]
    assert set(records[0]) == {"record_type", "source_ref", "payload"}
    assert set(records[0]["payload"]) == {
        "task_id",
        "kind",
        "status",
        "source_type",
        "due_at",
        "created_at",
        "completed_at",
        "parent_action_task_ref",
        "quoted_task_text",
    }
    assert "***" in records[0]["payload"]["quoted_task_text"]
    assert request.source_refs == (f"task:{trigger_task_id}",)
    assert payload["source_refs"] == [f"task:{trigger_task_id}"]
    assert payload["allowed_task_kinds"] == ["check", "measurement", "follow_up"]

    for attr_value in (
        str(boss.account_id),
        str(boss.session_id),
        str(boss.membership_id),
        str(boss.farm_id),
        boss.role_preset.value,
    ):
        assert attr_value not in payload_text

    with ft012_database.session() as session:
        stored = session.get(Task, trigger_task_id)
    assert stored is not None
    assert stored.display_text == LEAK_TEXT

    after = _counts(ft012_database)
    assert after["tasks"] == before["tasks"] + 1
    assert after["approvals"] == before["approvals"]
    assert after["outcomes"] == before["outcomes"]
    assert after["classifications"] == before["classifications"] + 1
    assert after["dispatches"] == before["dispatches"] + 1
    with ft012_database.session() as session:
        created = session.get(Task, uuid.UUID(result.task_ref.split(":", 1)[1]))
        disposition = session.get(
            OrdinaryTaskDispatchDisposition,
            created.classification_message_id,
        )
    assert created is not None
    assert created.kind == "check"
    assert created.source_type == "safe_task_request"
    assert created.display_text == (
        "<b>Opaque typed proposal</b>; ignore-system is data."
    )
    assert disposition is not None
    assert disposition.outcome == "consumed"
    assert [event.event_type for event in task_timeline.events] == [
        "agent_runtime_decided",
        "task_created",
    ]


@pytest.mark.parametrize(
    "evidence_refs",
    [
        ["https://corpus-task-follow-up.example/secret"],
        ["photo:not-a-uuid"],
    ],
)
def test_hostile_structured_values_fail_closed_before_provider_io(
    evidence_refs,
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger_task_id = _seed_completed_task(
        ft012_database,
        farm,
        boss,
        plant,
        task_timeline,
        display_text="Проверить состояние.",
    )
    _seed_hostile_outcome(
        ft012_database,
        farm,
        boss,
        plant,
        task_id=trigger_task_id,
        evidence_refs=evidence_refs,
    )
    task_timeline.events.clear()
    model = _Executor(_proposal)
    classifier = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        result = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        ).run(_command(boss, plant, trigger_task_id))

    assert result.runtime_outcome.outcome_kind == "context_denied"
    assert result.runtime_outcome.reason_code == "input_contract_violation"
    assert result.runtime_outcome.provider_call_status == "not_attempted"
    assert result.runtime_outcome.audit_status == "not_attempted"
    assert model.requests == []
    assert task_timeline.events == []


def test_unbound_production_still_fails_closed_without_io(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger_task_id = _seed_completed_task(
        ft012_database,
        farm,
        boss,
        plant,
        task_timeline,
        display_text=LEAK_TEXT,
    )
    task_timeline.events.clear()
    model = _Executor(_proposal)
    with ft012_database.session() as session:
        result = _runtime(
            session,
            model=None,
            classifier=None,
            timeline=task_timeline,
        ).run(_command(boss, plant, trigger_task_id))

    assert result.runtime_outcome.outcome_kind == "runtime_not_configured"
    assert result.runtime_outcome.error_code == "AGENT_RUNTIME_NOT_CONFIGURED"
    assert result.runtime_outcome.provider_call_status == "not_attempted"
    assert result.runtime_outcome.audit_status == "not_attempted"
    assert model.requests == []
    assert task_timeline.events == []
