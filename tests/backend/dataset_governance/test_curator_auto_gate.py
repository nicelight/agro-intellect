"""FT-014-AC-014 server-side curator gate matrix.

A current-run ``selected`` result plus strong canonical evidence atomically
confirms through ``curator_auto``; every weak/stale/gold/``agent_labeled``/
authority/audit/commit failure rolls the selected advisory and the lifecycle
change back together and leaves no reusable selected advisory. Model wording
never enters the policy evaluation.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app import AppSettings
from backend.app.dataset_governance import (
    CandidateStatus,
    ConfirmationSource,
    DatasetAgentCommandV1,
    DatasetCandidate,
    DatasetGovernanceService,
    QualityTier,
    TransitionDatasetCandidateCommandV1,
    TrainingDataCuratorProviderRequestV1,
    TrainingDataCuratorRuntimeService,
)
from backend.app.timeline import TimelineJsonlAppender
from tests.backend.dataset_governance.conftest import (
    FT014_NOW,
    TimelineRecorder,
    make_creation_command,
)
from tests.backend.dataset_governance.test_follow_up_evidence_association import (
    _association_command,
    _outcome_row,
    _photo,
)
from tests.backend.plant_operations.conftest import archive_plant

_DIGEST = "a" * 64


class _Executor:
    model_ref = "test_provider:curator_v1"

    def __init__(self, decision: str, *, before_return=None) -> None:
        self.decision = decision
        self.before_return = before_return
        self.requests = []

    def execute(self, request: TrainingDataCuratorProviderRequestV1):
        self.requests.append(request)
        if self.before_return is not None:
            self.before_return()
        return {
            "schema_version": 1,
            "run_id": str(request.run_id),
            "curator_decision": self.decision,
            "curator_notes_ref": None,
        }


def _create_photo_candidate(database, farm, boss, plant, *, origin: str = "raw"):
    """Create a production-shaped raw/standard photo candidate with an Outcome
    follow-up ref, so the strong-evidence policy precondition holds."""
    photo_id = _photo(database, farm, boss, plant)
    with database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        result = service.record_dataset_evidence(
            make_creation_command(boss, plant_id=plant.plant_id, source_ref=photo_id)
        )
        candidate_id = result.candidate_id
    refs = (f"photo_catalog_item:{photo_id}",)
    outcome_id = _outcome_row(database, farm, boss, plant, evidence_refs=refs)
    with database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        service.associate_follow_up_evidence(
            _association_command(boss, plant.plant_id, outcome_id, refs)
        )
    if origin != "raw":
        with database.session() as session, session.begin():
            row = session.get(DatasetCandidate, candidate_id)
            row.candidate_origin = origin
    return candidate_id


def _command(actor, *, candidate_id, plant_id, run_id=None) -> DatasetAgentCommandV1:
    return DatasetAgentCommandV1(
        run_id=run_id or uuid.uuid4(),
        requested_at=FT014_NOW,
        actor_context=actor,
        plant_id=plant_id,
        candidate_id=candidate_id,
        agent_id="training_data_curator",
        trigger_kind="manual_review",
    )


def _run(database, command, executor, recorder, *, commit=True):
    with database.session() as session:
        service = TrainingDataCuratorRuntimeService(
            session, model_executor=executor, timeline_append=recorder
        )
        outcome = service.invoke(command)
        if commit:
            session.commit()
        return outcome


def _row(database, candidate_id) -> DatasetCandidate:
    with database.session() as session:
        return session.get(DatasetCandidate, candidate_id)


# ---------------------------------------------------------------------------
# Positive: selected plus strong evidence confirms atomically
# ---------------------------------------------------------------------------


def test_selected_atomic_confirmation_commits_identity_and_trainability(
    ft014_database, ft014_seed,
):
    farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_photo_candidate(ft014_database, farm, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()

    outcome = _run(ft014_database, command, _Executor("selected"), recorder)

    assert outcome.outcome_kind == "advisory_ready"
    assert outcome.status == "advisory_ready"
    assert outcome.curator_gate_result == "confirmed"
    assert outcome.audit_status == "appended"
    assert outcome.error_code is None
    assert outcome.validated_result.curator_decision == "selected"

    row = _row(ft014_database, candidate_id)
    assert row.candidate_status == CandidateStatus.CONFIRMED.value
    assert row.confirmation_source == ConfirmationSource.CURATOR_AUTO.value
    assert row.quality_tier == QualityTier.STANDARD.value
    assert row.can_train_on is True
    assert row.curator_decision == "selected"
    assert row.curator_run_id == command.run_id
    assert row.curator_command_sha256 == command.command_sha256
    assert row.curator_recorded_at is not None
    assert row.record_version == 4  # create + evidence-linked + advisory + transition
    assert len(row.evidence_refs) == 2

    event_types = [e.event_type for e in recorder.events]
    assert event_types == [
        "dataset_candidate_reviewed",
        "dataset_agent_runtime_decided",
    ]
    runtime_payload = recorder.events[-1].payload_summary
    assert runtime_payload["outcome_kind"] == "advisory_ready"
    assert runtime_payload["curator_gate_result"] == "confirmed"
    assert runtime_payload["advisory_persisted"] is True
    assert runtime_payload["lifecycle_changed"] is True
    reviewed = recorder.events[0].payload_summary
    assert reviewed["confirmation_source"] == "curator_auto"
    assert reviewed["to_status"] == "confirmed"
    assert reviewed["can_train_on"] is True


# ---------------------------------------------------------------------------
# Negative: policy failures roll back and leave no reusable selected advisory
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "weak",
    [
        "single_photo_no_follow_up",
        "follow_up_missing_seen",
        "two_photos_no_outcome",
    ],
)
def test_selected_weak_evidence_policy_blocked_rolls_back(
    ft014_database, ft014_seed, weak,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        result = service.record_dataset_evidence(
            make_creation_command(boss, plant_id=plant.plant_id, source_ref=photo_id)
        )
        candidate_id = result.candidate_id
    # Prepare any extra source rows before touching the candidate so no nested
    # transaction writes inside a locked unit of work.
    if weak == "follow_up_missing_seen":
        outcome_id = _outcome_row(
            ft014_database, farm, boss, plant,
            evidence_refs=(f"photo_catalog_item:{photo_id}",),
        )
    elif weak == "two_photos_no_outcome":
        other_photo_id = _photo(ft014_database, farm, boss, plant)
    with ft014_database.session() as session, session.begin():
        row = session.get(DatasetCandidate, candidate_id)
        if weak == "single_photo_no_follow_up":
            row.evidence_refs = [{"kind": "photo", "ref": str(photo_id)}]
        elif weak == "follow_up_missing_seen":
            row.evidence_refs = [
                {"kind": "photo", "ref": str(photo_id)},
                {"kind": "follow_up_outcome", "ref": str(outcome_id)},
            ]
            row.follow_up_seen = False
        else:  # two_photos_no_outcome
            row.evidence_refs = [
                {"kind": "photo", "ref": str(photo_id)},
                {"kind": "photo", "ref": str(other_photo_id)},
            ]
            row.follow_up_seen = False

    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    outcome = _run(ft014_database, command, _Executor("selected"), recorder)

    assert outcome.outcome_kind == "policy_blocked"
    assert outcome.status == "blocked"
    assert outcome.validated_result is None
    assert outcome.curator_gate_result == "policy_blocked"
    assert outcome.error_code == "dataset_confirmation_policy_violation"
    assert outcome.audit_status == "appended"

    row = _row(ft014_database, candidate_id)
    assert row.candidate_status == CandidateStatus.CANDIDATE.value
    assert row.confirmation_source is None
    assert row.quality_tier == QualityTier.STANDARD.value
    assert row.can_train_on is False
    assert row.curator_decision is None
    assert row.curator_run_id is None
    assert row.curator_command_sha256 is None
    assert row.curator_recorded_at is None
    assert row.record_version == 1
    assert len(recorder.events) == 1
    assert recorder.events[0].payload_summary["advisory_persisted"] is False
    assert recorder.events[0].payload_summary["lifecycle_changed"] is False


def test_selected_gold_candidate_never_confirms_and_preserves_state(
    ft014_database, ft014_seed,
):
    farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_photo_candidate(ft014_database, farm, boss, plant)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        service.transition_candidate(
            TransitionDatasetCandidateCommandV1(
                actor_context=boss,
                candidate_id=candidate_id,
                transition="confirm",
                expected_status="candidate",
                expected_record_version=2,
                confirmation_source="human_review",
                quality_tier="gold",
            )
        )
    with ft014_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == "confirmed"
        assert row.quality_tier == "gold"
        assert row.confirmation_source == "human_review"

    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    outcome = _run(ft014_database, command, _Executor("selected"), recorder)

    assert outcome.outcome_kind == "policy_blocked"
    assert outcome.curator_gate_result == "policy_blocked"
    row = _row(ft014_database, candidate_id)
    assert row.candidate_status == "confirmed"
    assert row.confirmation_source == "human_review"
    assert row.quality_tier == "gold"
    assert row.can_train_on is True
    assert row.curator_run_id is None
    assert row.record_version == 3
    assert len(recorder.events) == 1
    assert recorder.events[0].payload_summary["advisory_persisted"] is False


def test_selected_agent_labeled_policy_blocked_without_partial_authority(
    ft014_database, ft014_seed,
):
    farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_photo_candidate(
        ft014_database, farm, boss, plant, origin="agent_labeled"
    )
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    outcome = _run(ft014_database, command, _Executor("selected"), recorder)

    assert outcome.outcome_kind == "policy_blocked"
    assert outcome.curator_gate_result == "policy_blocked"
    row = _row(ft014_database, candidate_id)
    assert row.candidate_origin == "agent_labeled"
    assert row.candidate_status == "candidate"
    assert row.confirmation_source is None
    assert row.can_train_on is False
    assert row.curator_run_id is None
    assert row.record_version == 2
    assert len(recorder.events) == 1
    assert recorder.events[0].payload_summary["lifecycle_changed"] is False


def test_policy_blocked_run_can_be_safely_rerun_after_strong_evidence(
    ft014_database, ft014_seed,
):
    """A blocked selected attempt leaves no reusable selection: enriching the
    candidate afterwards lets a fresh run confirm without conflict."""
    farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_photo_candidate(ft014_database, farm, boss, plant)
    # Degrade to weak evidence so the first run is blocked.
    with ft014_database.session() as session, session.begin():
        row = session.get(DatasetCandidate, candidate_id)
        row.evidence_refs = [row.evidence_refs[0]]
        row.follow_up_seen = False
        row.record_version += 1
    first = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    outcome = _run(ft014_database, first, _Executor("selected"), TimelineRecorder())
    assert outcome.outcome_kind == "policy_blocked"
    assert _row(ft014_database, candidate_id).curator_run_id is None

    # Restore strong evidence and rerun with a fresh run id.
    photo_id = _row(ft014_database, candidate_id).evidence_refs[0]["ref"]
    refs = (f"photo_catalog_item:{photo_id}",)
    outcome_id = _outcome_row(ft014_database, farm, boss, plant, evidence_refs=refs)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        service.associate_follow_up_evidence(
            _association_command(boss, plant.plant_id, outcome_id, refs)
        )
    second = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    outcome = _run(ft014_database, second, _Executor("selected"), TimelineRecorder())
    assert outcome.outcome_kind == "advisory_ready"
    assert outcome.curator_gate_result == "confirmed"
    row = _row(ft014_database, candidate_id)
    assert row.candidate_status == "confirmed"
    assert row.confirmation_source == "curator_auto"
    assert row.can_train_on is True
    assert row.curator_run_id == second.run_id


# ---------------------------------------------------------------------------
# Stale / duplicate run and post-I/O authority races
# ---------------------------------------------------------------------------


def test_stale_duplicate_run_is_post_io_guard_denied_preserving_prior_state(
    ft014_database, ft014_seed,
):
    farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_photo_candidate(ft014_database, farm, boss, plant)
    prior_run = uuid.uuid4()
    with ft014_database.session() as session, session.begin():
        row = session.get(DatasetCandidate, candidate_id)
        row.curator_decision = "deferred"
        row.curator_run_id = prior_run
        row.curator_command_sha256 = _DIGEST
        row.curator_recorded_at = FT014_NOW
        row.record_version += 1

    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    outcome = _run(ft014_database, command, _Executor("selected"), recorder)

    assert outcome.outcome_kind == "post_io_guard_denied"
    assert outcome.status == "blocked"
    assert outcome.curator_gate_result == "not_applicable"
    assert outcome.error_code == "dataset_agent_post_io_guard_denied"
    row = _row(ft014_database, candidate_id)
    assert row.curator_run_id == prior_run
    assert row.curator_decision == "deferred"
    assert row.candidate_status == "candidate"
    assert row.can_train_on is False
    assert row.record_version == 3
    assert len(recorder.events) == 1
    assert recorder.events[0].payload_summary["advisory_persisted"] is False


def test_archive_during_selected_io_is_post_io_guard_denied(
    ft014_database, ft014_seed,
):
    farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_photo_candidate(ft014_database, farm, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder()
    executor = _Executor(
        "selected",
        before_return=lambda: archive_plant(
            ft014_database, boss, plant_id=plant.plant_id
        ),
    )
    outcome = _run(ft014_database, command, executor, recorder)

    assert outcome.outcome_kind == "post_io_guard_denied"
    row = _row(ft014_database, candidate_id)
    assert row.curator_run_id is None
    assert row.candidate_status == "candidate"
    assert row.can_train_on is False
    assert row.record_version == 2


# ---------------------------------------------------------------------------
# Audit and commit failure branches
# ---------------------------------------------------------------------------


def test_transition_audit_failure_returns_audit_failed_without_event_or_state(
    ft014_database, ft014_seed,
):
    farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_photo_candidate(ft014_database, farm, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder(fail_on="dataset_candidate_reviewed")
    outcome = _run(ft014_database, command, _Executor("selected"), recorder)

    assert outcome.outcome_kind == "audit_failed"
    assert outcome.status == "failed"
    assert outcome.validated_result is None
    assert outcome.event_ref is None
    assert outcome.audit_status == "failed"
    assert outcome.error_code == "dataset_agent_audit_failed"
    row = _row(ft014_database, candidate_id)
    assert row.candidate_status == "candidate"
    assert row.confirmation_source is None
    assert row.can_train_on is False
    assert row.curator_run_id is None
    assert row.curator_decision is None
    assert row.record_version == 2
    assert recorder.events == []


def test_runtime_audit_failure_on_selected_rolls_back_advisory(
    ft014_database, ft014_seed,
):
    farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_photo_candidate(ft014_database, farm, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    recorder = TimelineRecorder(fail_on="dataset_agent_runtime_decided")
    outcome = _run(ft014_database, command, _Executor("selected"), recorder)

    assert outcome.outcome_kind == "audit_failed"
    assert outcome.audit_status == "failed"
    row = _row(ft014_database, candidate_id)
    assert row.candidate_status == "candidate"
    assert row.can_train_on is False
    assert row.curator_run_id is None
    assert row.record_version == 2
    # The transition's reviewed append succeeded before the runtime audit event
    # failed; it remains non-authoritative audit noise with zero replay power.
    assert len(recorder.events) == 1
    assert recorder.events[0].event_type == "dataset_candidate_reviewed"
    assert recorder.events[0].payload_summary["can_train_on"] is True


def test_append_success_then_commit_failure_is_audit_noise_only(
    ft014_database, ft014_seed, tmp_path,
):
    farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_photo_candidate(ft014_database, farm, boss, plant)
    command = _command(boss, candidate_id=candidate_id, plant_id=plant.plant_id)
    settings = AppSettings.from_env().model_copy(
        update={"local_timeline_root": str(tmp_path)}
    )
    appender = TimelineJsonlAppender(settings)
    with ft014_database.session() as session:
        service = TrainingDataCuratorRuntimeService(
            session, model_executor=_Executor("selected"), timeline_append=appender
        )
        outcome = service.invoke(command)
        assert outcome.outcome_kind == "advisory_ready"
        assert outcome.curator_gate_result == "confirmed"
        try:
            session.execute(text("SELECT 1 FROM nonexistent_probe_table"))
            session.commit()
        except Exception:
            session.rollback()
        else:
            session.rollback()

    row = _row(ft014_database, candidate_id)
    assert row.candidate_status == "candidate"
    assert row.confirmation_source is None
    assert row.can_train_on is False
    assert row.curator_run_id is None
    assert row.record_version == 2

    lines = (tmp_path / "timeline.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert lines[0].find('"dataset_candidate_reviewed"') != -1
    assert lines[1].find('"dataset_agent_runtime_decided"') != -1
