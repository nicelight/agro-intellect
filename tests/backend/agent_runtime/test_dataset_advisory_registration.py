from __future__ import annotations

import uuid

from backend.app.agent_runtime import (
    CANONICAL_ROSTER_V1,
    ProviderExecutorBindings,
    canonical_roster,
)
from backend.app.agent_runtime.roster import (
    RUNTIME_ROUTE_DATASET_ADVISORY,
    RUNTIME_ROUTE_GENERIC,
)
from backend.app.dataset_governance import (
    DatasetAgentCommandV1,
    DatasetGovernanceRuntimeService,
    DatasetGovernanceService,
    TrainingDataCuratorRuntimeService,
)
from tests.backend.dataset_governance.conftest import (
    FT014_NOW,
    TimelineRecorder,
    make_creation_command,
)


def _create_candidate(database, boss, plant) -> uuid.UUID:
    with database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        result = service.record_dataset_evidence(
            make_creation_command(boss, plant_id=plant.plant_id)
        )
        session.flush()
        return result.candidate_id


def test_roster_declares_advisory_only_route_immutably():
    roster = canonical_roster()
    by_id = {item.agent_id: item for item in roster}
    assert by_id["dataset_governance"].runtime_route == RUNTIME_ROUTE_DATASET_ADVISORY
    assert by_id["training_data_curator"].runtime_route == RUNTIME_ROUTE_DATASET_ADVISORY
    for agent_id in ("companion", "vision_observation", "plant_state", "hydroponics_advisor",
                     "task_follow_up", "safety_gate"):
        assert by_id[agent_id].runtime_route == RUNTIME_ROUTE_GENERIC
    assert CANONICAL_ROSTER_V1 is roster
    assert len(roster) == 8


def test_provider_bindings_expose_explicit_dataset_governance_slot():
    default = ProviderExecutorBindings()
    assert default.dataset_governance is None
    executor = object()
    explicit = ProviderExecutorBindings(dataset_governance=executor)
    assert explicit.dataset_governance is executor
    assert explicit.companion is None
    assert explicit.safety_gate is None


def test_provider_bindings_expose_explicit_training_data_curator_slot():
    default = ProviderExecutorBindings()
    assert default.training_data_curator is None
    executor = object()
    explicit = ProviderExecutorBindings(training_data_curator=executor)
    assert explicit.training_data_curator is executor
    assert explicit.dataset_governance is None
    assert explicit.companion is None
    assert explicit.safety_gate is None


def test_unbound_production_never_selects_fake_and_returns_not_configured(
    ft014_database,
    ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = DatasetAgentCommandV1(
        run_id=uuid.uuid4(),
        requested_at=FT014_NOW,
        actor_context=boss,
        plant_id=plant.plant_id,
        candidate_id=candidate_id,
        agent_id="dataset_governance",
        trigger_kind="dataset_candidate_created",
    )
    recorder = TimelineRecorder()
    with ft014_database.session() as session:
        outcome = DatasetGovernanceRuntimeService(
            session,
            model_executor=None,
            timeline_append=recorder,
        ).invoke(command)
    assert outcome.outcome_kind == "runtime_not_configured"
    assert outcome.error_code == "dataset_agent_runtime_not_configured"
    assert outcome.audit_status == "appended"
    assert len(recorder.events) == 1


def test_unbound_curator_production_fails_closed_with_audit(
    ft014_database,
    ft014_seed,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    command = DatasetAgentCommandV1(
        run_id=uuid.uuid4(),
        requested_at=FT014_NOW,
        actor_context=boss,
        plant_id=plant.plant_id,
        candidate_id=candidate_id,
        agent_id="training_data_curator",
        trigger_kind="manual_review",
    )
    recorder = TimelineRecorder()
    with ft014_database.session() as session:
        outcome = TrainingDataCuratorRuntimeService(
            session,
            model_executor=None,
            timeline_append=recorder,
        ).invoke(command)
    assert outcome.outcome_kind == "runtime_not_configured"
    assert outcome.error_code == "dataset_agent_runtime_not_configured"
    assert outcome.provider_call_status == "not_attempted"
    assert outcome.audit_status == "appended"
    assert outcome.curator_gate_result == "not_applicable"
    assert len(recorder.events) == 1
