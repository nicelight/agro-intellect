from __future__ import annotations

from datetime import datetime, timezone
import os
import uuid

import pytest

from backend.app.agent_runtime import (
    AgentDefinition,
    AgentRunCommand,
    AgentRuntimeService,
    AgnoModelExecutorFactory,
    ProviderBinding,
    StaticAgentDefinitionResolver,
)
from backend.app.plant_operations import PlantOperationsService
from tests.backend.agent_runtime.test_ft007_runtime import _persistent_actor
from tests.backend.plant_operations.conftest import (
    _postgres_database,
    create_active_plant,
    create_actor,
    seed_farm,
)


@pytest.mark.real_model
def test_credentialed_real_provider_runtime_contract_smoke():
    """Fail (never fake/fallback) when an explicitly requested smoke is incomplete."""

    if os.environ.get("AGENT_REAL_SMOKE") != "1":
        pytest.skip("credentialed smoke was not explicitly requested")
    profile = os.environ.get("AGENT_REAL_SMOKE_PROFILE")
    model_id = os.environ.get("AGENT_REAL_SMOKE_MODEL_ID")
    egress = os.environ.get("AGENT_EXTERNAL_EGRESS_ENABLED", "").lower() == "true"
    credential_name = {
        "deepseek": "DEEPSEEK_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }.get(profile or "")
    missing = []
    if profile not in {"deepseek", "gemini"}:
        missing.append("AGENT_REAL_SMOKE_PROFILE=deepseek|gemini")
    if not model_id:
        missing.append("AGENT_REAL_SMOKE_MODEL_ID")
    if not egress:
        missing.append("AGENT_EXTERNAL_EGRESS_ENABLED=true")
    if credential_name is None or not os.environ.get(credential_name):
        missing.append(credential_name or "matching provider credential")
    if missing:
        pytest.fail("missing explicit real-provider smoke inputs: " + ", ".join(missing))

    binding = ProviderBinding(profile or "", model_id or "")
    executor = AgnoModelExecutorFactory(
        egress_enabled=True,
        environ=os.environ,
    ).create(binding)
    definition = AgentDefinition(
        agent_id="runtime_contract_smoke",
        competence="Inspect authorized typed Plant evidence without making physical actions.",
        instructions=(
            "Return only AgentModelResultV1. Use speak/observation with one or more supplied "
            "source_refs, or silent with insufficient_evidence. Do not add fields."
        ),
        allowed_candidate_claim_types=("observation",),
    )
    events = []

    def append_event(event):
        events.append(event)
        event_id = uuid.uuid4()
        return {
            "timeline_event_id": str(event_id),
            "timeline_ref": f"timeline.jsonl#{event_id}",
            "event_type": event.event_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    with _postgres_database() as database:
        farm = seed_farm(database)
        boss, _ = create_actor(database, farm, "boss")
        plant = create_active_plant(database, boss, plant_key="real_smoke")
        with database.session() as session:
            PlantOperationsService(session, timeline_append=append_event).create_check_in(
                boss,
                plant_id=plant.plant_id,
                observation_state="observed",
                observation_text="The latest leaves were inspected during a real runtime smoke.",
            )
        actor = _persistent_actor(database, boss)
        with database.session() as session:
            outcome = AgentRuntimeService(
                session,
                definition_resolver=StaticAgentDefinitionResolver(
                    {"runtime_contract_smoke": definition}
                ),
                model_executor=executor,
                timeline_append=append_event,
            ).invoke(
                AgentRunCommand(
                    run_id=uuid.uuid4(),
                    requested_at=datetime.now(timezone.utc),
                    agent_definition_id="runtime_contract_smoke",
                    actor_context=actor,
                    plant_id=plant.plant_id,
                )
            )

    assert outcome.model_ref == binding.model_ref
    assert outcome.audit_status == "appended"
    assert outcome.event_ref is not None
    if outcome.outcome_kind == "envelope_ready":
        assert outcome.status == "envelope_ready"
        assert outcome.message_envelope is not None
        assert outcome.message_envelope.publication_state == "pending_classification"
        assert outcome.message_envelope.consumable_by_agents is False
    else:
        assert outcome.outcome_kind == "model_silent"
        assert outcome.status == "silent"
        assert outcome.final_decision == "silent"
        assert outcome.reason_code in {"no_material_output", "insufficient_evidence"}
        assert outcome.message_envelope is None
