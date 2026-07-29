from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import func, select

from backend.app.agent_runtime import (
    CurrentAuthorizationScope,
    RuntimeDecision,
    SafetyClassificationResultV1,
)
from backend.app.plant_state import (
    PlantStateAssessmentCandidateV1,
    PlantStateError,
    PlantStateErrorCode,
    PlantStateRecord,
    PlantStateTrustService,
)
from backend.app.photo_intake.models import PhotoCatalogItem
from backend.app.plant_state.runtime import _PlantStateMessageEnvelopeV1
from backend.app.vision_observation import (
    VisionObservationValidationError,
    VisionStateCandidateV1,
)
from backend.app.vision_observation.service import _VisionMessageEnvelopeV1
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_active_plant,
    create_actor,
    disable_membership,
    grant_access,
    revoke_access,
)


def _vision_handoff(
    actor,
    plant,
    *,
    confidence=0.75,
    polarity="present",
    observation_key="leaf_spots",
    message_id=None,
    summary=None,
    source_refs=None,
):
    message_id = message_id or uuid.uuid4()
    summary = summary or f"Synthetic {polarity} evidence for {observation_key}."
    source_refs = source_refs or (f"photo:{uuid.uuid4()}",)
    severity = {
        "present": "mild",
        "absent": "none",
        "uncertain": "unknown",
        "not_assessable": "unknown",
    }[polarity]
    scope = CurrentAuthorizationScope(
        farm_id=actor.farm_id,
        plant_id=plant.plant_id,
        role_preset=actor.role_preset.value,
        operation_kind="normal_read",
        permission_source="boss_role"
        if actor.role_preset.value == "boss"
        else "plant_access_grant",
        grant_id=None if actor.role_preset.value == "boss" else uuid.uuid4(),
    )
    envelope = _VisionMessageEnvelopeV1(
        message_id=message_id,
        run_id=uuid.uuid4(),
        agent_id="vision_observation",
        created_at=datetime.now(timezone.utc),
        farm_id=actor.farm_id,
        plant_id=plant.plant_id,
        runtime_decision=RuntimeDecision.SPEAK,
        candidate_claim_type=(
            "observation"
            if polarity in {"present", "absent"} and confidence >= 0.50
            else "hypothesis"
        ),
        confidence=confidence,
        source_refs=source_refs,
        candidate_output=summary,
        authorization_scope=scope,
    )
    candidate = VisionStateCandidateV1(
        run_id=envelope.run_id,
        message_id=message_id,
        observation_key=observation_key,
        polarity=polarity,
        severity=severity,
        summary=summary,
        confidence=confidence,
        source_refs=source_refs,
        observed_at=datetime.now(timezone.utc),
    )
    return envelope, candidate, _safe_classification(message_id)


def _assessment_handoff(actor, plant, records, *, kind="conflict", direction="not_applicable"):
    message_id = uuid.uuid4()
    refs = tuple(f"plant_state_record:{item.state_record_id}" for item in records)
    scope = CurrentAuthorizationScope(
        farm_id=actor.farm_id,
        plant_id=plant.plant_id,
        role_preset="boss",
        operation_kind="normal_read",
        permission_source="boss_role",
        grant_id=None,
    )
    summary = f"Synthetic {kind} assessment."
    envelope = _PlantStateMessageEnvelopeV1(
        message_id=message_id,
        run_id=uuid.uuid4(),
        agent_id="plant_state",
        created_at=datetime.now(timezone.utc),
        farm_id=actor.farm_id,
        plant_id=plant.plant_id,
        runtime_decision=RuntimeDecision.SPEAK,
        candidate_claim_type="hypothesis",
        confidence=0.8,
        source_refs=refs,
        candidate_output=summary,
        authorization_scope=scope,
    )
    candidate = PlantStateAssessmentCandidateV1(
        run_id=envelope.run_id,
        message_id=message_id,
        farm_id=actor.farm_id,
        plant_id=plant.plant_id,
        assessment_kind=kind,
        observation_key=records[0].observation_key,
        direction=direction,
        summary=summary,
        confidence=0.8,
        source_refs=refs,
        observed_at=max(item.observed_at for item in records),
    )
    return envelope, candidate, _safe_classification(message_id)


def _safe_classification(message_id):
    return SafetyClassificationResultV1.from_untrusted(
        {
            "schema_version": 1,
            "message_id": str(message_id),
            "classifier_version": "test-v1",
            "classification": "safe_information",
            "safe_task_kind": None,
            "reason_code": "non_physical_information",
        }
    )


def _persist(database, actor, handoff):
    candidate = handoff[1]
    envelope = handoff[0]
    if isinstance(candidate, VisionStateCandidateV1):
        photo_id = _valid_vision_photo_id(candidate.source_refs)
        if photo_id is not None:
            _seed_photo_catalog(
                database,
                actor,
                farm_id=envelope.farm_id,
                plant_id=envelope.plant_id,
                photo_id=photo_id,
            )
    with database.session() as session:
        return PlantStateTrustService(session).persist_classified(
            actor,
            envelope=envelope,
            candidate=candidate,
            classification=handoff[2],
        )


def _seed_photo_catalog(
    database,
    actor,
    *,
    farm_id,
    plant_id,
    photo_id,
):
    now = datetime.now(timezone.utc)
    with database.session() as session, session.begin():
        if session.get(PhotoCatalogItem, photo_id) is not None:
            return
        session.add(
            PhotoCatalogItem(
                photo_id=photo_id,
                farm_id=farm_id,
                plant_id=plant_id,
                uploaded_by_account_id=actor.account_id,
                uploaded_by_membership_id=actor.membership_id,
                photo_type="whole_plant",
                captured_at=now,
                uploaded_at=now,
                content_type="image/jpeg",
                size_bytes=1,
                sha256="a" * 64,
                original_file_ref=(
                    f"plants/{plant_id}/photos/{photo_id}/original.jpg"
                ),
                manifest_ref=(
                    f"plants/{plant_id}/photos/{photo_id}/"
                    "manifest.initial_capture.json"
                ),
                source_refs={},
                event_refs={},
                local_only=True,
                can_train_on=False,
            )
        )


def _valid_vision_photo_id(source_refs):
    if len(source_refs) != 1:
        return None
    photo_ref = source_refs[0]
    if not photo_ref.startswith("photo:"):
        return None
    try:
        photo_id = uuid.UUID(photo_ref.split(":", 1)[1])
    except ValueError:
        return None
    return photo_id if photo_ref == f"photo:{photo_id}" else None


@pytest.mark.parametrize(
    ("confidence", "polarity", "expected"),
    [
        (0.0, "present", "unknown"),
        (0.499, "absent", "unknown"),
        (0.50, "present", "observed"),
        (1.0, "absent", "observed"),
        (0.99, "uncertain", "unknown"),
        (0.99, "not_assessable", "unknown"),
    ],
)
def test_classified_only_exact_trust_mapping_and_no_agent_confirmation(
    confidence,
    polarity,
    expected,
    ft009_database,
    ft009_seed,
):
    _farm, boss, plant = ft009_seed
    item = _persist(
        ft009_database,
        boss,
        _vision_handoff(boss, plant, confidence=confidence, polarity=polarity),
    )
    assert item.trust_status == expected
    assert item.confirmation_source is None
    assert item.confirmed_at is None
    assert item.version == 1


def test_pending_unsafe_mismatch_and_revoked_current_access_write_nothing(
    ft009_database,
    ft009_seed,
):
    farm, boss, plant = ft009_seed
    engineer, membership = create_actor(ft009_database, farm, "engineer")
    grant_access(
        ft009_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    envelope, candidate, _classification = _vision_handoff(engineer, plant)
    unsafe = SafetyClassificationResultV1.from_untrusted(
        {
            "schema_version": 1,
            "message_id": str(envelope.message_id),
            "classifier_version": "test-v1",
            "classification": "physical_action",
            "safe_task_kind": None,
            "reason_code": "physical_action_detected",
        }
    )
    with ft009_database.session() as session, pytest.raises(PlantStateError) as raised:
        PlantStateTrustService(session).persist_classified(
            engineer,
            envelope=envelope,
            candidate=candidate,
            classification=unsafe,
        )
    assert raised.value.code is PlantStateErrorCode.PLANT_STATE_CLASSIFICATION_REQUIRED
    revoke_access(
        ft009_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    with ft009_database.session() as session, pytest.raises(PlantStateError) as denied:
        PlantStateTrustService(session).persist_classified(
            engineer,
            envelope=envelope,
            candidate=candidate,
            classification=_safe_classification(envelope.message_id),
        )
    assert denied.value.code is PlantStateErrorCode.AUTH_PLANT_FORBIDDEN
    with ft009_database.session() as session:
        assert session.scalar(select(func.count(PlantStateRecord.state_record_id))) == 0


def test_wrong_farm_envelope_and_scope_fail_closed_before_insert(
    ft009_database,
    ft009_seed,
):
    _farm, boss, plant = ft009_seed
    envelope, candidate, classification = _vision_handoff(boss, plant)
    forged_farm_id = uuid.uuid4()
    forged_scope = CurrentAuthorizationScope(
        farm_id=forged_farm_id,
        plant_id=plant.plant_id,
        role_preset="boss",
        operation_kind="normal_read",
        permission_source="boss_role",
        grant_id=None,
    )
    forged_envelope = replace(
        envelope,
        farm_id=forged_farm_id,
        authorization_scope=forged_scope,
    )

    with ft009_database.session() as session, pytest.raises(PlantStateError) as denied:
        PlantStateTrustService(session).persist_classified(
            boss,
            envelope=forged_envelope,
            candidate=candidate,
            classification=classification,
        )
    assert denied.value.code is PlantStateErrorCode.AUTH_PLANT_FORBIDDEN
    with ft009_database.session() as session:
        assert session.scalar(select(func.count(PlantStateRecord.state_record_id))) == 0


def test_valid_singleton_photo_provenance_persists(
    ft009_database,
    ft009_seed,
):
    _farm, boss, plant = ft009_seed
    persisted = _persist(ft009_database, boss, _vision_handoff(boss, plant))
    assert persisted.plant_id == plant.plant_id
    assert len(persisted.source_refs) == 1
    assert persisted.source_refs[0].startswith("photo:")


def test_cross_plant_photo_provenance_fails_closed_with_dual_authorization(
    ft009_database,
    ft009_seed,
):
    _farm, boss, plant_a = ft009_seed
    plant_b = create_active_plant(
        ft009_database,
        boss,
        plant_key=f"target_{uuid.uuid4().hex[:8]}",
    )
    photo_a = uuid.uuid4()
    _seed_photo_catalog(
        ft009_database,
        boss,
        farm_id=boss.farm_id,
        plant_id=plant_a.plant_id,
        photo_id=photo_a,
    )
    envelope, candidate, classification = _vision_handoff(
        boss,
        plant_b,
        source_refs=(f"photo:{photo_a}",),
    )

    with ft009_database.session() as session, pytest.raises(PlantStateError) as denied:
        PlantStateTrustService(session).persist_classified(
            boss,
            envelope=envelope,
            candidate=candidate,
            classification=classification,
        )
    assert denied.value.code is PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID
    with ft009_database.session() as session:
        assert session.scalar(select(func.count(PlantStateRecord.state_record_id))) == 0


def test_retained_session_refreshes_authoritative_photo_ownership(
    ft009_database,
    ft009_seed,
):
    _farm, boss, plant_a = ft009_seed
    plant_b = create_active_plant(
        ft009_database,
        boss,
        plant_key=f"moved_{uuid.uuid4().hex[:8]}",
    )
    photo_id = uuid.uuid4()
    _seed_photo_catalog(
        ft009_database,
        boss,
        farm_id=boss.farm_id,
        plant_id=plant_a.plant_id,
        photo_id=photo_id,
    )
    handoff = _vision_handoff(
        boss,
        plant_a,
        source_refs=(f"photo:{photo_id}",),
    )

    with ft009_database.session() as session_a:
        retained_photo = session_a.get(PhotoCatalogItem, photo_id)
        assert retained_photo is not None
        assert retained_photo.plant_id == plant_a.plant_id
        session_a.commit()

        with ft009_database.session() as session_b, session_b.begin():
            authoritative_photo = session_b.get(PhotoCatalogItem, photo_id)
            assert authoritative_photo is not None
            authoritative_photo.plant_id = plant_b.plant_id

        assert retained_photo.plant_id == plant_a.plant_id
        with pytest.raises(PlantStateError) as denied:
            PlantStateTrustService(session_a).persist_classified(
                boss,
                envelope=handoff[0],
                candidate=handoff[1],
                classification=handoff[2],
            )
        assert denied.value.code is PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID

    with ft009_database.session() as session:
        assert session.scalar(select(func.count(PlantStateRecord.state_record_id))) == 0


def test_unknown_photo_and_mismatched_authorization_scope_fail_closed(
    ft009_database,
    ft009_seed,
):
    _farm, boss, plant = ft009_seed
    unknown = _vision_handoff(boss, plant)
    with ft009_database.session() as session, pytest.raises(PlantStateError) as missing:
        PlantStateTrustService(session).persist_classified(
            boss,
            envelope=unknown[0],
            candidate=unknown[1],
            classification=unknown[2],
        )
    assert missing.value.code is PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID

    photo_id = uuid.uuid4()
    _seed_photo_catalog(
        ft009_database,
        boss,
        farm_id=boss.farm_id,
        plant_id=plant.plant_id,
        photo_id=photo_id,
    )
    envelope, candidate, classification = _vision_handoff(
        boss,
        plant,
        source_refs=(f"photo:{photo_id}",),
    )
    mismatched_scope = CurrentAuthorizationScope(
        farm_id=boss.farm_id,
        plant_id=plant.plant_id,
        role_preset="engineer",
        operation_kind="normal_read",
        permission_source="plant_access_grant",
        grant_id=uuid.uuid4(),
    )
    with ft009_database.session() as session, pytest.raises(PlantStateError) as denied:
        PlantStateTrustService(session).persist_classified(
            boss,
            envelope=replace(envelope, authorization_scope=mismatched_scope),
            candidate=candidate,
            classification=classification,
        )
    assert denied.value.code is PlantStateErrorCode.AUTH_PLANT_FORBIDDEN
    with ft009_database.session() as session:
        assert session.scalar(select(func.count(PlantStateRecord.state_record_id))) == 0


def test_missing_and_malformed_vision_refs_fail_at_strict_value_boundary(
    ft009_seed,
):
    _farm, boss, plant = ft009_seed
    candidate = _vision_handoff(boss, plant)[1]
    for refs in (
        (),
        (f"plant:{plant.plant_id}",),
        (f"photo:{uuid.uuid4()}", f"photo:{uuid.uuid4()}"),
        ("photo:not-a-canonical-uuid",),
    ):
        with pytest.raises(VisionObservationValidationError):
            replace(candidate, source_refs=refs)


def test_message_and_classification_mismatch_write_nothing(
    ft009_database,
    ft009_seed,
):
    _farm, boss, plant = ft009_seed
    envelope, candidate, classification = _vision_handoff(boss, plant)
    mismatched_candidate = replace(candidate, message_id=uuid.uuid4())
    with ft009_database.session() as session, pytest.raises(PlantStateError) as invalid:
        PlantStateTrustService(session).persist_classified(
            boss,
            envelope=envelope,
            candidate=mismatched_candidate,
            classification=classification,
        )
    assert invalid.value.code is PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID

    mismatched_classification = _safe_classification(uuid.uuid4())
    with ft009_database.session() as session, pytest.raises(PlantStateError) as missing:
        PlantStateTrustService(session).persist_classified(
            boss,
            envelope=envelope,
            candidate=candidate,
            classification=mismatched_classification,
        )
    assert missing.value.code is PlantStateErrorCode.PLANT_STATE_CLASSIFICATION_REQUIRED
    with ft009_database.session() as session:
        assert session.scalar(select(func.count(PlantStateRecord.state_record_id))) == 0


def test_identical_message_is_idempotent_and_changed_content_conflicts(
    ft009_database,
    ft009_seed,
):
    _farm, boss, plant = ft009_seed
    handoff = _vision_handoff(boss, plant)
    first = _persist(ft009_database, boss, handoff)
    second = _persist(ft009_database, boss, handoff)
    assert second.state_record_id == first.state_record_id
    changed = _vision_handoff(
        boss,
        plant,
        message_id=handoff[0].message_id,
        summary="Changed immutable content.",
    )
    with pytest.raises(PlantStateError) as raised:
        _persist(ft009_database, boss, changed)
    assert raised.value.code is PlantStateErrorCode.PLANT_STATE_CONTENT_CONFLICT


def test_conflict_stays_explicit_until_reject_then_authorized_confirm(
    ft009_database,
    ft009_seed,
):
    _farm, boss, plant = ft009_seed
    present = _persist(
        ft009_database,
        boss,
        _vision_handoff(boss, plant, polarity="present", observation_key="wilting"),
    )
    absent = _persist(
        ft009_database,
        boss,
        _vision_handoff(boss, plant, polarity="absent", observation_key="wilting"),
    )
    assessment = _persist(
        ft009_database,
        boss,
        _assessment_handoff(boss, plant, (present, absent)),
    )
    assert assessment.trust_status == "conflicting"
    with ft009_database.session() as session:
        source_rows = list(
            session.scalars(
                select(PlantStateRecord).where(
                    PlantStateRecord.state_record_id.in_(
                        [present.state_record_id, absent.state_record_id]
                    )
                )
            )
        )
    assert {item.trust_status for item in source_rows} == {"conflicting"}
    assert {item.version for item in source_rows} == {2}

    with ft009_database.session() as session, pytest.raises(PlantStateError) as raised:
        PlantStateTrustService(session).review_record(
            boss,
            plant_id=plant.plant_id,
            state_record_id=present.state_record_id,
            expected_version=2,
            decision="confirm",
        )
    assert raised.value.code is PlantStateErrorCode.PLANT_STATE_CONFLICT_UNRESOLVED
    with ft009_database.session() as session:
        rejected = PlantStateTrustService(session).review_record(
            boss,
            plant_id=plant.plant_id,
            state_record_id=absent.state_record_id,
            expected_version=2,
            decision="reject",
        )
    assert rejected.trust_status == "rejected" and rejected.version == 3
    with ft009_database.session() as session:
        confirmed = PlantStateTrustService(session).review_record(
            boss,
            plant_id=plant.plant_id,
            state_record_id=present.state_record_id,
            expected_version=2,
            decision="confirm",
        )
    assert confirmed.trust_status == "confirmed"
    assert confirmed.confirmation_source == "human_review"
    assert confirmed.version == 3
    with ft009_database.session() as session:
        repeated = PlantStateTrustService(session).review_record(
            boss,
            plant_id=plant.plant_id,
            state_record_id=present.state_record_id,
            expected_version=3,
            decision="confirm",
        )
    assert repeated.version == 3


def test_review_authorization_version_archive_retention_and_pagination(
    ft009_database,
    ft009_seed,
):
    farm, boss, plant = ft009_seed
    first = _persist(ft009_database, boss, _vision_handoff(boss, plant))
    second = _persist(
        ft009_database,
        boss,
        _vision_handoff(boss, plant, observation_key="leaf_color_change"),
    )
    consultant, membership = create_actor(ft009_database, farm, "consultant")
    grant_access(
        ft009_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    with ft009_database.session() as session, pytest.raises(PlantStateError) as denied:
        PlantStateTrustService(session).review_record(
            consultant,
            plant_id=plant.plant_id,
            state_record_id=first.state_record_id,
            expected_version=1,
            decision="reject",
        )
    assert denied.value.code is PlantStateErrorCode.AUTH_PLANT_FORBIDDEN
    with ft009_database.session() as session, pytest.raises(PlantStateError) as stale:
        PlantStateTrustService(session).review_record(
            boss,
            plant_id=plant.plant_id,
            state_record_id=first.state_record_id,
            expected_version=99,
            decision="reject",
        )
    assert stale.value.code is PlantStateErrorCode.PLANT_STATE_VERSION_CONFLICT

    with ft009_database.session() as session:
        page1 = PlantStateTrustService(session).list_records(
            boss,
            plant_id=plant.plant_id,
            cursor=None,
            limit=1,
        )
    assert len(page1.items) == 1 and page1.next_cursor
    with ft009_database.session() as session:
        page2 = PlantStateTrustService(session).list_records(
            boss,
            plant_id=plant.plant_id,
            cursor=page1.next_cursor,
            limit=1,
        )
    assert len(page2.items) == 1 and page2.next_cursor is None
    assert {page1.items[0].state_record_id, page2.items[0].state_record_id} == {
        first.state_record_id,
        second.state_record_id,
    }

    archive_plant(ft009_database, boss, plant_id=plant.plant_id)
    with ft009_database.session() as session:
        retained = PlantStateTrustService(session).list_records(
            boss,
            plant_id=plant.plant_id,
            cursor=None,
            limit=50,
        )
    assert len(retained.items) == 2
    with ft009_database.session() as session, pytest.raises(PlantStateError) as archived:
        PlantStateTrustService(session).review_record(
            boss,
            plant_id=plant.plant_id,
            state_record_id=first.state_record_id,
            expected_version=1,
            decision="reject",
        )
    assert archived.value.code is PlantStateErrorCode.AUTH_PLANT_FORBIDDEN


def test_authorized_engineer_can_review_but_revoked_disabled_and_wrong_plant_fail(
    ft009_database,
    ft009_seed,
):
    farm, boss, plant = ft009_seed
    engineer, membership = create_actor(ft009_database, farm, "engineer")
    grant_access(
        ft009_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    first = _persist(ft009_database, boss, _vision_handoff(boss, plant))
    with ft009_database.session() as session:
        confirmed = PlantStateTrustService(session).review_record(
            engineer,
            plant_id=plant.plant_id,
            state_record_id=first.state_record_id,
            expected_version=1,
            decision="confirm",
        )
    assert confirmed.trust_status == "confirmed"
    assert confirmed.confirmation_source == "human_review"

    second = _persist(
        ft009_database,
        boss,
        _vision_handoff(boss, plant, observation_key="leaf_color_change"),
    )
    revoke_access(
        ft009_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    with ft009_database.session() as session, pytest.raises(PlantStateError) as revoked:
        PlantStateTrustService(session).review_record(
            engineer,
            plant_id=plant.plant_id,
            state_record_id=second.state_record_id,
            expected_version=1,
            decision="reject",
        )
    assert revoked.value.code is PlantStateErrorCode.AUTH_PLANT_FORBIDDEN

    other_engineer, other_membership = create_actor(ft009_database, farm, "engineer")
    grant_access(
        ft009_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=other_membership.membership_id,
    )
    disable_membership(ft009_database, other_membership.membership_id)
    with ft009_database.session() as session, pytest.raises(PlantStateError) as disabled:
        PlantStateTrustService(session).review_record(
            other_engineer,
            plant_id=plant.plant_id,
            state_record_id=second.state_record_id,
            expected_version=1,
            decision="reject",
        )
    assert disabled.value.code is PlantStateErrorCode.AUTH_PLANT_FORBIDDEN

    ungranted, _ = create_actor(ft009_database, farm, "engineer")
    with ft009_database.session() as session, pytest.raises(PlantStateError) as wrong_scope:
        PlantStateTrustService(session).review_record(
            ungranted,
            plant_id=plant.plant_id,
            state_record_id=second.state_record_id,
            expected_version=1,
            decision="reject",
        )
    assert wrong_scope.value.code is PlantStateErrorCode.AUTH_PLANT_FORBIDDEN
