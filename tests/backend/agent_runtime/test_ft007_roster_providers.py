from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest

from backend.app.agent_runtime import (
    AgentDefinition,
    AgentRunCommand,
    AgentRuntimeService,
    CANONICAL_ROSTER_V1,
    ProviderExecutorBindings,
    StaticAgentDefinitionResolver,
    canonical_roster,
)
from tests.backend.agent_runtime.test_ft007_runtime import _persistent_actor
from tests.backend.plant_operations.conftest import (
    create_active_plant,
    create_actor,
    seed_farm,
)


EXPECTED_IDS = (
    "companion",
    "vision_observation",
    "plant_state",
    "hydroponics_advisor",
    "task_follow_up",
    "safety_gate",
    "dataset_governance",
    "training_data_curator",
)
EXPECTED_NAMES = (
    "Companion Agent",
    "Vision Observation Agent",
    "Plant State Agent",
    "Hydroponics Advisor Agent",
    "Task & Follow-up Agent",
    "Safety Gate Agent",
    "Dataset Governance Agent",
    "Training Data Curator Agent",
)
EXPECTED_FEATURES = (
    "FT-013",
    "FT-009",
    "FT-009",
    "FT-010",
    "FT-012",
    "FT-011",
    "FT-014",
    "FT-014",
)


def test_provider_bindings_are_explicit_and_unbound_by_default():
    default = ProviderExecutorBindings()
    companion = object()
    safety = object()
    explicit = ProviderExecutorBindings(companion=companion, safety_gate=safety)

    assert default.companion is default.safety_gate is None
    assert explicit.companion is companion
    assert explicit.safety_gate is safety


def test_canonical_roster_v1_is_exact_ordered_and_immutable():
    assert isinstance(CANONICAL_ROSTER_V1, tuple)
    assert canonical_roster() is CANONICAL_ROSTER_V1
    assert tuple(item.agent_id for item in CANONICAL_ROSTER_V1) == EXPECTED_IDS
    assert tuple(item.display_name for item in CANONICAL_ROSTER_V1) == EXPECTED_NAMES
    assert tuple(item.owning_feature for item in CANONICAL_ROSTER_V1) == EXPECTED_FEATURES
    assert all(item.output_schema_version == 1 for item in CANONICAL_ROSTER_V1)
    assert all(item.competence_summary for item in CANONICAL_ROSTER_V1)
    assert all(item.introduction_text for item in CANONICAL_ROSTER_V1)
    with pytest.raises(ValueError):
        canonical_roster(2)


def test_unbound_agent_runtime_returns_not_configured_before_executor_io(
    ft004_database,
    event_ref_factory,
):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    plant = create_active_plant(ft004_database, boss, plant_key="unbound_runtime")
    actor = _persistent_actor(ft004_database, boss)
    definition = AgentDefinition(
        agent_id="runtime_test",
        competence="Exercise the provider-neutral executor boundary.",
        instructions="Return only the strict test result schema.",
        allowed_candidate_claim_types=("observation",),
    )

    with ft004_database.session() as session:
        outcome = AgentRuntimeService(
            session,
            definition_resolver=StaticAgentDefinitionResolver(
                {"runtime_test": definition}
            ),
            model_executor=None,
            timeline_append=event_ref_factory,
        ).invoke(
            AgentRunCommand(
                run_id=uuid.uuid4(),
                requested_at=datetime.now(timezone.utc),
                agent_definition_id="runtime_test",
                actor_context=actor,
                plant_id=plant.plant_id,
            )
        )

    assert outcome.outcome_kind == "runtime_not_configured"
    assert outcome.error_code == "AGENT_RUNTIME_NOT_CONFIGURED"
    assert outcome.provider_call_status == "not_attempted"
    assert outcome.audit_status == "not_attempted"
    assert outcome.model_ref is None
    assert event_ref_factory.events == []
