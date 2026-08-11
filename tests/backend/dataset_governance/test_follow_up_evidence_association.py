"""FT-014-AC-007 follow-up evidence association command PostgreSQL matrix."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
from threading import Barrier
import uuid

import pytest
from sqlalchemy import text

from backend.app import AppSettings
from backend.app.dataset_governance import (
    AssociateFollowUpEvidenceCommandV1,
    AssociateFollowUpEvidenceResultV1,
    DatasetCandidate,
    DatasetGovernanceError,
    DatasetGovernanceErrorCode,
    DatasetGovernanceRepository,
    DatasetGovernanceService,
    DatasetGovernanceValidationError,
    SourceKind,
)
from backend.app.photo_intake import PhotoCatalogItem
from backend.app.plant_operations import DailyCheckIn, ManualMeasurement
from backend.app.safety_gate import SafetyClassification
from backend.app.task_follow_up import Outcome, Task
from backend.app.timeline import TimelineJsonlAppender
from tests.backend.dataset_governance.conftest import (
    FT014_NOW,
    TimelineRecorder,
    make_creation_command,
)
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    create_active_plant,
    grant_access,
    revoke_access,
)

_DIGEST = "a" * 64


def _photo(database, farm, boss, plant, *, photo_id=None):
    photo_id = photo_id or uuid.uuid4()
    with database.session() as session, session.begin():
        session.add(
            PhotoCatalogItem(
                photo_id=photo_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                uploaded_by_account_id=boss.account_id,
                uploaded_by_membership_id=boss.membership_id,
                photo_type="whole_plant",
                captured_at=FT014_NOW,
                uploaded_at=FT014_NOW,
                content_type="image/jpeg",
                size_bytes=100,
                sha256=_DIGEST,
                original_file_ref=(
                    f"plants/{plant.plant_id}/photos/{photo_id}/original.jpg"
                ),
                manifest_ref=(
                    f"plants/{plant.plant_id}/photos/{photo_id}/"
                    "manifest.initial_capture.json"
                ),
                source_refs={},
                event_refs={},
                local_only=True,
                can_train_on=False,
            )
        )
    return photo_id


def _check_in(database, farm, boss, plant, *, check_in_id=None):
    check_in_id = check_in_id or uuid.uuid4()
    with database.session() as session, session.begin():
        session.add(
            DailyCheckIn(
                check_in_id=check_in_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                actor_account_id=boss.account_id,
                actor_membership_id=boss.membership_id,
                check_in_state="completed",
                observed_at=FT014_NOW,
                recorded_at=FT014_NOW,
                observation_state="observed",
                observation_text="ok",
                source_refs={},
                event_refs={},
            )
        )
    return check_in_id


def _measurement(database, farm, boss, plant, *, measurement_id=None):
    measurement_id = measurement_id or uuid.uuid4()
    with database.session() as session, session.begin():
        session.add(
            ManualMeasurement(
                measurement_id=measurement_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                actor_account_id=boss.account_id,
                actor_membership_id=boss.membership_id,
                measured_at=FT014_NOW,
                recorded_at=FT014_NOW,
                ph=Decimal("6.10"),
                ec_ms_cm=None,
                source_type="manual_user",
                source_refs={},
                trust_status="confirmed",
                event_refs={},
            )
        )
    return measurement_id


def _create_candidate(
    database,
    boss,
    plant,
    *,
    source_kind: str,
    source_ref: uuid.UUID,
    status: str = "candidate",
):
    with database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        result = service.record_dataset_evidence(
            make_creation_command(
                boss,
                plant_id=plant.plant_id,
                source_kind=source_kind,
                source_ref=source_ref,
            )
        )
        candidate_id = result.candidate_id
        if status != "candidate":
            row = session.get(DatasetCandidate, candidate_id)
            row.candidate_status = status
    return candidate_id


def _outcome_row(
    database,
    farm,
    boss,
    plant,
    *,
    outcome_id=None,
    evidence_refs=(),
):
    outcome_id = outcome_id or uuid.uuid4()
    message_id = uuid.uuid4()
    with database.session() as session, session.begin():
        session.add(
            SafetyClassification(
                message_id=message_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                origin_agent_id="hydroponics_advisor",
                classifier_version="safety_gate_v1",
                classification="safe_task_request",
                safe_task_kind="follow_up",
                reason_code="safe_follow_up_request",
                physical_action_kind=None,
                provider_status="completed",
                model_ref="test:safety",
                input_sha256=_DIGEST,
                result_sha256=_DIGEST,
            )
        )
        session.flush()
        task = Task(
            task_id=uuid.uuid4(),
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
            kind="follow_up",
            status="completed",
            display_text="Follow up",
            source_type="safe_task_request",
            source_refs=[],
            classification_message_id=message_id,
            created_by_account_id=boss.account_id,
            created_by_membership_id=boss.membership_id,
            created_by_role_preset="boss",
            created_at=FT014_NOW,
            create_request_id=uuid.uuid4(),
            create_request_fingerprint=_DIGEST,
            created_event_ref={"timeline_event_id": str(uuid.uuid4())},
            completed_at=FT014_NOW,
            completed_by_account_id=boss.account_id,
            completed_by_membership_id=boss.membership_id,
            completed_by_role_preset="boss",
            completion_request_id=uuid.uuid4(),
            completion_request_fingerprint=_DIGEST,
            completed_event_ref={"timeline_event_id": str(uuid.uuid4())},
        )
        session.add(task)
        session.flush()
        session.add(
            Outcome(
                outcome_id=outcome_id,
                follow_up_task_id=task.task_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                value="improved",
                evidence_refs=list(evidence_refs),
                recorded_at=FT014_NOW,
                recorded_by_account_id=boss.account_id,
                recorded_by_membership_id=boss.membership_id,
                recorded_by_role_preset="boss",
                request_id=uuid.uuid4(),
                request_fingerprint=_DIGEST,
                outcome_event_ref={"timeline_event_id": str(uuid.uuid4())},
                task_completed_event_ref={"timeline_event_id": str(uuid.uuid4())},
            )
        )
    return outcome_id


def _association_command(
    actor,
    plant_id,
    outcome_id,
    evidence_refs=(),
) -> AssociateFollowUpEvidenceCommandV1:
    return AssociateFollowUpEvidenceCommandV1(
        actor_context=actor,
        plant_id=plant_id,
        outcome_id=outcome_id,
        evidence_refs=tuple(evidence_refs),
    )


# ---------------------------------------------------------------------------
# Contract / structural rejection
# ---------------------------------------------------------------------------


def test_command_structurally_rejects_caller_selected_fields(ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    with pytest.raises(TypeError):
        AssociateFollowUpEvidenceCommandV1(
            actor_context=boss,
            plant_id=plant.plant_id,
            outcome_id=uuid.uuid4(),
            evidence_refs=(),
            candidate_id=uuid.uuid4(),
        )
    with pytest.raises(TypeError):
        AssociateFollowUpEvidenceCommandV1(
            actor_context=boss,
            plant_id=plant.plant_id,
            outcome_id=uuid.uuid4(),
            evidence_refs=(),
            evidence_body={"kind": "photo", "ref": str(uuid.uuid4())},
        )
    with pytest.raises(TypeError):
        AssociateFollowUpEvidenceCommandV1(
            actor_context=boss,
            plant_id=plant.plant_id,
            outcome_id=uuid.uuid4(),
            evidence_refs=(),
            can_train_on=True,
            candidate_status="confirmed",
            split="train",
        )


def test_command_validates_shape_and_refs(ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    with pytest.raises(DatasetGovernanceValidationError):
        AssociateFollowUpEvidenceCommandV1(
            actor_context=boss,
            plant_id=plant.plant_id,
            outcome_id=uuid.uuid4(),
            evidence_refs=("not-a-ref",),
        )
    with pytest.raises(DatasetGovernanceValidationError):
        duplicate_ref = f"photo_catalog_item:{uuid.uuid4()}"
        AssociateFollowUpEvidenceCommandV1(
            actor_context=boss,
            plant_id=plant.plant_id,
            outcome_id=uuid.uuid4(),
            evidence_refs=(duplicate_ref, duplicate_ref),
        )
    with pytest.raises(DatasetGovernanceValidationError):
        AssociateFollowUpEvidenceCommandV1(
            actor_context=boss,
            plant_id=plant.plant_id,
            outcome_id=uuid.uuid4(),
            evidence_refs=(f"photo_catalog_item:{uuid.uuid4()}",) * 5,
        )
    with pytest.raises(DatasetGovernanceValidationError):
        _association_command(boss, "not-uuid", uuid.uuid4())


def test_service_rejects_non_command_association_handoff(ft014_seed, ft014_database):
    _farm, boss, _membership, _plant = ft014_seed
    with ft014_database.session() as session:
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceValidationError):
            service.associate_follow_up_evidence({"outcome_id": uuid.uuid4()})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Target derivation: supported and ignored source kinds
# ---------------------------------------------------------------------------


def test_photo_checkin_measurement_refs_derive_eligible_candidates(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    check_in_id = _check_in(ft014_database, farm, boss, plant)
    measurement_id = _measurement(ft014_database, farm, boss, plant)
    photo_candidate = _create_candidate(
        ft014_database, boss, plant, source_kind="photo_catalog_item", source_ref=photo_id
    )
    check_in_candidate = _create_candidate(
        ft014_database, boss, plant, source_kind="daily_check_in", source_ref=check_in_id
    )
    measurement_candidate = _create_candidate(
        ft014_database, boss, plant, source_kind="manual_measurement", source_ref=measurement_id
    )
    refs = (
        f"photo_catalog_item:{photo_id}",
        f"daily_checkin:{check_in_id}",
        f"manual_measurement:{measurement_id}",
    )
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs
    )
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.associate_follow_up_evidence(
            _association_command(boss, plant.plant_id, outcome_id, refs)
        )
        assert result.result == "associated"
        assert result.changed_candidate_ids == (
            photo_candidate,
            check_in_candidate,
            measurement_candidate,
        )
        assert result.unchanged_match_count == 0
        for candidate_id, expected_kind in (
            (photo_candidate, "photo_catalog_item"),
            (check_in_candidate, "daily_check_in"),
            (measurement_candidate, "manual_measurement"),
        ):
            row = session.get(DatasetCandidate, candidate_id)
            assert row.source_kind == expected_kind
            assert row.evidence_refs[-1] == {
                "kind": "follow_up_outcome",
                "ref": str(outcome_id),
            }
            assert row.follow_up_seen is True
            assert row.record_version == 2
    assert len(appender.events) == 3
    assert all(e.event_type == "dataset_candidate_evidence_linked" for e in appender.events)
    for event in appender.events:
        assert event.payload_summary["added_evidence_kind"] == "follow_up_outcome"
        assert event.payload_summary["follow_up_seen"] is True
        assert event.payload_summary["can_train_on"] is False
        assert event.payload_summary["candidate_status"] in {"candidate", "needs_review"}


def test_plant_and_plant_state_record_refs_are_ignored(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    photo_candidate = _create_candidate(
        ft014_database, boss, plant, source_kind="photo_catalog_item", source_ref=photo_id
    )
    refs = (
        f"plant:{plant.plant_id}",
        f"plant_state_record:{uuid.uuid4()}",
        f"photo_catalog_item:{photo_id}",
    )
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs
    )
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.associate_follow_up_evidence(
            _association_command(boss, plant.plant_id, outcome_id, refs)
        )
        assert result.result == "associated"
        assert result.changed_candidate_ids == (photo_candidate,)
        row = session.get(DatasetCandidate, photo_candidate)
        assert row.evidence_refs[-1] == {
            "kind": "follow_up_outcome",
            "ref": str(outcome_id),
        }
    assert len(appender.events) == 1


def test_zero_eligible_matches_succeeds_without_event(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    refs = (f"plant:{plant.plant_id}",)
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs
    )
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.associate_follow_up_evidence(
            _association_command(boss, plant.plant_id, outcome_id, refs)
        )
        assert result.result == "noop"
        assert result.changed_candidate_ids == ()
        assert result.unchanged_match_count == 0
    assert len(appender.events) == 0

    # A ref with no existing candidate is also a zero-match no-op.
    refs2 = (f"photo_catalog_item:{photo_id}",)
    outcome_id2 = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs2
    )
    appender2 = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender2)
        result = service.associate_follow_up_evidence(
            _association_command(boss, plant.plant_id, outcome_id2, refs2)
        )
        assert result.result == "noop"
    assert len(appender2.events) == 0


def test_unsupported_ref_kind_fails_closed(ft014_seed, ft014_database):
    farm, boss, _membership, plant = ft014_seed
    refs = (f"arbitrary_evidence:{uuid.uuid4()}",)
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs
    )
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.associate_follow_up_evidence(
                _association_command(boss, plant.plant_id, outcome_id, refs)
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.EVIDENCE_ASSOCIATION_CONFLICT


# ---------------------------------------------------------------------------
# Candidate-state eligibility and idempotent duplicates
# ---------------------------------------------------------------------------


def test_needs_review_is_eligible_and_confirmed_unchanged(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    needs_review_photo = _photo(ft014_database, farm, boss, plant)
    confirmed_photo = _photo(ft014_database, farm, boss, plant)
    needs_review_candidate = _create_candidate(
        ft014_database, boss, plant,
        source_kind="photo_catalog_item", source_ref=needs_review_photo,
        status="needs_review",
    )
    confirmed_candidate = _create_candidate(
        ft014_database, boss, plant,
        source_kind="photo_catalog_item", source_ref=confirmed_photo,
        status="confirmed",
    )
    refs = (
        f"photo_catalog_item:{needs_review_photo}",
        f"photo_catalog_item:{confirmed_photo}",
    )
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs
    )
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.associate_follow_up_evidence(
            _association_command(boss, plant.plant_id, outcome_id, refs)
        )
        assert result.result == "associated"
        assert result.changed_candidate_ids == (needs_review_candidate,)
        assert result.unchanged_match_count == 1
        needs_row = session.get(DatasetCandidate, needs_review_candidate)
        assert needs_row.evidence_refs[-1]["kind"] == "follow_up_outcome"
        assert needs_row.record_version == 2
        confirmed_row = session.get(DatasetCandidate, confirmed_candidate)
        assert len(confirmed_row.evidence_refs) == 1
        assert confirmed_row.record_version == 1
        assert confirmed_row.can_train_on is False
        assert confirmed_row.follow_up_seen is False
    assert len(appender.events) == 1


@pytest.mark.parametrize("status", ["rejected", "excluded"])
def test_terminal_candidates_retained_unchanged(
    ft014_seed, ft014_database, status,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(
        ft014_database, boss, plant,
        source_kind="photo_catalog_item", source_ref=photo_id, status=status,
    )
    refs = (f"photo_catalog_item:{photo_id}",)
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs
    )
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.associate_follow_up_evidence(
            _association_command(boss, plant.plant_id, outcome_id, refs)
        )
        assert result.result == "noop"
        assert result.changed_candidate_ids == ()
        assert result.unchanged_match_count == 1
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == status
        assert len(row.evidence_refs) == 1
        assert row.record_version == 1
        assert row.follow_up_seen is False
    assert len(appender.events) == 0


def test_identical_delivery_is_idempotent_noop(ft014_seed, ft014_database):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(
        ft014_database, boss, plant, source_kind="photo_catalog_item", source_ref=photo_id
    )
    refs = (f"photo_catalog_item:{photo_id}",)
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs
    )
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        first = service.associate_follow_up_evidence(
            _association_command(boss, plant.plant_id, outcome_id, refs)
        )
        second = service.associate_follow_up_evidence(
            _association_command(boss, plant.plant_id, outcome_id, refs)
        )
        assert first.result == "associated"
        assert first.changed_candidate_ids == (candidate_id,)
        assert second.result == "noop"
        assert second.changed_candidate_ids == ()
        assert second.unchanged_match_count == 1
        row = session.get(DatasetCandidate, candidate_id)
        assert len(row.evidence_refs) == 2
        assert [r for r in row.evidence_refs if r["kind"] == "follow_up_outcome"] == [
            {"kind": "follow_up_outcome", "ref": str(outcome_id)}
        ]
        assert row.record_version == 2
    assert len(appender.events) == 1


# ---------------------------------------------------------------------------
# Authority / scope / lock order
# ---------------------------------------------------------------------------


def test_archived_plant_and_revoked_grant_fail_closed(ft014_seed, ft014_database):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    _create_candidate(
        ft014_database, boss, plant, source_kind="photo_catalog_item", source_ref=photo_id
    )
    refs = (f"photo_catalog_item:{photo_id}",)
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs
    )
    archive_plant(ft014_database, boss, plant_id=plant.plant_id)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.associate_follow_up_evidence(
                _association_command(boss, plant.plant_id, outcome_id, refs)
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.CONTEXT_FORBIDDEN

    engineer, engineer_membership = create_actor(ft014_database, farm, "engineer")
    grant_access(
        ft014_database, boss, plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    revoke_access(
        ft014_database, boss, plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.associate_follow_up_evidence(
                _association_command(engineer, plant.plant_id, outcome_id, refs)
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.CONTEXT_FORBIDDEN


def test_missing_or_cross_scope_outcome_row_fails_closed(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    _create_candidate(
        ft014_database, boss, plant, source_kind="photo_catalog_item", source_ref=photo_id
    )
    refs = (f"photo_catalog_item:{photo_id}",)
    missing_outcome_id = uuid.uuid4()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.associate_follow_up_evidence(
                _association_command(boss, plant.plant_id, missing_outcome_id, refs)
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.EVIDENCE_ASSOCIATION_CONFLICT

    boss_two, _membership_two = create_actor(ft014_database, farm, "boss")
    plant_two = create_active_plant(
        ft014_database,
        boss_two,
        plant_key=f"ft014_assoc_{uuid.uuid4().hex[:8]}",
    )
    cross_outcome_id = _outcome_row(
        ft014_database, farm, boss_two, plant_two, evidence_refs=refs
    )
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.associate_follow_up_evidence(
                _association_command(boss, plant.plant_id, cross_outcome_id, refs)
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.EVIDENCE_ASSOCIATION_CONFLICT


def test_caller_refs_must_match_locked_outcome_row(ft014_seed, ft014_database):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    other_photo_id = _photo(ft014_database, farm, boss, plant)
    _create_candidate(
        ft014_database, boss, plant, source_kind="photo_catalog_item", source_ref=photo_id
    )
    _create_candidate(
        ft014_database, boss, plant, source_kind="photo_catalog_item", source_ref=other_photo_id
    )
    authorized = (f"photo_catalog_item:{photo_id}",)
    forged = (f"photo_catalog_item:{other_photo_id}",)
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=authorized
    )
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.associate_follow_up_evidence(
                _association_command(boss, plant.plant_id, outcome_id, forged)
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.EVIDENCE_ASSOCIATION_CONFLICT
        first_candidate = session.scalar(
            text("SELECT candidate_id FROM dataset_candidates WHERE source_ref = :rid"),
            {"rid": photo_id},
        )
        assert first_candidate is not None


def test_cross_scope_source_row_fails_closed(ft014_seed, ft014_database):
    farm, boss, _membership, plant = ft014_seed
    boss_two, _membership_two = create_actor(ft014_database, farm, "boss")
    plant_two = create_active_plant(
        ft014_database,
        boss_two,
        plant_key=f"ft014_assoc_{uuid.uuid4().hex[:8]}",
    )
    other_photo = _photo(ft014_database, farm, boss_two, plant_two)
    refs = (f"photo_catalog_item:{other_photo}",)
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs
    )
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.associate_follow_up_evidence(
                _association_command(boss, plant.plant_id, outcome_id, refs)
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.EVIDENCE_ASSOCIATION_CONFLICT


class _AssociationBarrierRepository(DatasetGovernanceRepository):
    def __init__(self, session, barrier: Barrier) -> None:
        super().__init__(session)
        self._barrier = barrier

    def current_scope(self, actor, *, plant_id, for_update):
        self._barrier.wait(timeout=15)
        return super().current_scope(actor, plant_id=plant_id, for_update=for_update)


def test_concurrent_same_outcome_association_commits_once(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(
        ft014_database, boss, plant, source_kind="photo_catalog_item", source_ref=photo_id
    )
    refs = (f"photo_catalog_item:{photo_id}",)
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs
    )
    barrier = Barrier(2)

    def attempt():
        try:
            with ft014_database.session() as session, session.begin():
                service = DatasetGovernanceService(
                    session,
                    repository=_AssociationBarrierRepository(session, barrier),
                    timeline_appender=TimelineRecorder(),
                )
                result = service.associate_follow_up_evidence(
                    _association_command(boss, plant.plant_id, outcome_id, refs)
                )
            return result.result
        except DatasetGovernanceError as error:
            return error.code.value

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(lambda _item: attempt(), range(2)))
    assert results == ["associated", "noop"]
    with ft014_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
        assert row.record_version == 2
        assert [r for r in row.evidence_refs if r["kind"] == "follow_up_outcome"] == [
            {"kind": "follow_up_outcome", "ref": str(outcome_id)}
        ]
        assert len(row.event_refs) == 2


# ---------------------------------------------------------------------------
# Audit: append rollback / commit-failure noise
# ---------------------------------------------------------------------------


def test_append_failure_rolls_back_association(ft014_seed, ft014_database):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(
        ft014_database, boss, plant, source_kind="photo_catalog_item", source_ref=photo_id
    )
    refs = (f"photo_catalog_item:{photo_id}",)
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs
    )
    appender = TimelineRecorder(fail_on="dataset_candidate_evidence_linked")
    with ft014_database.session() as session:
        with pytest.raises(DatasetGovernanceError) as excinfo:
            with session.begin():
                service = DatasetGovernanceService(session, timeline_appender=appender)
                service.associate_follow_up_evidence(
                    _association_command(boss, plant.plant_id, outcome_id, refs)
                )
        assert excinfo.value.code is DatasetGovernanceErrorCode.AUDIT_FAILED
    with ft014_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
        assert len(row.evidence_refs) == 1
        assert row.record_version == 1
        assert len(row.event_refs) == 1


def test_append_success_then_commit_failure_is_audit_noise(
    ft014_seed, ft014_database, tmp_path,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(
        ft014_database, boss, plant, source_kind="photo_catalog_item", source_ref=photo_id
    )
    refs = (f"photo_catalog_item:{photo_id}",)
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs
    )
    settings = AppSettings.from_env().model_copy(
        update={"local_timeline_root": str(tmp_path)}
    )
    appender = TimelineJsonlAppender(settings)
    with ft014_database.session() as session:
        session.begin()
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.associate_follow_up_evidence(
            _association_command(boss, plant.plant_id, outcome_id, refs)
        )
        assert result.result == "associated"
        try:
            session.execute(text("SELECT 1 FROM nonexistent_probe_table"))
            session.commit()
        except Exception:
            session.rollback()
        else:
            session.rollback()

    with ft014_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
        assert len(row.evidence_refs) == 1
        assert row.record_version == 1
        assert len(row.event_refs) == 1

    lines = (tmp_path / "timeline.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["event_type"] == "dataset_candidate_evidence_linked"


def test_evidence_linked_timeline_event_is_registered_redacted_canonical(
    ft014_seed, ft014_database, tmp_path,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(
        ft014_database, boss, plant, source_kind="photo_catalog_item", source_ref=photo_id
    )
    refs = (f"photo_catalog_item:{photo_id}",)
    outcome_id = _outcome_row(
        ft014_database, farm, boss, plant, evidence_refs=refs
    )
    settings = AppSettings.from_env().model_copy(
        update={"local_timeline_root": str(tmp_path)}
    )
    appender = TimelineJsonlAppender(settings)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        service.associate_follow_up_evidence(
            _association_command(boss, plant.plant_id, outcome_id, refs)
        )
        row = session.get(DatasetCandidate, candidate_id)
        assert len(row.event_refs) == 2

    lines = (tmp_path / "timeline.jsonl").read_text(encoding="utf-8").strip().splitlines()
    records = [json.loads(line) for line in lines]
    linked = [r for r in records if r["event_type"] == "dataset_candidate_evidence_linked"]
    assert len(linked) == 1
    record = linked[0]
    assert record["source_type"] == "dataset_candidate"
    assert record["source_id"] == str(candidate_id)
    assert record["payload_summary"] == {
        "added_evidence_kind": "follow_up_outcome",
        "candidate_status": "candidate",
        "evidence_ref_count": 2,
        "distinct_evidence_kind_count": 2,
        "follow_up_seen": True,
        "can_train_on": False,
    }
    assert record["redaction_status"] == "clean"
    assert record["source_refs"] == {
        "record_refs": [f"dataset_candidate:{candidate_id}"]
    }
    body = json.dumps(record, ensure_ascii=False, sort_keys=True)
    assert "photo_id" not in body
    assert "session_id" not in body
    assert "token" not in body
    assert "sha256" not in body
    assert "observation_text" not in body
    assert "improved" not in body
