from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import uuid

import pytest

from backend.app.access_admin.models import Farm
from backend.app.agent_runtime import ModelExecution
from backend.app.photo_intake import PhotoIntakeService, PhotoUploadInput
from backend.app.vision_observation import (
    DatabaseVisionInputAssembler,
    VisionInputDenied,
    VisionObservationCommand,
    VisionObservationService,
)
from tests.backend.agent_runtime.test_ft007_runtime import _persistent_actor
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_active_plant,
    create_actor,
    grant_access,
    revoke_access,
    seed_farm,
)


FIXTURE = Path("tests/fixtures/vision/tomato_001_leaf.jpg")


class _Executor:
    model_ref = "test_provider:model_1"

    def __init__(self, result_factory, *, before_return=None):
        self.result_factory = result_factory
        self.before_return = before_return
        self.calls = []

    def execute(self, request, media):
        self.calls.append((request, media))
        if self.before_return is not None:
            self.before_return()
        return ModelExecution(
            model_ref=self.model_ref,
            result=self.result_factory(request),
        )


class _FailingExecutor:
    model_ref = "test_provider:model_1"

    def __init__(self):
        self.calls = []

    def execute(self, request, media):
        self.calls.append((request, media))
        raise RuntimeError("provider failure with secret-looking details")


def _speak(request, *, confidence=0.78, polarity="present"):
    return {
        "schema_version": 1,
        "runtime_decision": "speak",
        "observation_key": "leaf_color_change",
        "polarity": polarity,
        "severity": "mild" if polarity == "present" else "unknown",
        "summary": "Visible pale mottling appears across the tomato leaf.",
        "confidence": confidence,
        "source_refs": [request.source_refs[1]],
        "reason_code": None,
    }


def _clarify(request):
    return {
        "schema_version": 1,
        "runtime_decision": "clarify",
        "observation_key": "image_quality",
        "polarity": "not_assessable",
        "severity": "unknown",
        "summary": "The leaf is not visible clearly enough.",
        "confidence": None,
        "source_refs": [request.source_refs[1]],
        "reason_code": None,
    }


def _silent(_request):
    return {
        "schema_version": 1,
        "runtime_decision": "silent",
        "observation_key": None,
        "polarity": None,
        "severity": None,
        "summary": None,
        "confidence": None,
        "source_refs": [],
        "reason_code": "no_material_output",
    }


def _accepted_photo(database, artifact_store, event_ref_factory, *, actor=None, plant=None):
    farm = seed_farm(database) if actor is None else None
    if actor is None:
        actor, _ = create_actor(database, farm, "boss")
    if plant is None:
        plant = create_active_plant(database, actor, plant_key=f"vision_{uuid.uuid4().hex[:8]}")
    with database.session() as session:
        accepted = PhotoIntakeService(
            session,
            artifact_store=artifact_store,
            timeline_append=event_ref_factory,
        ).accept_photo(
            actor,
            plant_id=plant.plant_id,
            upload=PhotoUploadInput(
                content=FIXTURE.read_bytes(),
                content_type="image/jpeg",
                photo_type="leaf_closeup",
            ),
        )
    event_ref_factory.events.clear()
    return actor, plant, accepted.item


def _command(actor, plant_id, photo_id):
    return VisionObservationCommand(
        run_id=uuid.uuid4(),
        requested_at=datetime.now(timezone.utc),
        actor_context=actor,
        plant_id=plant_id,
        photo_id=photo_id,
    )


def _invoke(database, settings, event_ref_factory, actor, plant, photo, executor):
    current_actor = _persistent_actor(database, actor)
    with database.session() as session:
        return VisionObservationService(
            session,
            model_executor=executor,
            settings=settings,
            timeline_append=event_ref_factory,
        ).invoke(_command(current_actor, plant.plant_id, photo.photo_id))


def test_speak_uses_exact_accepted_bytes_and_returns_pending_matching_candidate(
    ft005_database,
    vision_artifact_store,
    vision_settings,
    event_ref_factory,
):
    actor, plant, photo = _accepted_photo(
        ft005_database,
        vision_artifact_store,
        event_ref_factory,
    )
    executor = _Executor(_speak)
    outcome = _invoke(
        ft005_database,
        vision_settings,
        event_ref_factory,
        actor,
        plant,
        photo,
        executor,
    )

    assert outcome.outcome_kind == "envelope_ready"
    assert outcome.final_decision == "speak"
    assert outcome.audit_status == "appended"
    envelope = outcome.message_envelope
    candidate = outcome.state_candidate
    assert envelope is not None and candidate is not None
    assert envelope.publication_state == "pending_classification"
    assert envelope.consumable_by_agents is False
    assert envelope.candidate_claim_type == "observation"
    assert candidate.message_id == envelope.message_id
    assert candidate.run_id == outcome.run_id
    assert candidate.source_refs == (f"photo:{photo.photo_id}",)
    request, media = executor.calls[0]
    assert request.source_refs == (
        f"plant:{plant.plant_id}",
        f"photo:{photo.photo_id}",
    )
    assert media.source_ref == f"photo:{photo.photo_id}"
    assert media.content == FIXTURE.read_bytes()
    assert media.sha256 == photo.sha256
    provider_text = str(request.as_provider_payload())
    assert photo.original_file_ref not in provider_text
    assert str(vision_settings.local_artifact_root) not in provider_text
    assert "session_id" not in provider_text
    event = event_ref_factory.events[-1]
    assert event.event_type == "agent_runtime_decided"
    assert event.payload_summary["outcome_kind"] == "envelope_ready"
    assert "candidate_output" not in event.payload_summary
    assert photo.original_file_ref not in str(event)
    assert media.content not in str(event).encode()


@pytest.mark.parametrize(
    ("result_factory", "decision", "has_envelope", "has_candidate", "claim"),
    [
        (_clarify, "clarify", True, False, "clarification"),
        (_silent, "silent", False, False, None),
        (lambda request: _speak(request, confidence=0.49, polarity="uncertain"), "speak", True, True, "hypothesis"),
    ],
)
def test_closed_result_matrix_and_low_confidence_transport_claim(
    result_factory,
    decision,
    has_envelope,
    has_candidate,
    claim,
    ft005_database,
    vision_artifact_store,
    vision_settings,
    event_ref_factory,
):
    actor, plant, photo = _accepted_photo(
        ft005_database,
        vision_artifact_store,
        event_ref_factory,
    )
    outcome = _invoke(
        ft005_database,
        vision_settings,
        event_ref_factory,
        actor,
        plant,
        photo,
        _Executor(result_factory),
    )
    assert outcome.final_decision == decision
    assert (outcome.message_envelope is not None) is has_envelope
    assert (outcome.state_candidate is not None) is has_candidate
    if has_envelope:
        assert outcome.message_envelope.candidate_claim_type == claim
    if decision == "silent":
        assert outcome.outcome_kind == "model_silent"
    if outcome.state_candidate is not None:
        assert outcome.state_candidate.polarity == "uncertain"
        assert "trust_status" not in outcome.state_candidate.as_value()


@pytest.mark.parametrize("case", ["missing", "tampered"])
def test_missing_or_tampered_photo_denies_before_provider_and_runtime_audit(
    case,
    ft005_database,
    vision_artifact_store,
    vision_settings,
    event_ref_factory,
):
    actor, plant, photo = _accepted_photo(
        ft005_database,
        vision_artifact_store,
        event_ref_factory,
    )
    photo_id = photo.photo_id
    if case == "missing":
        photo_id = uuid.uuid4()
    else:
        vision_artifact_store.path_for_test(photo.original_file_ref).write_bytes(b"tampered")
    executor = _Executor(_speak)
    current_actor = _persistent_actor(ft005_database, actor)
    with ft005_database.session() as session:
        outcome = VisionObservationService(
            session,
            model_executor=executor,
            settings=vision_settings,
            timeline_append=event_ref_factory,
        ).invoke(_command(current_actor, plant.plant_id, photo_id))
    assert outcome.outcome_kind == "context_denied"
    assert outcome.reason_code == "input_contract_violation"
    assert outcome.provider_call_status == "not_attempted"
    assert outcome.audit_status == "not_attempted"
    assert outcome.message_envelope is None
    assert outcome.state_candidate is None
    assert executor.calls == []
    assert event_ref_factory.events == []


def test_unauthorized_photo_and_unsafe_catalog_path_fail_before_egress(
    ft005_database,
    vision_artifact_store,
    vision_settings,
    event_ref_factory,
):
    actor, plant, photo = _accepted_photo(
        ft005_database,
        vision_artifact_store,
        event_ref_factory,
    )
    with ft005_database.session() as session:
        farm = session.get(Farm, actor.farm_id)
        assert farm is not None
    unauthorized, _ = create_actor(ft005_database, farm, "engineer")
    executor = _Executor(_speak)
    denied_actor = _persistent_actor(ft005_database, unauthorized)
    with ft005_database.session() as session:
        denied = VisionObservationService(
            session,
            model_executor=executor,
            settings=vision_settings,
            timeline_append=event_ref_factory,
        ).invoke(_command(denied_actor, plant.plant_id, photo.photo_id))
    assert denied.outcome_kind == "context_denied"
    assert executor.calls == []
    assert event_ref_factory.events == []

    class _Rows:
        def __init__(self):
            self.values = iter((plant, photo))

        def scalar(self, _statement):
            return next(self.values)

    photo.original_file_ref = "../../outside.jpg"
    with pytest.raises(VisionInputDenied):
        DatabaseVisionInputAssembler(
            _Rows(),  # type: ignore[arg-type]
            settings=vision_settings,
        ).assemble(
            actor,
            plant_id=plant.plant_id,
            photo_id=photo.photo_id,
        )


def test_archive_and_grant_revoke_after_model_io_block_handoff(
    ft005_database,
    vision_artifact_store,
    vision_settings,
    event_ref_factory,
):
    farm = seed_farm(ft005_database)
    boss, _ = create_actor(ft005_database, farm, "boss")
    engineer, membership = create_actor(ft005_database, farm, "engineer")
    first = create_active_plant(ft005_database, boss, plant_key="vision_archive")
    grant_access(
        ft005_database,
        boss,
        plant_id=first.plant_id,
        membership_id=membership.membership_id,
    )
    _, _, first_photo = _accepted_photo(
        ft005_database,
        vision_artifact_store,
        event_ref_factory,
        actor=engineer,
        plant=first,
    )
    archived = _invoke(
        ft005_database,
        vision_settings,
        event_ref_factory,
        engineer,
        first,
        first_photo,
        _Executor(
            _speak,
            before_return=lambda: archive_plant(
                ft005_database, boss, plant_id=first.plant_id
            ),
        ),
    )
    assert archived.outcome_kind == "publication_guard_denied"
    assert archived.message_envelope is None
    assert archived.state_candidate is None

    second = create_active_plant(ft005_database, boss, plant_key="vision_revoke")
    grant_access(
        ft005_database,
        boss,
        plant_id=second.plant_id,
        membership_id=membership.membership_id,
    )
    _, _, second_photo = _accepted_photo(
        ft005_database,
        vision_artifact_store,
        event_ref_factory,
        actor=engineer,
        plant=second,
    )
    revoked = _invoke(
        ft005_database,
        vision_settings,
        event_ref_factory,
        engineer,
        second,
        second_photo,
        _Executor(
            _speak,
            before_return=lambda: revoke_access(
                ft005_database,
                boss,
                plant_id=second.plant_id,
                membership_id=membership.membership_id,
            ),
        ),
    )
    assert revoked.outcome_kind == "publication_guard_denied"
    assert revoked.message_envelope is None
    assert revoked.state_candidate is None


def test_provider_output_and_audit_fail_closed_without_artifacts(
    ft005_database,
    vision_artifact_store,
    vision_settings,
    event_ref_factory,
):
    actor, plant, photo = _accepted_photo(
        ft005_database,
        vision_artifact_store,
        event_ref_factory,
    )
    failed = _invoke(
        ft005_database,
        vision_settings,
        event_ref_factory,
        actor,
        plant,
        photo,
        _FailingExecutor(),
    )
    assert failed.outcome_kind == "provider_failed"
    assert failed.error_code == "AGENT_PROVIDER_FAILED"
    assert failed.message_envelope is None and failed.state_candidate is None
    assert "secret-looking" not in str(event_ref_factory.events[-1])

    event_ref_factory.events.clear()
    invalid = _speak

    def invalid_result(request):
        value = invalid(request)
        value["diagnosis"] = "not allowed"
        return value

    output_invalid = _invoke(
        ft005_database,
        vision_settings,
        event_ref_factory,
        actor,
        plant,
        photo,
        _Executor(invalid_result),
    )
    assert output_invalid.outcome_kind == "output_invalid"
    assert output_invalid.message_envelope is None
    assert output_invalid.state_candidate is None

    def fail_audit(_event):
        raise RuntimeError("audit unavailable")

    current_actor = _persistent_actor(ft005_database, actor)
    with ft005_database.session() as session:
        audit_failed = VisionObservationService(
            session,
            model_executor=_Executor(_speak),
            settings=vision_settings,
            timeline_append=fail_audit,
        ).invoke(_command(current_actor, plant.plant_id, photo.photo_id))
    assert audit_failed.outcome_kind == "audit_failed"
    assert audit_failed.message_envelope is None
    assert audit_failed.state_candidate is None


@pytest.mark.parametrize(
    "executor",
    [None, type("MalformedExecutor", (), {"model_ref": "unsafe model ref"})()],
)
def test_missing_or_invalid_executor_is_not_configured_without_io(
    executor,
    ft005_database,
    vision_artifact_store,
    vision_settings,
    event_ref_factory,
):
    actor, plant, photo = _accepted_photo(
        ft005_database,
        vision_artifact_store,
        event_ref_factory,
    )
    outcome = _invoke(
        ft005_database,
        vision_settings,
        event_ref_factory,
        actor,
        plant,
        photo,
        executor,
    )
    assert outcome.outcome_kind == "runtime_not_configured"
    assert outcome.provider_call_status == "not_attempted"
    assert event_ref_factory.events == []
