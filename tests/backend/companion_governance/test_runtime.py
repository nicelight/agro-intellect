from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
from threading import Barrier

import pytest
from sqlalchemy import func, select, update

from backend.app.agent_runtime import ModelExecution
from backend.app.companion_governance import (
    CompanionHumanAttention,
    CompanionInputRecordV1,
    CompanionIssue,
    CompanionModelResultV1,
    CompanionProposal,
    CompanionProviderRequestV1,
    CompanionRunCommandV1,
    CompanionRuntimeService,
    CompanionRuntimeValidationError,
    DatabaseCompanionInputAssembler,
)
from backend.app.plant_operations import DailyCheckIn, ManualMeasurement
from backend.app.safety_gate import SafetyClassification
from backend.app.task_follow_up import Task
from tests.backend.companion_governance.conftest import (  # noqa: F401
    FT013_NOW,
    TimelineRecorder,
    ft013_database,
    ft013_seed,
)
from tests.backend.plant_operations.conftest import archive_plant
from tests.backend.plant_operations.conftest import (
    create_actor,
    grant_access,
    revoke_access,
)


class _Executor:
    def __init__(self, factory, model_ref: str, *, before_return=None):
        self.factory = factory
        self.model_ref = model_ref
        self.before_return = before_return
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        if self.before_return is not None:
            self.before_return()
        return ModelExecution(
            model_ref=self.model_ref,
            result=self.factory(request),
        )


def _proposal(request, *, effect="check"):
    return {
        "schema_version": 1,
        "runtime_decision": "speak",
        "issue_summary": (
            None
            if request.target_mode == "existing_issue"
            else "Проверить устойчивость текущего состояния."
        ),
        "attention_summary": "Нужно решение оператора.",
        "proposal_summary": "Выполнить дополнительную проверку.",
        "proposal_text": "Провести проверку листьев и записать наблюдение.",
        "rationale_text": "Текущих данных недостаточно для окончательного вывода.",
        "proposed_effect": effect,
        "task_display_text": (
            "Проверить листья и записать наблюдение."
            if effect in {"check", "measurement", "follow_up"}
            else None
        ),
        "suggested_resolution": "keep_open",
        "confidence": 0.82,
        "source_refs": list(request.source_refs),
        "reason_code": None,
    }


def _safety(_request, *, classification="safe_task_request", kind="check"):
    return {
        "schema_version": 1,
        "candidate_classification": classification,
        "safe_task_kind": kind if classification == "safe_task_request" else None,
        "physical_action_kind": (
            "ph_adjustment" if classification == "physical_action" else None
        ),
    }


def _silence(_request):
    return {
        "schema_version": 1,
        "runtime_decision": "silent",
        "issue_summary": None,
        "attention_summary": None,
        "proposal_summary": None,
        "proposal_text": None,
        "rationale_text": None,
        "proposed_effect": None,
        "task_display_text": None,
        "suggested_resolution": None,
        "confidence": None,
        "source_refs": [],
        "reason_code": "insufficient_evidence",
    }


def _command(actor, plant, *, run_id=None, issue_id=None, version=None):
    return CompanionRunCommandV1(
        run_id=run_id or uuid.uuid4(),
        requested_at=FT013_NOW,
        actor_context=actor,
        plant_id=plant.plant_id,
        issue_id=issue_id,
        expected_issue_version=version,
    )


def _seed_snapshot(database, farm, actor, plant):
    with database.session() as session, session.begin():
        older = DailyCheckIn(
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
            actor_account_id=actor.account_id,
            actor_membership_id=actor.membership_id,
            check_in_state="completed",
            observed_at=FT013_NOW - timedelta(hours=2),
            recorded_at=FT013_NOW - timedelta(hours=2),
            observation_state="observed",
            observation_text="Старое наблюдение.",
            source_refs={},
            event_refs={},
        )
        latest = DailyCheckIn(
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
            actor_account_id=actor.account_id,
            actor_membership_id=actor.membership_id,
            check_in_state="completed",
            observed_at=FT013_NOW - timedelta(hours=1),
            recorded_at=FT013_NOW - timedelta(hours=1),
            observation_state="observed",
            observation_text="Листья без заметных изменений.",
            source_refs={},
            event_refs={},
        )
        ph_only = ManualMeasurement(
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
            actor_account_id=actor.account_id,
            actor_membership_id=actor.membership_id,
            measured_at=FT013_NOW - timedelta(minutes=10),
            recorded_at=FT013_NOW - timedelta(minutes=9),
            ph=Decimal("6.25"),
            ec_ms_cm=None,
            source_type="manual_user",
            trust_status="confirmed",
            source_refs={},
            event_refs={},
        )
        ec_latest = ManualMeasurement(
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
            actor_account_id=actor.account_id,
            actor_membership_id=actor.membership_id,
            measured_at=FT013_NOW - timedelta(minutes=5),
            recorded_at=FT013_NOW - timedelta(minutes=4),
            ph=None,
            ec_ms_cm=Decimal("1.350"),
            source_type="manual_user",
            trust_status="confirmed",
            source_refs={},
            event_refs={},
        )
        session.add_all([older, latest, ph_only, ec_latest])
        session.flush()
        return latest.check_in_id, ec_latest.measurement_id


def _counts(database):
    with database.session() as session:
        return {
            "issues": session.scalar(select(func.count(CompanionIssue.issue_id))),
            "attentions": session.scalar(
                select(func.count(CompanionHumanAttention.attention_id))
            ),
            "proposals": session.scalar(
                select(func.count(CompanionProposal.proposal_id))
            ),
            "classifications": session.scalar(
                select(func.count(SafetyClassification.message_id))
            ),
            "tasks": session.scalar(select(func.count(Task.task_id))),
        }


def test_strict_companion_contracts_reject_unknown_and_invalid_matrix(ft013_seed):
    _farm, actor, _membership, plant = ft013_seed
    command = _command(actor, plant)
    assert {field.name for field in fields(command)} == {
        "run_id",
        "requested_at",
        "actor_context",
        "plant_id",
        "issue_id",
        "expected_issue_version",
        "schema_version",
    }
    with pytest.raises(CompanionRuntimeValidationError):
        CompanionRunCommandV1(
            run_id=uuid.uuid4(),
            requested_at=FT013_NOW,
            actor_context=actor,
            plant_id=plant.plant_id,
            issue_id=uuid.uuid4(),
            expected_issue_version=None,
        )
    request = CompanionProviderRequestV1(
        target_mode="new_issue",
        records=(
            CompanionInputRecordV1(
                "plant",
                f"plant:{plant.plant_id}",
                {"plant_id": str(plant.plant_id), "status": "active"},
            ),
        ),
    )
    with pytest.raises(CompanionRuntimeValidationError):
        CompanionModelResultV1.from_untrusted(
            {**_proposal(request), "action": "forbidden"},
            request=request,
        )


def test_exact_snapshot_two_spies_persist_one_classified_current_proposal(
    ft013_database,
    ft013_seed,
):
    farm, actor, _membership, plant = ft013_seed
    latest_check, latest_measurement = _seed_snapshot(
        ft013_database, farm, actor, plant
    )
    companion = _Executor(_proposal, "test_provider:companion_v1")
    safety = _Executor(_safety, "test_provider:safety_v1")
    timeline = TimelineRecorder()
    command = _command(actor, plant)
    with ft013_database.session() as session:
        result = CompanionRuntimeService(
            session,
            model_executor=companion,
            safety_classifier_executor=safety,
            timeline_append=timeline,
            clock=lambda: FT013_NOW,
        ).run(command)

    assert result.route_status == "proposal_created"
    assert result.runtime_outcome is not None
    assert result.runtime_outcome.message_envelope is not None
    assert len(companion.requests) == len(safety.requests) == 1
    request = companion.requests[0]
    assert [record.record_type for record in request.records] == [
        "plant",
        "daily_checkin",
        "manual_measurement",
    ]
    assert request.records[1].source_ref == f"daily_checkin:{latest_check}"
    assert request.records[2].source_ref == f"manual_measurement:{latest_measurement}"
    assert request.records[2].payload["ph"] is None
    assert request.records[2].payload["ec_ms_cm"] == "1.350"
    outbound = str(request.as_provider_payload()).lower()
    assert "6.25" not in outbound
    assert all(
        forbidden not in outbound
        for forbidden in (
            "farm_id",
            "session_id",
            "account_id",
            "membership_id",
            "grant_id",
            "proposal_text",
            "provider_history",
            "prompt",
        )
    )
    assert _counts(ft013_database) == {
        "issues": 1,
        "attentions": 1,
        "proposals": 1,
        "classifications": 1,
        "tasks": 0,
    }


@pytest.mark.parametrize("selected_ref_index", [0, -1])
def test_model_source_ref_subset_is_transient_but_proposal_keeps_full_provenance(
    ft013_database,
    ft013_seed,
    selected_ref_index,
):
    farm, actor, _membership, plant = ft013_seed
    _seed_snapshot(ft013_database, farm, actor, plant)

    def proposal_with_subset(request):
        return {
            **_proposal(request),
            "source_refs": [request.source_refs[selected_ref_index]],
        }

    companion = _Executor(proposal_with_subset, "test_provider:companion_v1")
    with ft013_database.session() as session:
        result = CompanionRuntimeService(
            session,
            model_executor=companion,
            safety_classifier_executor=_Executor(
                _safety,
                "test_provider:safety_v1",
            ),
            timeline_append=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant))

    assert result.route_status == "proposal_created"
    assert result.runtime_outcome is not None
    envelope = result.runtime_outcome.message_envelope
    assert envelope is not None
    request = companion.requests[0]
    assert tuple(envelope.source_refs) == (
        request.source_refs[selected_ref_index],
    )
    with ft013_database.session() as session:
        proposal = session.scalar(
            select(CompanionProposal).where(
                CompanionProposal.source_run_id == result.run_id
            )
        )
        assert proposal is not None
        assert tuple(proposal.source_refs) == (
            *request.source_refs,
            f"message_envelope:{envelope.message_id}",
            result.classification_ref,
        )


def test_snapshot_empty_combined_and_equal_time_ties_preserve_one_row_nulls(
    ft013_database,
    ft013_seed,
):
    farm, actor, _membership, plant = ft013_seed
    with ft013_database.session() as session:
        empty = DatabaseCompanionInputAssembler(session).assemble(
            _command(actor, plant)
        )
    assert [record.record_type for record in empty.request.records] == ["plant"]

    tied_at = FT013_NOW - timedelta(minutes=3)
    lower_check_id = uuid.UUID("00000000-0000-4000-8000-000000000001")
    higher_check_id = uuid.UUID("00000000-0000-4000-8000-000000000002")
    lower_measurement_id = uuid.UUID("00000000-0000-4000-8000-000000000003")
    higher_measurement_id = uuid.UUID("00000000-0000-4000-8000-000000000004")
    with ft013_database.session() as session, session.begin():
        session.add_all(
            [
                DailyCheckIn(
                    check_in_id=lower_check_id,
                    farm_id=farm.farm_id,
                    plant_id=plant.plant_id,
                    actor_account_id=actor.account_id,
                    actor_membership_id=actor.membership_id,
                    check_in_state="completed",
                    observed_at=tied_at,
                    recorded_at=tied_at,
                    observation_state="observed",
                    observation_text="Нижний UUID.",
                    source_refs={},
                    event_refs={},
                ),
                DailyCheckIn(
                    check_in_id=higher_check_id,
                    farm_id=farm.farm_id,
                    plant_id=plant.plant_id,
                    actor_account_id=actor.account_id,
                    actor_membership_id=actor.membership_id,
                    check_in_state="completed",
                    observed_at=tied_at,
                    recorded_at=tied_at,
                    observation_state="no_observation_provided",
                    observation_text=None,
                    source_refs={},
                    event_refs={},
                ),
                ManualMeasurement(
                    measurement_id=lower_measurement_id,
                    farm_id=farm.farm_id,
                    plant_id=plant.plant_id,
                    actor_account_id=actor.account_id,
                    actor_membership_id=actor.membership_id,
                    measured_at=tied_at,
                    recorded_at=tied_at,
                    ph=Decimal("6.40"),
                    ec_ms_cm=Decimal("1.200"),
                    source_type="manual_user",
                    trust_status="confirmed",
                    source_refs={},
                    event_refs={},
                ),
                ManualMeasurement(
                    measurement_id=higher_measurement_id,
                    farm_id=farm.farm_id,
                    plant_id=plant.plant_id,
                    actor_account_id=actor.account_id,
                    actor_membership_id=actor.membership_id,
                    measured_at=tied_at,
                    recorded_at=tied_at,
                    ph=None,
                    ec_ms_cm=Decimal("1.500"),
                    source_type="manual_user",
                    trust_status="confirmed",
                    source_refs={},
                    event_refs={},
                ),
            ]
        )

    with ft013_database.session() as session:
        tied = DatabaseCompanionInputAssembler(session).assemble(
            _command(actor, plant)
        )
    check_in, measurement = tied.request.records[1:]
    assert check_in.source_ref == f"daily_checkin:{higher_check_id}"
    assert check_in.payload["observation_text"] is None
    assert measurement.source_ref == f"manual_measurement:{higher_measurement_id}"
    assert measurement.payload["ph"] is None
    assert measurement.payload["ec_ms_cm"] == "1.500"
    assert "6.40" not in str(tied.request.as_provider_payload())


def test_committed_duplicate_returns_refs_without_provider_or_envelope_replay(
    ft013_database,
    ft013_seed,
):
    _farm, actor, _membership, plant = ft013_seed
    timeline = TimelineRecorder()
    run_id = uuid.uuid4()
    first_model = _Executor(_proposal, "test_provider:companion_v1")
    first_safety = _Executor(_safety, "test_provider:safety_v1")
    with ft013_database.session() as session:
        first = CompanionRuntimeService(
            session,
            model_executor=first_model,
            safety_classifier_executor=first_safety,
            timeline_append=timeline,
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant, run_id=run_id))
    retry_model = _Executor(_proposal, "test_provider:companion_retry")
    retry_safety = _Executor(_safety, "test_provider:safety_retry")
    with ft013_database.session() as session:
        duplicate = CompanionRuntimeService(
            session,
            model_executor=retry_model,
            safety_classifier_executor=retry_safety,
            timeline_append=timeline,
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant, run_id=run_id))

    assert first.route_status == "proposal_created"
    assert duplicate.route_status == "proposal_duplicate"
    assert duplicate.runtime_outcome is None
    assert (
        duplicate.issue_ref,
        duplicate.attention_ref,
        duplicate.proposal_ref,
        duplicate.classification_ref,
    ) == (
        first.issue_ref,
        first.attention_ref,
        first.proposal_ref,
        first.classification_ref,
    )
    assert retry_model.requests == retry_safety.requests == []
    assert _counts(ft013_database)["proposals"] == 1


def test_conflicting_run_reuse_fails_before_egress_and_silence_stays_non_mutating(
    ft013_database,
    ft013_seed,
):
    _farm, actor, _membership, plant = ft013_seed
    timeline = TimelineRecorder()
    run_id = uuid.uuid4()
    with ft013_database.session() as session:
        first = CompanionRuntimeService(
            session,
            model_executor=_Executor(_proposal, "test:companion"),
            safety_classifier_executor=_Executor(_safety, "test:safety"),
            timeline_append=timeline,
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant, run_id=run_id))
    issue_id = uuid.UUID(first.issue_ref.split(":", 1)[1])
    retry_model = _Executor(_proposal, "test:retry")
    with ft013_database.session() as session:
        conflict = CompanionRuntimeService(
            session,
            model_executor=retry_model,
            safety_classifier_executor=_Executor(_safety, "test:safety"),
            timeline_append=timeline,
            clock=lambda: FT013_NOW,
        ).run(
            _command(
                actor,
                plant,
                run_id=run_id,
                issue_id=issue_id,
                version=1,
            )
        )
    assert conflict.route_status == "failed"
    assert conflict.failure_code == "COMPANION_VERSION_CONFLICT"
    assert retry_model.requests == []

    silent_model = _Executor(_silence, "test:silent")
    silent_safety = _Executor(_safety, "test:safety")
    with ft013_database.session() as session:
        silent = CompanionRuntimeService(
            session,
            model_executor=silent_model,
            safety_classifier_executor=silent_safety,
            timeline_append=timeline,
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant))
    assert silent.route_status == "silent"
    assert silent.reason_code == "insufficient_evidence"
    assert len(silent_model.requests) == 1
    assert silent_safety.requests == []
    assert _counts(ft013_database)["proposals"] == 1


def test_existing_issue_sends_exact_persisted_summary_and_serially_supersedes(
    ft013_database,
    ft013_seed,
):
    _farm, actor, _membership, plant = ft013_seed
    timeline = TimelineRecorder()
    with ft013_database.session() as session:
        first = CompanionRuntimeService(
            session,
            model_executor=_Executor(_proposal, "test:companion"),
            safety_classifier_executor=_Executor(_safety, "test:safety"),
            timeline_append=timeline,
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant))
    issue_id = uuid.UUID(first.issue_ref.split(":", 1)[1])
    with ft013_database.session() as session:
        issue = session.get(CompanionIssue, issue_id)
        issue.summary_text = "  Сохранённый текст с пробелами внутри.  ".strip()
        version = issue.record_version
        session.commit()

    model = _Executor(_proposal, "test:companion")
    with ft013_database.session() as session:
        second = CompanionRuntimeService(
            session,
            model_executor=model,
            safety_classifier_executor=_Executor(_safety, "test:safety"),
            timeline_append=timeline,
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant, issue_id=issue_id, version=version))

    assert second.route_status == "proposal_created"
    issue_record = model.requests[0].records[1]
    assert issue_record.record_type == "companion_issue"
    assert issue_record.payload["summary_text"] == "Сохранённый текст с пробелами внутри."
    assert "issue_summary" not in str(model.requests[0].as_provider_payload())
    with ft013_database.session() as session:
        proposals = list(
            session.scalars(
                select(CompanionProposal)
                .where(CompanionProposal.issue_id == issue_id)
                .order_by(CompanionProposal.proposal_sequence)
            )
        )
    assert [row.state for row in proposals] == ["superseded", "pending"]


def test_post_io_issue_version_and_archive_races_fail_before_classifier_or_write(
    ft013_database,
    ft013_seed,
):
    _farm, actor, _membership, plant = ft013_seed
    timeline = TimelineRecorder()
    with ft013_database.session() as session:
        first = CompanionRuntimeService(
            session,
            model_executor=_Executor(_proposal, "test:companion"),
            safety_classifier_executor=_Executor(_safety, "test:safety"),
            timeline_append=timeline,
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant))
    issue_id = uuid.UUID(first.issue_ref.split(":", 1)[1])
    with ft013_database.session() as session:
        version = session.get(CompanionIssue, issue_id).record_version

    def change_version():
        with ft013_database.session() as session, session.begin():
            session.execute(
                update(CompanionIssue)
                .where(CompanionIssue.issue_id == issue_id)
                .values(record_version=CompanionIssue.record_version + 1)
            )

    version_safety = _Executor(_safety, "test:safety")
    with ft013_database.session() as session:
        raced = CompanionRuntimeService(
            session,
            model_executor=_Executor(
                _proposal,
                "test:companion",
                before_return=change_version,
            ),
            safety_classifier_executor=version_safety,
            timeline_append=timeline,
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant, issue_id=issue_id, version=version))
    assert raced.route_status == "failed"
    assert raced.failure_code == "COMPANION_VERSION_CONFLICT"
    assert version_safety.requests == []

    archive_safety = _Executor(_safety, "test:safety")
    with ft013_database.session() as session:
        archived = CompanionRuntimeService(
            session,
            model_executor=_Executor(
                _proposal,
                "test:companion",
                before_return=lambda: archive_plant(
                    ft013_database,
                    actor,
                    plant_id=plant.plant_id,
                ),
            ),
            safety_classifier_executor=archive_safety,
            timeline_append=timeline,
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant))
    assert archived.route_status == "failed"
    assert archived.failure_code == "COMPANION_PLANT_NOT_ACTIVE"
    assert archive_safety.requests == []
    assert _counts(ft013_database)["proposals"] == 1


def test_post_io_grant_revoke_fails_before_classifier_or_write(
    ft013_database,
    ft013_seed,
):
    farm, boss, _membership, plant = ft013_seed
    engineer, engineer_membership = create_actor(
        ft013_database,
        farm,
        "engineer",
    )
    grant_access(
        ft013_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    safety = _Executor(_safety, "test:safety")
    with ft013_database.session() as session:
        result = CompanionRuntimeService(
            session,
            model_executor=_Executor(
                _proposal,
                "test:companion",
                before_return=lambda: revoke_access(
                    ft013_database,
                    boss,
                    plant_id=plant.plant_id,
                    membership_id=engineer_membership.membership_id,
                ),
            ),
            safety_classifier_executor=safety,
            timeline_append=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).run(_command(engineer, plant))

    assert result.route_status == "failed"
    assert result.failure_code == "COMPANION_COMMAND_FORBIDDEN"
    assert safety.requests == []
    assert _counts(ft013_database)["proposals"] == 0


def test_same_run_concurrency_calls_both_spies_but_commits_one_product_effect(
    ft013_database,
    ft013_seed,
):
    _farm, actor, _membership, plant = ft013_seed
    barrier = Barrier(2)
    model = _Executor(
        _proposal,
        "test:companion",
        before_return=lambda: barrier.wait(timeout=10),
    )
    safety = _Executor(_safety, "test:safety")
    timeline = TimelineRecorder()
    run_id = uuid.uuid4()

    def invoke():
        with ft013_database.session() as session:
            return CompanionRuntimeService(
                session,
                model_executor=model,
                safety_classifier_executor=safety,
                timeline_append=timeline,
                clock=lambda: FT013_NOW,
            ).run(_command(actor, plant, run_id=run_id))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _item: invoke(), range(2)))

    assert sorted(result.route_status for result in results) == [
        "proposal_created",
        "proposal_duplicate",
    ]
    assert len(model.requests) == len(safety.requests) == 2
    assert _counts(ft013_database)["proposals"] == 1
    duplicate = next(
        result for result in results if result.route_status == "proposal_duplicate"
    )
    assert duplicate.runtime_outcome is None


class _FailingExecutor:
    model_ref = "test:companion"

    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        raise TimeoutError("credential=must-not-leak")


def test_provider_audit_classifier_uncertainty_and_mismatch_are_closed(
    ft013_database,
    ft013_seed,
):
    _farm, actor, _membership, plant = ft013_seed
    with ft013_database.session() as session:
        provider_failed = CompanionRuntimeService(
            session,
            model_executor=_FailingExecutor(),
            safety_classifier_executor=_Executor(_safety, "test:safety"),
            timeline_append=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant))
    assert provider_failed.failure_code == "AGENT_PROVIDER_FAILED"

    with ft013_database.session() as session:
        audit_failed = CompanionRuntimeService(
            session,
            model_executor=_Executor(_proposal, "test:companion"),
            safety_classifier_executor=_Executor(_safety, "test:safety"),
            timeline_append=TimelineRecorder(fail_on="agent_runtime_decided"),
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant))
    assert audit_failed.failure_code == "AGENT_AUDIT_FAILED"

    with ft013_database.session() as session:
        uncertain = CompanionRuntimeService(
            session,
            model_executor=_Executor(_proposal, "test:companion"),
            safety_classifier_executor=None,
            timeline_append=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant))
    assert uncertain.route_status == "not_governable"
    assert uncertain.reason_code == "classification_uncertain"

    mismatch_safety = _Executor(
        lambda request: _safety(
            request,
            classification="safe_information",
            kind=None,
        ),
        "test:safety",
    )
    with ft013_database.session() as session:
        mismatch = CompanionRuntimeService(
            session,
            model_executor=_Executor(_proposal, "test:companion"),
            safety_classifier_executor=mismatch_safety,
            timeline_append=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant))
    assert mismatch.route_status == "not_governable"
    assert mismatch.reason_code == "classification_mismatch"
    assert _counts(ft013_database)["proposals"] == 0


@pytest.mark.parametrize(
    ("model", "safety", "expected_status", "expected_code"),
    [
        (None, None, "failed", "AGENT_RUNTIME_NOT_CONFIGURED"),
        (
            _Executor(lambda _request: {"schema_version": 1}, "test:invalid"),
            _Executor(_safety, "test:safety"),
            "failed",
            "AGENT_OUTPUT_INVALID",
        ),
        (
            _Executor(_proposal, "test:companion"),
            _Executor(
                lambda request: _safety(
                    request,
                    classification="physical_action",
                    kind=None,
                ),
                "test:safety",
            ),
            "not_governable",
            None,
        ),
    ],
)
def test_unbound_invalid_and_physical_paths_create_no_governance(
    ft013_database,
    ft013_seed,
    model,
    safety,
    expected_status,
    expected_code,
):
    _farm, actor, _membership, plant = ft013_seed
    with ft013_database.session() as session:
        result = CompanionRuntimeService(
            session,
            model_executor=model,
            safety_classifier_executor=safety,
            timeline_append=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant))
    assert result.route_status == expected_status
    assert result.failure_code == expected_code
    if expected_status == "not_governable":
        assert result.reason_code == "physical_action_not_allowed"
    assert _counts(ft013_database)["proposals"] == 0


CORPUS_DB_PASSWORD = "corpus-ft078-db-pw-4h9k"
CORPUS_BEARER = "corpus-ft078-bearer-7q2m"
CORPUS_COOKIE = "corpus-ft078-cookie-1p5t"
CORPUS_SESSION = "corpus-ft078-session-8v3r"
CORPUS_SECRETS = [
    CORPUS_DB_PASSWORD,
    CORPUS_BEARER,
    CORPUS_COOKIE,
    CORPUS_SESSION,
]

CORPUS_OBSERVATION = (
    f"Watered 2L. dbpw={CORPUS_DB_PASSWORD} bearer={CORPUS_BEARER} "
    f"cookieval={CORPUS_COOKIE} sess={CORPUS_SESSION}"
)
CORPUS_SUMMARY = (
    f"Итог: dbpw={CORPUS_DB_PASSWORD} bearer={CORPUS_BEARER} "
    f"cookieval={CORPUS_COOKIE} sess={CORPUS_SESSION}"
)


def _corpus_assembler(session):
    return DatabaseCompanionInputAssembler(
        session,
        secret_values=tuple(CORPUS_SECRETS),
    )


def _seed_corpus_check_in(database, farm, actor, plant):
    with database.session() as session, session.begin():
        check_in = DailyCheckIn(
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
            actor_account_id=actor.account_id,
            actor_membership_id=actor.membership_id,
            check_in_state="completed",
            observed_at=FT013_NOW,
            recorded_at=FT013_NOW,
            observation_state="observed",
            observation_text=CORPUS_OBSERVATION,
            source_refs={},
            event_refs={},
        )
        session.add(check_in)
        return check_in.check_in_id


def _seed_corpus_issue(database, farm, plant):
    with database.session() as session, session.begin():
        issue = CompanionIssue(
            issue_id=uuid.uuid4(),
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
            status="open",
            is_focused=True,
            summary_text=CORPUS_SUMMARY,
            record_version=1,
            created_by_run_id=uuid.uuid4(),
            opened_event_ref={},
        )
        session.add(issue)
        return issue.issue_id


def test_companion_request_removes_configured_corpus_before_provider_boundary(
    ft013_database,
    ft013_seed,
):
    farm, actor, _membership, plant = ft013_seed
    _seed_corpus_check_in(ft013_database, farm, actor, plant)
    companion = _Executor(_proposal, "test_provider:companion_v1")
    safety = _Executor(_safety, "test_provider:safety_v1")
    with ft013_database.session() as session:
        result = CompanionRuntimeService(
            session,
            model_executor=companion,
            safety_classifier_executor=safety,
            input_assembler=_corpus_assembler(session),
            timeline_append=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant))

    assert result.route_status == "proposal_created"
    assert len(companion.requests) == len(safety.requests) == 1
    request = companion.requests[0]
    payload_text = str(request.as_provider_payload())
    record_text = repr(request)
    for raw in CORPUS_SECRETS:
        assert raw not in payload_text
        assert raw not in record_text
    assert "***" in payload_text
    check_in = request.records[1]
    assert check_in.record_type == "daily_checkin"
    assert "***" in check_in.payload["observation_text"]


def test_companion_request_keeps_source_values_unchanged_and_safe_parity(
    ft013_database,
    ft013_seed,
):
    farm, actor, _membership, plant = ft013_seed
    _seed_corpus_check_in(ft013_database, farm, actor, plant)
    companion = _Executor(_proposal, "test_provider:companion_v1")
    with ft013_database.session() as session:
        result = CompanionRuntimeService(
            session,
            model_executor=companion,
            safety_classifier_executor=_Executor(_safety, "test_provider:safety_v1"),
            input_assembler=_corpus_assembler(session),
            timeline_append=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant))

    assert result.route_status == "proposal_created"
    request = companion.requests[0]
    payload = request.as_provider_payload()
    assert list(payload) == [
        "schema_version",
        "agent_definition",
        "trigger_kind",
        "target_mode",
        "records",
        "source_refs",
    ]
    assert payload["schema_version"] == 1
    assert [record["record_type"] for record in payload["records"]] == [
        "plant",
        "daily_checkin",
    ]
    plant_payload = payload["records"][0]["payload"]
    assert set(plant_payload) == {"plant_id", "status"}
    assert plant_payload["status"] == "active"
    check_in_payload = payload["records"][1]["payload"]
    assert set(check_in_payload) == {
        "check_in_id",
        "observed_at",
        "recorded_at",
        "observation_state",
        "observation_text",
    }
    with ft013_database.session() as session:
        stored = session.scalar(
            select(DailyCheckIn).where(DailyCheckIn.plant_id == plant.plant_id)
        )
        assert stored is not None
        assert stored.observation_text == CORPUS_OBSERVATION


def test_companion_issue_summary_corpus_removed_before_provider_boundary(
    ft013_database,
    ft013_seed,
):
    _farm, actor, _membership, plant = ft013_seed
    issue_id = _seed_corpus_issue(ft013_database, _farm, plant)
    companion = _Executor(_proposal, "test_provider:companion_v1")
    with ft013_database.session() as session:
        result = CompanionRuntimeService(
            session,
            model_executor=companion,
            safety_classifier_executor=_Executor(_safety, "test_provider:safety_v1"),
            input_assembler=_corpus_assembler(session),
            timeline_append=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).run(_command(actor, plant, issue_id=issue_id, version=1))

    assert result.route_status == "proposal_created"
    request = companion.requests[0]
    assert [record.record_type for record in request.records] == [
        "plant",
        "companion_issue",
    ]
    issue_record = request.records[1]
    assert "***" in issue_record.payload["summary_text"]
    for raw in CORPUS_SECRETS:
        assert raw not in str(request.as_provider_payload())
    with ft013_database.session() as session:
        stored = session.get(CompanionIssue, issue_id)
        assert stored is not None
        assert stored.summary_text == CORPUS_SUMMARY


def test_companion_rejected_unsafe_input_zero_io_and_regression_counts(
    ft013_database,
    ft013_seed,
):
    _farm, actor, _membership, plant = ft013_seed
    companion = _Executor(_proposal, "test_provider:companion_v1")
    safety = _Executor(_safety, "test_provider:safety_v1")
    with ft013_database.session() as session:
        denied = CompanionRuntimeService(
            session,
            model_executor=companion,
            safety_classifier_executor=safety,
            input_assembler=_corpus_assembler(session),
            timeline_append=TimelineRecorder(),
            clock=lambda: FT013_NOW,
        ).run(
            _command(
                actor,
                plant,
                issue_id=uuid.UUID("00000000-0000-4000-8000-0000000000ff"),
                version=1,
            )
        )
    assert denied.route_status == "failed"
    assert denied.failure_code == "COMPANION_COMMAND_FORBIDDEN"
    assert companion.requests == safety.requests == []
    assert _counts(ft013_database) == {
        "issues": 0,
        "attentions": 0,
        "proposals": 0,
        "classifications": 0,
        "tasks": 0,
    }
