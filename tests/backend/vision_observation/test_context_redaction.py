"""FT-015-AC-013: Vision Observation request/media context redaction.

Proves through the ACTUAL assembler and provider/media spy that the strict
request and verified media contain only registered authorized values and the
exact accepted-photo media identity, that hostile catalog values fail closed
BEFORE provider/media I/O, and that unbound production still fails closed.

Vision has no free-text channel into the outbound payload: every value is a
fixed constant, a canonical UUID, a closed-set member, or a UTC RFC 3339
timestamp, and the strict allowlist validators reject hostile row values.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import uuid

import pytest

from backend.app.agent_runtime import ModelExecution
from backend.app.photo_intake import PhotoCatalogItem, PhotoIntakeService, PhotoUploadInput
from backend.app.vision_observation import (
    DatabaseVisionInputAssembler,
    VisionObservationCommand,
    VisionObservationService,
)
from tests.backend.agent_runtime.test_ft007_runtime import _persistent_actor
from tests.backend.plant_operations.conftest import (
    create_active_plant,
    create_actor,
    seed_farm,
)


FIXTURE = Path("tests/fixtures/vision/tomato_001_leaf.jpg")

BARE_CORPUS = [
    "corpus-vision-db-pw-7h2k",
    "corpus-vision-bearer-5c3m",
    "corpus-vision-cookie-8p1t",
    "corpus-vision-session-3m6z",
]
FORBIDDEN_HEADERS = [
    "session=corpus-vision-cookie-8p1t; HttpOnly",
    "Authorization: Bearer corpus-vision-bearer-5c3m",
    "corpus-vision-ui-feed-entry-4q1r",
    "corpus-vision-provider-history-6t9c",
]


class _Executor:
    model_ref = "test_provider:model_1"

    def __init__(self):
        self.calls = []

    def execute(self, request, media):
        self.calls.append((request, media))
        return ModelExecution(
            model_ref=self.model_ref,
            result={
                "schema_version": 1,
                "runtime_decision": "speak",
                "observation_key": "leaf_color_change",
                "polarity": "present",
                "severity": "mild",
                "summary": "Visible pale mottling appears across the tomato leaf.",
                "confidence": 0.78,
                "reason_code": None,
            },
        )


def _accepted_photo(database, artifact_store, event_ref_factory):
    farm = seed_farm(database)
    actor, _ = create_actor(database, farm, "boss")
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


def test_request_and_media_carry_only_allowlist_and_exact_photo_identity(
    ft005_database,
    vision_artifact_store,
    vision_settings,
    event_ref_factory,
):
    actor, plant, photo = _accepted_photo(
        ft005_database, vision_artifact_store, event_ref_factory
    )
    executor = _Executor()
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
    assert len(executor.calls) == 1
    request, media = executor.calls[0]

    payload_text = str(request.as_provider_payload())
    assert request.source_refs == (f"plant:{plant.plant_id}", f"photo:{photo.photo_id}")
    for value in BARE_CORPUS + FORBIDDEN_HEADERS:
        assert value not in payload_text
        assert value not in repr(request)
        assert value not in repr(media)

    for attr_value in (
        str(actor.account_id),
        str(actor.session_id),
        str(actor.membership_id),
        str(actor.farm_id),
        actor.role_preset.value,
    ):
        assert attr_value not in payload_text
    assert str(vision_settings.local_artifact_root) not in payload_text
    assert photo.original_file_ref not in payload_text

    assert media.source_ref == f"photo:{photo.photo_id}"
    assert media.content_type == "image/jpeg"
    assert media.sha256 == photo.sha256
    assert media.content == FIXTURE.read_bytes()

    expected_payload = {"schema_version", "agent_definition", "records", "source_refs"}
    assert set(request.as_provider_payload()) == expected_payload
    records = request.as_provider_payload()["records"]
    assert [record["record_type"] for record in records] == ["plant", "photo"]
    assert set(records[0]["payload"]) == {"plant_id", "status"}
    assert set(records[1]["payload"]) == {
        "photo_id",
        "plant_id",
        "photo_type",
        "captured_at",
        "content_type",
        "size_bytes",
        "sha256",
        "local_only",
    }

    with ft005_database.session() as session:
        stored = session.get(PhotoCatalogItem, photo.photo_id)
        assert stored.photo_type == photo.photo_type
        assert stored.content_type == photo.content_type
        assert stored.sha256 == photo.sha256
    assert (
        vision_artifact_store.path_for_test(photo.original_file_ref).read_bytes()
        == FIXTURE.read_bytes()
    )


@pytest.mark.parametrize(
    ("field", "hostile"),
    [
        ("photo_type", "corpus-photo-type-7d3a"),
        ("content_type", "corpus/content-type-9x2b"),
        ("sha256", "corpus-sha256-not-hex-5p1q"),
    ],
)
def test_hostile_catalog_values_fail_closed_before_provider_io(
    field,
    hostile,
    ft005_database,
    vision_artifact_store,
    vision_settings,
    event_ref_factory,
):
    actor, plant, photo = _accepted_photo(
        ft005_database, vision_artifact_store, event_ref_factory
    )
    with ft005_database.session() as session:
        from sqlalchemy import select

        hostile_photo = session.scalar(
            select(PhotoCatalogItem).where(PhotoCatalogItem.photo_id == photo.photo_id)
        )
        setattr(hostile_photo, field, hostile)

        class _Rows:
            def __init__(self):
                self.values = iter((plant, hostile_photo))

            def scalar(self, _statement):
                return next(self.values)

        assembler = DatabaseVisionInputAssembler(
            _Rows(),  # type: ignore[arg-type]
            settings=vision_settings,
        )
        executor = _Executor()
        denied = VisionObservationService(
            session,
            model_executor=executor,
            input_assembler=assembler,
            settings=vision_settings,
            timeline_append=event_ref_factory,
        ).invoke(_command(_persistent_actor(ft005_database, actor), plant.plant_id, photo.photo_id))
    assert denied.outcome_kind == "context_denied"
    assert denied.reason_code == "input_contract_violation"
    assert denied.provider_call_status == "not_attempted"
    assert denied.audit_status == "not_attempted"
    assert executor.calls == []
    assert event_ref_factory.events == []


def test_unbound_production_still_fails_closed_without_io(
    ft005_database,
    vision_artifact_store,
    vision_settings,
    event_ref_factory,
):
    actor, plant, photo = _accepted_photo(
        ft005_database, vision_artifact_store, event_ref_factory
    )
    outcome = _invoke(
        ft005_database,
        vision_settings,
        event_ref_factory,
        actor,
        plant,
        photo,
        None,
    )
    assert outcome.outcome_kind == "runtime_not_configured"
    assert outcome.error_code == "AGENT_RUNTIME_NOT_CONFIGURED"
    assert outcome.provider_call_status == "not_attempted"
    assert outcome.audit_status == "not_attempted"
    assert event_ref_factory.events == []
