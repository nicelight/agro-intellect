"""FT-014-AC-014 / FT-014-BHV-003 production curator-auto positive path.

The sole production route to the strong-evidence precondition is
``record_follow_up_outcome`` invoking ``associate_follow_up_evidence`` in its
own UoW. A fresh Training Data Curator ``selected`` run then atomically
commits selected identity + ``curator_auto`` confirmation + derived
``can_train_on=true`` over that canonical multi-evidence state, with no
MessageEnvelope, Safety, Bus, UI, gold, or caller-selected authority.
"""

from __future__ import annotations

import uuid

from backend.app.dataset_governance import (
    DatasetAgentCommandV1,
    DatasetCandidate,
    DatasetGovernanceService,
    TrainingDataCuratorProviderRequestV1,
    TrainingDataCuratorRuntimeService,
)
from backend.app.task_follow_up import (
    RecordOutcomeCommandV1,
    TaskFollowUpService,
    OutcomeValue,
)
from tests.backend.dataset_governance.conftest import (
    FT014_NOW,
    TimelineRecorder,
)
from tests.backend.dataset_governance.test_outcome_association_wiring import (
    _open_follow_up,
    _photo_source,
)
from tests.backend.plant_operations.conftest import (
    create_actor,
    seed_farm,
    create_active_plant,
)
from tests.backend.task_follow_up.test_domain_loop import NOW


class _Executor:
    model_ref = "test_provider:curator_v1"

    def __init__(self, decision: str = "selected") -> None:
        self.decision = decision
        self.requests = []

    def execute(self, request: TrainingDataCuratorProviderRequestV1):
        self.requests.append(request)
        return {
            "schema_version": 1,
            "run_id": str(request.run_id),
            "curator_decision": self.decision,
            "curator_notes_ref": None,
        }


def _create_photo_candidate(database, farm, boss, plant):
    photo_id = _photo_source(database, farm, boss, plant)
    recorder = TimelineRecorder()
    with database.session() as session, session.begin():
        service = DatasetGovernanceService(
            session, timeline_appender=recorder, clock=lambda: FT014_NOW
        )
        from backend.app.dataset_governance import RecordDatasetEvidenceCommandV1

        result = service.record_dataset_evidence(
            RecordDatasetEvidenceCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                source_kind="photo_catalog_item",
                source_ref=photo_id,
            )
        )
        candidate_id = result.candidate_id
    return candidate_id, photo_id


def _run_curator(database, boss, plant, candidate_id, *, executor, recorder):
    command = DatasetAgentCommandV1(
        run_id=uuid.uuid4(),
        requested_at=FT014_NOW,
        actor_context=boss,
        plant_id=plant.plant_id,
        candidate_id=candidate_id,
        agent_id="training_data_curator",
        trigger_kind="manual_review",
    )
    with database.session() as session:
        service = TrainingDataCuratorRuntimeService(
            session, model_executor=executor, timeline_append=recorder
        )
        outcome = service.invoke(command)
        session.commit()
    return command, outcome


def test_production_photo_outcome_route_reaches_atomic_curator_auto_confirm(
    ft014_database,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(ft014_database, boss, plant_key="prod_curator_auto")
    recorder = TimelineRecorder()

    candidate_id, photo_id = _create_photo_candidate(
        ft014_database, farm, boss, plant
    )
    with ft014_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == "candidate"
        assert row.can_train_on is False
        assert len(row.evidence_refs) == 1
        assert row.record_version == 1

    follow_up = _open_follow_up(ft014_database, farm, boss, plant, recorder)
    with ft014_database.session() as session:
        TaskFollowUpService(
            session,
            timeline_appender=recorder,
            clock=lambda: NOW,
            dataset_governance=DatasetGovernanceService(
                session, timeline_appender=recorder, clock=lambda: FT014_NOW
            ),
        ).record_outcome(
            RecordOutcomeCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                follow_up_task_id=follow_up.task_id,
                request_id=uuid.uuid4(),
                value=OutcomeValue.IMPROVED,
                evidence_refs=(f"photo_catalog_item:{photo_id}",),
            )
        )

    with ft014_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
        assert row.follow_up_seen is True
        assert len(row.evidence_refs) == 2
        assert {item["kind"] for item in row.evidence_refs} == {
            "photo",
            "follow_up_outcome",
        }
        assert row.can_train_on is False
        assert row.record_version == 2

    runtime_recorder = TimelineRecorder()
    executor = _Executor("selected")
    command, outcome = _run_curator(
        ft014_database,
        boss,
        plant,
        candidate_id,
        executor=executor,
        recorder=runtime_recorder,
    )

    assert outcome.outcome_kind == "advisory_ready"
    assert outcome.status == "advisory_ready"
    assert outcome.curator_gate_result == "confirmed"
    assert outcome.audit_status == "appended"
    assert outcome.error_code is None
    assert outcome.validated_result.curator_decision == "selected"

    assert len(executor.requests) == 1
    payload = executor.requests[0].as_provider_payload()
    assert payload["agent_id"] == "training_data_curator"
    assert payload["candidate_id"] == str(candidate_id)
    assert payload["candidate"]["follow_up_seen"] is True
    assert payload["candidate"]["evidence_ref_count"] == 2
    assert payload["candidate"]["evidence_kinds"] == ["follow_up_outcome", "photo"]

    with ft014_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == "confirmed"
        assert row.confirmation_source == "curator_auto"
        assert row.quality_tier == "standard"
        assert row.can_train_on is True
        assert row.curator_decision == "selected"
        assert row.curator_run_id == command.run_id
        assert row.curator_command_sha256 == command.command_sha256
        assert row.curator_recorded_at is not None
        assert row.record_version == 4
        assert len(row.event_refs) == 3  # created + evidence_linked + reviewed

    event_types = [e.event_type for e in runtime_recorder.events]
    assert event_types == [
        "dataset_candidate_reviewed",
        "dataset_agent_runtime_decided",
    ]
    reviewed = runtime_recorder.events[0].payload_summary
    assert reviewed["confirmation_source"] == "curator_auto"
    assert reviewed["from_status"] == "candidate"
    assert reviewed["to_status"] == "confirmed"
    assert reviewed["can_train_on"] is True
    runtime_payload = runtime_recorder.events[-1].payload_summary
    assert runtime_payload["outcome_kind"] == "advisory_ready"
    assert runtime_payload["curator_gate_result"] == "confirmed"
    assert runtime_payload["advisory_persisted"] is True
    assert runtime_payload["lifecycle_changed"] is True


def test_production_path_selected_stale_run_stays_non_confirmed(
    ft014_database,
):
    """A second curator run on an already-persisted prior run is a closed
    stale/duplicate denial; production state keeps the earlier confirmation
    and gains no partial authority from the new run."""
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(ft014_database, boss, plant_key="prod_curator_stale")
    recorder = TimelineRecorder()

    candidate_id, photo_id = _create_photo_candidate(
        ft014_database, farm, boss, plant
    )
    follow_up = _open_follow_up(ft014_database, farm, boss, plant, recorder)
    with ft014_database.session() as session:
        TaskFollowUpService(
            session,
            timeline_appender=recorder,
            clock=lambda: NOW,
            dataset_governance=DatasetGovernanceService(
                session, timeline_appender=recorder, clock=lambda: FT014_NOW
            ),
        ).record_outcome(
            RecordOutcomeCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                follow_up_task_id=follow_up.task_id,
                request_id=uuid.uuid4(),
                value=OutcomeValue.IMPROVED,
                evidence_refs=(f"photo_catalog_item:{photo_id}",),
            )
        )

    first_command, first = _run_curator(
        ft014_database,
        boss,
        plant,
        candidate_id,
        executor=_Executor("selected"),
        recorder=TimelineRecorder(),
    )
    assert first.curator_gate_result == "confirmed"

    second_recorder = TimelineRecorder()
    second_command, second = _run_curator(
        ft014_database,
        boss,
        plant,
        candidate_id,
        executor=_Executor("selected"),
        recorder=second_recorder,
    )
    assert second.outcome_kind == "post_io_guard_denied"
    assert second.curator_gate_result == "not_applicable"
    with ft014_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == "confirmed"
        assert row.confirmation_source == "curator_auto"
        assert row.can_train_on is True
        assert row.curator_run_id == first_command.run_id
        assert row.curator_run_id != second_command.run_id
        assert row.record_version == 4
    assert len(second_recorder.events) == 1
    assert second_recorder.events[0].payload_summary["advisory_persisted"] is False


def test_production_path_has_no_generic_publication_effect(ft014_database):
    """The curator route is reachable only through the explicit internal
    command; the runtime module contains no MessageEnvelope/Safety/Bus/UI
    wiring."""
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
    ):
        assert forbidden not in source
