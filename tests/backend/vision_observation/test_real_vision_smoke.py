from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import uuid

import pytest

from backend.app import AppSettings
from backend.app.agent_runtime import ProductionProviderComposition, ProviderConfigurationError
from backend.app.photo_intake import PhotoArtifactStore, PhotoIntakeService, PhotoUploadInput
from backend.app.vision_observation import VisionObservationCommand, VisionObservationService
from tests.backend.agent_runtime.test_ft007_runtime import _persistent_actor
from tests.backend.photo_intake.conftest import _postgres_database
from tests.backend.plant_operations.conftest import create_active_plant, create_actor, seed_farm


@pytest.mark.real_model
def test_canonical_vision_observation_real_tomato_photo_smoke(tmp_path):
    """An explicitly requested smoke fails rather than skipping or substituting."""

    if os.environ.get("AGENT_REAL_VISION_SMOKE") != "1":
        pytest.skip("credentialed Vision smoke was not explicitly requested")
    settings = AppSettings.from_env()
    missing = []
    if not settings.agent_external_egress_enabled:
        missing.append("AGENT_EXTERNAL_EGRESS_ENABLED=true")
    if not os.environ.get("GOOGLE_API_KEY"):
        missing.append("GOOGLE_API_KEY")
    if settings.agent_model_bindings_json == "{}":
        missing.append("AGENT_MODEL_BINDINGS_JSON vision_observation binding")
    if missing:
        pytest.fail("missing explicit real Vision smoke inputs: " + ", ".join(missing))
    try:
        executor = ProductionProviderComposition(
            bindings_json=settings.agent_model_bindings_json,
            egress_enabled=settings.agent_external_egress_enabled,
            environ=os.environ,
        ).vision_executor_for()
    except ProviderConfigurationError:
        pytest.fail("canonical Vision Gemini composition is unavailable")

    fixture = Path("tests/fixtures/vision/tomato_001_leaf.jpg").read_bytes()
    smoke_settings = settings.model_copy(
        update={"local_artifact_root": tmp_path / "accepted-artifacts"}
    )
    store = PhotoArtifactStore(smoke_settings)
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
        plant = create_active_plant(database, boss, plant_key="real_vision")
        with database.session() as session:
            accepted = PhotoIntakeService(
                session,
                artifact_store=store,
                timeline_append=append_event,
            ).accept_photo(
                boss,
                plant_id=plant.plant_id,
                upload=PhotoUploadInput(
                    content=fixture,
                    content_type="image/jpeg",
                    photo_type="leaf_closeup",
                ),
            )
        events.clear()
        actor = _persistent_actor(database, boss)
        with database.session() as session:
            outcome = VisionObservationService(
                session,
                model_executor=executor,
                settings=smoke_settings,
                timeline_append=append_event,
            ).invoke(
                VisionObservationCommand(
                    run_id=uuid.uuid4(),
                    requested_at=datetime.now(timezone.utc),
                    actor_context=actor,
                    plant_id=plant.plant_id,
                    photo_id=accepted.item.photo_id,
                )
            )

    assert outcome.model_ref.startswith("gemini:")
    assert outcome.provider_call_status == "completed"
    assert outcome.audit_status == "appended"
    assert outcome.outcome_kind == "envelope_ready"
    assert outcome.final_decision == "speak"
    assert outcome.message_envelope is not None
    assert outcome.message_envelope.publication_state == "pending_classification"
    assert outcome.message_envelope.consumable_by_agents is False
    assert outcome.state_candidate is not None
    assert outcome.state_candidate.message_id == outcome.message_envelope.message_id
    assert outcome.state_candidate.source_refs == (
        f"photo:{accepted.item.photo_id}",
    ) or outcome.state_candidate.source_refs == (
        f"plant:{plant.plant_id}",
        f"photo:{accepted.item.photo_id}",
    )
    assert len(events) == 1
    assert "candidate_output" not in events[0].payload_summary

