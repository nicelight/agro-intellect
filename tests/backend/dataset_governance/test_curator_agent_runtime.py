"""FT-014-AC-013 Training Data Curator advisory-only runtime matrix.

The registered provider-neutral curator route (AD-011) runs only through
``TrainingDataCuratorProviderRequestV1`` / ``TrainingDataCuratorDecisionV1``.
Deferred/rejected results persist only the exact current-run advisory
allowlist; ``silent`` persists nothing; unbound production fails closed with
no fake/canned/fallback; and every pre/post-I/O guard, audit, and validation
branch returns its canonical outcome with zero partial lifecycle or
trainability authority and no MessageEnvelope/Safety/Bus/UI effect.
"""

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
    DatasetGovernanceRuntimeValidationError,
    DatasetGovernanceService,
    DatasetGovernanceValidationError,
    TrainingDataCuratorDecisionV1,
    TrainingDataCuratorProviderRequestV1,
    TrainingDataCuratorRuntimeService,
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


class _Executor:
    model_ref = "test_provider:curator_v1"

    def __init__(self, result: dict[str, object], *, before_return=None) -> None:
        self.result = result
        self.before_return = before_return
        self.requests = []

    def execute(self, request: TrainingDataCuratorProviderRequestV1):
        self.requests.append(request)
        if self.before_return is not None:
            self.before_return()
        return self.result


class _FailingExecutor:
    model_ref = "test_provider:curator_v1"

    def __init__(self) -> None:
        self.requests = []

    def execute(self, request: TrainingDataCuratorProviderRequestV1):
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
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
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
        agent_id="training_data_curator",
        trigger_kind="manual_review",
    )


def _decision(run_id: uuid.UUID, **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": 1,
        "run_id": str(run_id),
        "curator_decision": "deferred",
        "curator_notes_ref": None,
    }
    value.update(overrides)
    return value


def _service(session, executor, recorder) -> TrainingDataCuratorRuntimeService:
    return TrainingDataCuratorRuntimeService(
        session,
        model_executor=executor,
        timeline_append=recorder,
    )


def _row(database, candidate_id: uuid.UUID) -> DatasetCandidate:
    with database.session() as session:
        return session.get(DatasetCandidate, candidate_id)


# ---------------------------------------------------------------------------
# Strict request and result contracts
# ---------------------------------------------------------------------------


def test_request_is_exact_and_redacted_with_fingerprint(ft014_database, ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    assert command.command_sha256 == dataset_agent_command_sha256(command)
    assert len(command.command_sha256) == 64

    executor = _Executor(_decision(command.run_id))
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
    assert payload["agent_id"] == "training_data_curator"
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
    for forbidden in (
        "actor",
        "session",
        "account_id",
        "membership_id",
        "evidence_refs",
        "can_train_on",
        "split",
        "confirmation_source",
    ):
        assert forbidden not in rendered


def test_command_rejects_unknown_agent_for_curator_runtime(ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    with pytest.raises(DatasetGovernanceRuntimeValidationError):
        DatasetAgentCommandV1(
            run_id=uuid.uuid4(),
            requested_at=FT014_NOW,
            actor_context=boss,
            plant_id=plant.plant_id,
            candidate_id=uuid.uuid4(),
            agent_id="unknown_agent",
            trigger_kind="manual_review",
        )
    with pytest.raises(DatasetGovernanceRuntimeValidationError):
        DatasetAgentCommandV1(
            run_id=uuid.uuid4(),
            requested_at=FT014_NOW,
            actor_context=boss,
            plant_id=plant.plant_id,
            candidate_id=uuid.uuid4(),
            agent_id="training_data_curator",
            trigger_kind="page_read",
        )


def test_decision_contract_rejects_assignment_and_unknown_values(
    ft014_database, ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)

    with ft014_database.session() as session:
        executor = _Executor(_decision(command.run_id))
        _service(session, executor, TimelineRecorder()).invoke(command)
        request = executor.requests[0]

    forbidden = [
        {"candidate_status": "confirmed"},
        {"quality_tier": "gold"},
        {"split": "train"},
        {"confirmation_source": "curator_auto"},
        {"can_train_on": True},
        {"evidence_refs": [{"kind": "photo", "ref": str(uuid.uuid4())}]},
        {"assessment": "policy_violation"},
    ]
    for extra in forbidden:
        value = _decision(command.run_id)
        value.update(extra)
        with pytest.raises(DatasetGovernanceRuntimeValidationError):
            TrainingDataCuratorDecisionV1.from_untrusted(value, request=request)
    for bad in [
        {"curator_decision": "unknown"},
        {"run_id": str(uuid.uuid4())},
        {"schema_version": 2},
        {"curator_decision": "silent", "curator_notes_ref": "must stay silent"},
        {"curator_notes_ref": "x" * 201},
    ]:
        value = _decision(command.run_id)
        value.update(bad)
        with pytest.raises(DatasetGovernanceRuntimeValidationError):
            TrainingDataCuratorDecisionV1.from_untrusted(value, request=request)


# ---------------------------------------------------------------------------
# Advisory-only persistence: deferred / rejected / silent
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("decision", ["deferred", "rejected"])
def test_non_selected_result_persists_only_current_run_advisory_allowlist(
    ft014_database, ft014_seed, decision,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    executor = _Executor(
        _decision(command.run_id, curator_decision=decision, curator_notes_ref="note")
    )

    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(command)
        session.commit()

    assert isinstance(outcome, DatasetAgentRuntimeOutcomeV1)
    assert outcome.outcome_kind == "advisory_ready"
    assert outcome.status == "advisory_ready"
    assert outcome.curator_gate_result == "not_requested"
    assert outcome.audit_status == "appended"
    assert outcome.error_code is None
    assert outcome.validated_result.curator_decision == decision

    row = _row(ft014_database, candidate_id)
    assert row.curator_decision == decision
    assert row.curator_notes_ref == "note"
    assert row.curator_run_id == command.run_id
    assert row.curator_command_sha256 == command.command_sha256
    assert row.curator_recorded_at is not None
    assert row.record_version == 2
    assert row.candidate_status == "candidate"
    assert row.confirmation_source is None
    assert row.can_train_on is False
    assert len(row.evidence_refs) == 1

    assert len(recorder.events) == 1
    assert recorder.events[0].event_type == "dataset_agent_runtime_decided"
    assert recorder.events[0].source_refs == {
        "candidate_refs": [f"dataset_candidate:{candidate_id}"]
    }
    payload = recorder.events[0].payload_summary
    assert payload["agent_id"] == "training_data_curator"
    assert payload["outcome_kind"] == "advisory_ready"
    assert payload["curator_gate_result"] == "not_requested"
    assert payload["advisory_persisted"] is True
    assert payload["lifecycle_changed"] is False
    assert "curator_notes_ref" not in payload
    assert "candidate_status" not in payload


def test_silent_persists_nothing_and_returns_model_silent(ft014_database, ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    executor = _Executor(_decision(command.run_id, curator_decision="silent"))

    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(command)
        session.commit()

    assert outcome.outcome_kind == "model_silent"
    assert outcome.status == "silent"
    assert outcome.curator_gate_result == "not_requested"
    assert outcome.audit_status == "appended"
    assert outcome.validated_result.curator_decision == "silent"

    row = _row(ft014_database, candidate_id)
    assert row.curator_decision is None
    assert row.curator_notes_ref is None
    assert row.curator_run_id is None
    assert row.curator_command_sha256 is None
    assert row.curator_recorded_at is None
    assert row.record_version == 1
    assert row.candidate_status == "candidate"
    assert row.can_train_on is False

    assert len(recorder.events) == 1
    assert recorder.events[0].payload_summary["advisory_persisted"] is False
    assert recorder.events[0].payload_summary["lifecycle_changed"] is False


# ---------------------------------------------------------------------------
# Unbound production / provider / validation branches
# ---------------------------------------------------------------------------


def test_unbound_production_fails_closed_with_no_fake_or_fallback(
    ft014_database, ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()

    with ft014_database.session() as session:
        outcome = TrainingDataCuratorRuntimeService(
            session, model_executor=None, timeline_append=recorder
        ).invoke(command)
        session.commit()

    assert outcome.outcome_kind == "runtime_not_configured"
    assert outcome.status == "failed"
    assert outcome.model_ref is None
    assert outcome.provider_call_status == "not_attempted"
    assert outcome.audit_status == "appended"
    assert outcome.error_code == "dataset_agent_runtime_not_configured"
    assert outcome.curator_gate_result == "not_applicable"
    row = _row(ft014_database, candidate_id)
    assert row.curator_run_id is None
    assert row.record_version == 1
    assert len(recorder.events) == 1
    assert recorder.events[0].payload_summary["advisory_persisted"] is False


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
    assert outcome.curator_gate_result == "not_applicable"
    assert len(recorder.events) == 1


def test_invalid_output_is_blocked_with_audit(ft014_database, ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    invalid = _decision(command.run_id)
    invalid["run_id"] = str(uuid.uuid4())
    executor = _Executor(invalid)

    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(command)
        session.commit()

    assert outcome.outcome_kind == "output_invalid"
    assert outcome.status == "blocked"
    assert outcome.validated_result is None
    assert outcome.provider_call_status == "completed"
    assert outcome.audit_status == "appended"
    assert outcome.error_code == "dataset_agent_output_invalid"
    row = _row(ft014_database, candidate_id)
    assert row.curator_run_id is None
    assert row.record_version == 1
    assert len(recorder.events) == 1


# ---------------------------------------------------------------------------
# Pre / post-I/O guard branches
# ---------------------------------------------------------------------------


def test_context_denied_appends_empty_refs_event_and_blocks_provider(
    ft014_database, ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    engineer, _membership = create_actor(ft014_database, _farm, "engineer")
    denied = _command(engineer, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    executor = _Executor(_decision(denied.run_id))

    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(denied)

    assert outcome.outcome_kind == "context_denied"
    assert outcome.status == "blocked"
    assert outcome.validated_result is None
    assert outcome.model_ref is None
    assert outcome.provider_call_status == "not_attempted"
    assert outcome.error_code == "dataset_agent_context_denied"
    assert executor.requests == []
    assert len(recorder.events) == 1
    assert recorder.events[0].source_refs == {"candidate_refs": []}
    assert recorder.events[0].payload_summary["candidate_ref_count"] == 0


def test_unknown_candidate_is_context_denied(ft014_database, ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    command = _command(boss, candidate_id=uuid.uuid4(), plant_id=plant.plant_id)
    recorder = TimelineRecorder()

    with ft014_database.session() as session:
        outcome = _service(
            session, _Executor(_decision(command.run_id)), recorder
        ).invoke(command)

    assert outcome.outcome_kind == "context_denied"
    assert len(recorder.events) == 1
    assert recorder.events[0].source_refs == {"candidate_refs": []}


def test_archive_during_io_is_post_io_guard_denied(ft014_database, ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    executor = _Executor(
        _decision(command.run_id),
        before_return=lambda: archive_plant(
            ft014_database, boss, plant_id=plant.plant_id
        ),
    )

    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(command)
        session.commit()

    assert outcome.outcome_kind == "post_io_guard_denied"
    assert outcome.status == "blocked"
    assert outcome.validated_result is None
    assert outcome.provider_call_status == "completed"
    assert outcome.error_code == "dataset_agent_post_io_guard_denied"
    row = _row(ft014_database, candidate_id)
    assert row.curator_run_id is None
    assert row.record_version == 1
    assert len(recorder.events) == 1
    assert recorder.events[0].payload_summary["advisory_persisted"] is False


def test_revoke_during_io_is_post_io_guard_denied(ft014_database, ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    engineer, engineer_membership = create_actor(ft014_database, _farm, "engineer")
    grant_access(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    candidate_id = _create_candidate(ft014_database, engineer, plant)
    command = _command(engineer, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    executor = _Executor(
        _decision(command.run_id),
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
    assert outcome.audit_status == "appended"
    assert len(recorder.events) == 1


def test_candidate_version_change_during_io_is_post_io_guard_denied(
    ft014_database, ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()

    def bump_version():
        with ft014_database.session() as session, session.begin():
            row = session.get(DatasetCandidate, candidate_id)
            row.record_version += 1

    executor = _Executor(_decision(command.run_id), before_return=bump_version)
    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(command)

    assert outcome.outcome_kind == "post_io_guard_denied"
    assert outcome.validated_result is None
    assert outcome.audit_status == "appended"
    assert len(recorder.events) == 1


# ---------------------------------------------------------------------------
# Audit branch
# ---------------------------------------------------------------------------


def test_runtime_audit_failure_discards_result_and_event_ref(
    ft014_database, ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder(fail_on="dataset_agent_runtime_decided")
    executor = _Executor(_decision(command.run_id))

    with ft014_database.session() as session:
        outcome = _service(session, executor, recorder).invoke(command)
        session.commit()

    assert outcome.outcome_kind == "audit_failed"
    assert outcome.status == "failed"
    assert outcome.validated_result is None
    assert outcome.event_ref is None
    assert outcome.audit_status == "failed"
    assert outcome.error_code == "dataset_agent_audit_failed"
    row = _row(ft014_database, candidate_id)
    assert row.curator_run_id is None
    assert row.record_version == 1
    assert recorder.events == []


# ---------------------------------------------------------------------------
# Static anti-cheat: no generic publication / authority imports
# ---------------------------------------------------------------------------


def test_curator_runtime_has_no_generic_publication_imports():
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


def test_curator_never_writes_lifecycle_or_trainability_fields(
    ft014_database, ft014_seed,
):
    """A deferred/rejected result commits only advisory fields and the
    all-or-none run identity; status/tier/split/confirmation/trainability stay
    untouched."""
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()

    with ft014_database.session() as session:
        outcome = _service(
            session, _Executor(_decision(command.run_id)), recorder
        ).invoke(command)
        session.commit()

    assert outcome.outcome_kind == "advisory_ready"
    with ft014_database.session() as session:
        count = session.scalar(
            select(func.count(DatasetCandidate.candidate_id)).where(
                DatasetCandidate.candidate_id == candidate_id,
                DatasetCandidate.candidate_status == "candidate",
                DatasetCandidate.confirmation_source.is_(None),
                DatasetCandidate.quality_tier == "standard",
                DatasetCandidate.can_train_on.is_(False),
            )
        )
    assert count == 1


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
