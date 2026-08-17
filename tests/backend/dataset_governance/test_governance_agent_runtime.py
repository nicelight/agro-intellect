from __future__ import annotations

import hashlib
import json
import uuid

import pytest
from sqlalchemy import func, select

from backend.app.dataset_governance import (
    DatasetAgentCommandV1,
    DatasetAgentRuntimeOutcomeV1,
    DatasetCandidate,
    DatasetGovernanceAssessmentV1,
    DatasetGovernanceProviderRequestV1,
    DatasetGovernanceRuntimeService,
    DatasetGovernanceRuntimeValidationError,
    DatasetGovernanceService,
    dataset_agent_command_sha256,
)
from tests.backend.dataset_governance.conftest import (
    FT014_NOW,
    TimelineRecorder,
    make_creation_command,
)
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    grant_access,
    revoke_access,
)

CORPUS_DB_PASSWORD = "corpus-ft079-db-pw-7h2k"
CORPUS_BEARER = "corpus-ft079-bearer-5c3m"
CORPUS_COOKIE = "corpus-ft079-cookie-8p1t"
CORPUS_SESSION = "corpus-ft079-session-3m6z"
CORPUS_TOKEN = "corpus-ft079-token-9x4f"
CORPUS_API_KEY = "corpus-ft079-api-key-2v8n"
FORBIDDEN_HEADERS = [
    f"session={CORPUS_COOKIE}; HttpOnly",
    f"Authorization: Bearer {CORPUS_BEARER}",
    "corpus-ft079-ui-feed-entry-4q1r",
    "corpus-ft079-provider-history-6t9c",
]
ALL_SECRETS = [
    CORPUS_DB_PASSWORD,
    CORPUS_BEARER,
    CORPUS_COOKIE,
    CORPUS_SESSION,
    CORPUS_TOKEN,
    CORPUS_API_KEY,
    *FORBIDDEN_HEADERS,
]

HOSTILE_KIND = (
    f"photo note=dbpw:{CORPUS_DB_PASSWORD} bearer:{CORPUS_BEARER} "
    f"cookieval:{CORPUS_COOKIE} sess:{CORPUS_SESSION} "
    f"token={CORPUS_TOKEN} key={CORPUS_API_KEY} "
    + " ".join(FORBIDDEN_HEADERS)
)


class _Executor:
    model_ref = "test_provider:governance_v1"

    def __init__(self, result: dict[str, object], *, before_return=None) -> None:
        self.result = result
        self.before_return = before_return
        self.requests = []

    def execute(self, request: DatasetGovernanceProviderRequestV1):
        self.requests.append(request)
        if self.before_return is not None:
            self.before_return()
        return self.result


class _FailingExecutor:
    model_ref = "test_provider:governance_v1"

    def __init__(self) -> None:
        self.requests = []

    def execute(self, request: DatasetGovernanceProviderRequestV1):
        self.requests.append(request)
        raise TimeoutError("provider unreachable")


def _create_candidate(
    database,
    actor,
    plant,
    *,
    source_kind: str = "photo_catalog_item",
    source_ref: uuid.UUID | None = None,
) -> uuid.UUID:
    with database.session() as session, session.begin():
        recorder = TimelineRecorder()
        service = DatasetGovernanceService(session, timeline_appender=recorder)
        result = service.record_dataset_evidence(
            make_creation_command(
                actor,
                plant_id=plant.plant_id,
                source_kind=source_kind,
                source_ref=source_ref,
            )
        )
        session.flush()
        return result.candidate_id


def _command(actor, *, candidate_id: uuid.UUID, plant_id: uuid.UUID) -> DatasetAgentCommandV1:
    return DatasetAgentCommandV1(
        run_id=uuid.uuid4(),
        requested_at=FT014_NOW,
        actor_context=actor,
        plant_id=plant_id,
        candidate_id=candidate_id,
        agent_id="dataset_governance",
        trigger_kind="dataset_candidate_created",
    )


def _assessment(run_id: uuid.UUID, **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": 1,
        "run_id": str(run_id),
        "assessment": "eligible_for_curator_review",
        "violation_codes": [],
        "assessment_notes": "Eligible for curator review.",
    }
    value.update(overrides)
    return value


def _service(session, executor, recorder) -> DatasetGovernanceRuntimeService:
    return DatasetGovernanceRuntimeService(
        session,
        model_executor=executor,
        timeline_append=recorder,
    )


def test_request_is_exact_and_redacted_with_fingerprint(ft014_database, ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    expected_fingerprint = _manual_fingerprint(command)
    assert command.command_sha256 == expected_fingerprint
    assert dataset_agent_command_sha256(command) == expected_fingerprint

    executor = _Executor(_assessment(command.run_id))
    with ft014_database.session() as session:
        _service(session, executor, TimelineRecorder()).invoke(command)

    assert len(executor.requests) == 1
    payload = executor.requests[0].as_provider_payload()
    assert list(payload) == [
        "schema_version",
        "run_id",
        "requested_at",
        "agent_id",
        "plant_id",
        "candidate_id",
        "candidate",
        "policy_context",
    ]
    assert payload["schema_version"] == 1
    assert payload["run_id"] == str(command.run_id)
    assert payload["requested_at"] == "2026-08-10T07:00:00Z"
    assert payload["agent_id"] == "dataset_governance"
    assert payload["plant_id"] == str(plant.plant_id)
    assert payload["candidate_id"] == str(candidate_id)
    assert payload["candidate"] == {
        "candidate_status": "candidate",
        "candidate_origin": "raw",
        "quality_tier": "standard",
        "follow_up_seen": False,
        "corrected": False,
        "evidence_ref_count": 1,
        "evidence_kinds": ["photo"],
    }
    assert payload["policy_context"] == {
        "strong_evidence_policy": "ft014_strong_evidence_v1",
        "agent_labeled_guard": True,
    }
    rendered = json.dumps(payload)
    assert "actor" not in rendered
    assert "session" not in rendered
    assert "account_id" not in rendered
    assert "membership_id" not in rendered
    assert "evidence_refs" not in rendered
    assert "can_train_on" not in rendered
    assert "split" not in rendered


def test_command_rejects_unknown_agent_and_trigger(ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    with pytest.raises(DatasetGovernanceRuntimeValidationError):
        DatasetAgentCommandV1(
            run_id=uuid.uuid4(),
            requested_at=FT014_NOW,
            actor_context=boss,
            plant_id=plant.plant_id,
            candidate_id=uuid.uuid4(),
            agent_id="unknown_agent",
            trigger_kind="dataset_candidate_created",
        )
    with pytest.raises(DatasetGovernanceRuntimeValidationError):
        DatasetAgentCommandV1(
            run_id=uuid.uuid4(),
            requested_at=FT014_NOW,
            actor_context=boss,
            plant_id=plant.plant_id,
            candidate_id=uuid.uuid4(),
            agent_id="dataset_governance",
            trigger_kind="page_read",
        )


def test_assessment_rejects_assignment_and_unknown_values(ft014_database, ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)

    def request_for(run_id):
        with ft014_database.session() as session:
            executor = _Executor(_assessment(run_id))
            _service(session, executor, TimelineRecorder()).invoke(command)
            return executor.requests[0]

    request = request_for(command.run_id)
    forbidden = [
        {"candidate_status": "confirmed"},
        {"quality_tier": "gold"},
        {"split": "train"},
        {"confirmation_source": "curator_auto"},
        {"can_train_on": True},
        {"curator_decision": "selected"},
    ]
    for extra in forbidden:
        value = _assessment(command.run_id)
        value.update(extra)
        with pytest.raises(DatasetGovernanceRuntimeValidationError):
            DatasetGovernanceAssessmentV1.from_untrusted(value, request=request)
    for bad in [
        {"assessment": "unknown"},
        {"run_id": str(uuid.uuid4())},
        {"violation_codes": ["unknown_code"]},
        {"schema_version": 2},
        {"violation_codes": ["weak_evidence"]},
    ]:
        value = _assessment(command.run_id)
        value.update(bad)
        with pytest.raises(DatasetGovernanceRuntimeValidationError):
            DatasetGovernanceAssessmentV1.from_untrusted(value, request=request)


def test_success_returns_advisory_ready_with_single_redacted_event(
    ft014_database,
    ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    executor = _Executor(
        _assessment(
            command.run_id,
            assessment="policy_violation",
            violation_codes=["weak_evidence"],
        )
    )

    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(command)

    assert isinstance(outcome, DatasetAgentRuntimeOutcomeV1)
    assert outcome.outcome_kind == "advisory_ready"
    assert outcome.status == "advisory_ready"
    assert outcome.agent_id == "dataset_governance"
    assert outcome.candidate_id == candidate_id
    assert outcome.reason_code == "advisory_ready"
    assert outcome.error_code is None
    assert outcome.provider_call_status == "completed"
    assert outcome.audit_status == "appended"
    assert outcome.curator_gate_result == "not_applicable"
    assert outcome.model_ref == "test_provider:governance_v1"
    assert outcome.validated_result is not None
    assert outcome.validated_result.assessment == "policy_violation"
    assert outcome.validated_result.violation_codes == ("weak_evidence",)

    assert len(recorder.events) == 1
    event = recorder.events[0]
    assert event.event_type == "dataset_agent_runtime_decided"
    assert event.source_type == "dataset_agent_attempt"
    assert event.source_id == command.run_id
    assert event.source_refs == {"candidate_refs": [f"dataset_candidate:{candidate_id}"]}
    payload = event.payload_summary
    assert payload["agent_id"] == "dataset_governance"
    assert payload["outcome_kind"] == "advisory_ready"
    assert payload["status"] == "advisory_ready"
    assert payload["provider_call_status"] == "completed"
    assert payload["curator_gate_result"] == "not_applicable"
    assert payload["candidate_ref_count"] == 1
    assert payload["advisory_persisted"] is False
    assert payload["lifecycle_changed"] is False
    assert "assessment_notes" not in payload
    assert "candidate_status" not in payload

    with ft014_database.session() as session:
        count = session.scalar(select(func.count(DatasetCandidate.candidate_id)))
    assert count == 1


def test_context_denied_appends_empty_refs_event_and_blocks_provider(
    ft014_database,
    ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    executor = _Executor(_assessment(command.run_id))

    engineer, _ = create_actor(ft014_database, _farm, "engineer")
    denied = DatasetAgentCommandV1(
        run_id=uuid.uuid4(),
        requested_at=FT014_NOW,
        actor_context=engineer,
        plant_id=plant.plant_id,
        candidate_id=candidate_id,
        agent_id="dataset_governance",
        trigger_kind="manual_review",
    )
    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(denied)

    assert outcome.outcome_kind == "context_denied"
    assert outcome.status == "blocked"
    assert outcome.validated_result is None
    assert outcome.model_ref is None
    assert outcome.provider_call_status == "not_attempted"
    assert outcome.audit_status == "appended"
    assert outcome.error_code == "dataset_agent_context_denied"
    assert executor.requests == []
    assert len(recorder.events) == 1
    assert recorder.events[0].source_refs == {"candidate_refs": []}
    assert recorder.events[0].payload_summary["candidate_ref_count"] == 0


def test_unknown_candidate_is_context_denied_with_empty_refs(
    ft014_database,
    ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    command = _command(boss, candidate_id=uuid.uuid4(), plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    with ft014_database.session() as session:
        outcome = _service(session, _Executor(_assessment(command.run_id)), recorder).invoke(
            command
        )
    assert outcome.outcome_kind == "context_denied"
    assert outcome.status == "blocked"
    assert len(recorder.events) == 1
    assert recorder.events[0].source_refs == {"candidate_refs": []}
    assert recorder.events[0].payload_summary["candidate_ref_count"] == 0


def test_unbound_production_fails_closed_with_audit_and_no_executor(
    ft014_database,
    ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()

    with ft014_database.session() as session:
        outcome = DatasetGovernanceRuntimeService(
            session,
            model_executor=None,
            timeline_append=recorder,
        ).invoke(command)

    assert outcome.outcome_kind == "runtime_not_configured"
    assert outcome.status == "failed"
    assert outcome.model_ref is None
    assert outcome.provider_call_status == "not_attempted"
    assert outcome.audit_status == "appended"
    assert outcome.error_code == "dataset_agent_runtime_not_configured"
    assert len(recorder.events) == 1
    assert recorder.events[0].source_refs == {
        "candidate_refs": [f"dataset_candidate:{candidate_id}"]
    }
    assert recorder.events[0].payload_summary["candidate_ref_count"] == 1


def test_provider_failure_is_audited_failed_not_silence(ft014_database, ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    executor = _FailingExecutor()

    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(command)

    assert executor.requests
    assert outcome.outcome_kind == "provider_failed"
    assert outcome.status == "failed"
    assert outcome.validated_result is None
    assert outcome.provider_call_status == "failed"
    assert outcome.audit_status == "appended"
    assert outcome.error_code == "dataset_agent_provider_failed"
    assert len(recorder.events) == 1


def test_invalid_output_is_blocked_with_audit(ft014_database, ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    invalid = _assessment(command.run_id)
    invalid["run_id"] = str(uuid.uuid4())
    executor = _Executor(invalid)

    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(command)

    assert outcome.outcome_kind == "output_invalid"
    assert outcome.status == "blocked"
    assert outcome.validated_result is None
    assert outcome.provider_call_status == "completed"
    assert outcome.audit_status == "appended"
    assert outcome.error_code == "dataset_agent_output_invalid"
    assert len(recorder.events) == 1
    assert recorder.events[0].payload_summary["outcome_kind"] == "output_invalid"


def test_archive_during_io_is_post_io_guard_denied_with_audit(
    ft014_database,
    ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    executor = _Executor(
        _assessment(command.run_id),
        before_return=lambda: archive_plant(
            ft014_database, boss, plant_id=plant.plant_id
        ),
    )

    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(command)

    assert outcome.outcome_kind == "post_io_guard_denied"
    assert outcome.status == "blocked"
    assert outcome.validated_result is None
    assert outcome.provider_call_status == "completed"
    assert outcome.audit_status == "appended"
    assert outcome.error_code == "dataset_agent_post_io_guard_denied"
    assert len(recorder.events) == 1


def test_revoke_during_io_is_post_io_guard_denied(ft014_database, ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    engineer, engineer_membership = create_actor(ft014_database, _farm, "engineer")
    grant_access(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = DatasetAgentCommandV1(
        run_id=uuid.uuid4(),
        requested_at=FT014_NOW,
        actor_context=engineer,
        plant_id=plant.plant_id,
        candidate_id=candidate_id,
        agent_id="dataset_governance",
        trigger_kind="manual_review",
    )
    recorder = TimelineRecorder()
    executor = _Executor(
        _assessment(command.run_id),
        before_return=lambda: revoke_access(
            ft014_database,
            boss,
            plant_id=plant.plant_id,
            membership_id=engineer_membership.membership_id,
        ),
    )

    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(command)

    assert outcome.outcome_kind == "post_io_guard_denied"
    assert outcome.status == "blocked"
    assert outcome.audit_status == "appended"
    assert len(recorder.events) == 1


def test_candidate_version_change_during_io_is_post_io_guard_denied(
    ft014_database,
    ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()

    def bump_version():
        with ft014_database.session() as session, session.begin():
            row = session.get(DatasetCandidate, candidate_id)
            row.record_version += 1

    executor = _Executor(_assessment(command.run_id), before_return=bump_version)
    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(command)

    assert outcome.outcome_kind == "post_io_guard_denied"
    assert outcome.status == "blocked"
    assert outcome.validated_result is None
    assert outcome.audit_status == "appended"
    assert len(recorder.events) == 1


def test_audit_failure_discards_result_and_event_ref(ft014_database, ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder(fail_on="dataset_agent_runtime_decided")
    executor = _Executor(_assessment(command.run_id))

    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(command)

    assert outcome.outcome_kind == "audit_failed"
    assert outcome.status == "failed"
    assert outcome.validated_result is None
    assert outcome.event_ref is None
    assert outcome.audit_status == "failed"
    assert outcome.error_code == "dataset_agent_audit_failed"
    assert recorder.events == []


def test_runtime_module_has_no_generic_publication_imports():
    import pathlib

    root = pathlib.Path("backend/app/dataset_governance")
    source = "\n".join(
        (root / "runtime.py").read_text(encoding="utf-8")
        + (root / "runtime_contracts.py").read_text(encoding="utf-8")
    )
    for forbidden in (
        "MessageEnvelope",
        "SafetyClassification",
        "agent_chat",
        "bus_event",
        "ui_feed",
        "AgentRuntimeOutcomeV1",
        "ProviderRequestV1",
    ):
        assert forbidden not in source


def _manual_fingerprint(command: DatasetAgentCommandV1) -> str:
    actor = command.actor_context
    payload = {
        "schema_version": command.schema_version,
        "run_id": str(command.run_id),
        "requested_at": "2026-08-10T07:00:00Z",
        "request_id": actor.request_id,
        "session_id": str(actor.session_id),
        "account_id": str(actor.account_id),
        "farm_id": str(actor.farm_id),
        "membership_id": str(actor.membership_id),
        "plant_id": str(command.plant_id),
        "candidate_id": str(command.candidate_id),
        "agent_id": command.agent_id,
        "trigger_kind": command.trigger_kind,
    }
    compact = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(compact.encode("utf-8")).hexdigest()


def _poison_candidate(database, candidate_id: uuid.UUID) -> None:
    with database.session() as session, session.begin():
        row = session.get(DatasetCandidate, candidate_id)
        row.evidence_refs = [
            {"kind": "photo", "ref": str(uuid.uuid4())},
            {"kind": HOSTILE_KIND, "ref": str(uuid.uuid4())},
        ]


def _auth_context_values(actor) -> list[str]:
    return [
        str(actor.account_id),
        str(actor.session_id),
        str(actor.membership_id),
        str(actor.farm_id),
        actor.role_preset.value,
    ]


def test_ft015_ac019_corpus_never_reaches_governance_request_with_source_unchanged(
    ft014_database,
    ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    _poison_candidate(ft014_database, candidate_id)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    executor = _Executor(_assessment(command.run_id))

    with ft014_database.session() as session:
        outcome = DatasetGovernanceRuntimeService(
            session,
            model_executor=executor,
            timeline_append=recorder,
            secret_values=tuple(ALL_SECRETS),
        ).invoke(command)

    assert outcome.outcome_kind == "advisory_ready"
    assert len(executor.requests) == 1
    payload = executor.requests[0].as_provider_payload()
    assert list(payload) == [
        "schema_version",
        "run_id",
        "requested_at",
        "agent_id",
        "plant_id",
        "candidate_id",
        "candidate",
        "policy_context",
    ]
    payload_text = json.dumps(payload, sort_keys=True)
    for raw in ALL_SECRETS:
        assert raw not in payload_text
    for attr_value in _auth_context_values(boss):
        assert attr_value not in payload_text
    for forbidden in (
        "actor",
        "account_id",
        "session_id",
        "membership_id",
        "role_preset",
        "evidence_refs",
        "provider_history",
        "ui_feed",
    ):
        assert forbidden not in payload_text
    assert "***" in str(payload["candidate"]["evidence_kinds"])
    assert payload["agent_id"] == "dataset_governance"

    with ft014_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
    assert row.evidence_refs == [
        {"kind": "photo", "ref": row.evidence_refs[0]["ref"]},
        {"kind": HOSTILE_KIND, "ref": row.evidence_refs[1]["ref"]},
    ]
    assert row.evidence_refs[1]["kind"] == HOSTILE_KIND
    assert row.record_version == 1
    assert row.candidate_status == "candidate"
    assert row.can_train_on is False


def test_ft015_ac019_hostile_kind_collapse_is_context_denied_with_zero_io(
    ft014_database,
    ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    with ft014_database.session() as session, session.begin():
        row = session.get(DatasetCandidate, candidate_id)
        row.evidence_refs = [
            {"kind": CORPUS_TOKEN, "ref": str(uuid.uuid4())},
            {"kind": FORBIDDEN_HEADERS[2], "ref": str(uuid.uuid4())},
        ]
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    executor = _Executor(_assessment(command.run_id))

    with ft014_database.session() as session:
        outcome = DatasetGovernanceRuntimeService(
            session,
            model_executor=executor,
            timeline_append=recorder,
            secret_values=tuple(ALL_SECRETS),
        ).invoke(command)

    assert outcome.outcome_kind == "context_denied"
    assert outcome.status == "blocked"
    assert outcome.provider_call_status == "not_attempted"
    assert outcome.error_code == "dataset_agent_context_denied"
    assert executor.requests == []
    assert len(recorder.events) == 1
    assert recorder.events[0].source_refs == {"candidate_refs": []}
