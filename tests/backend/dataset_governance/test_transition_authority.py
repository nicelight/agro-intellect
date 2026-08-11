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
    DatasetCandidate,
    DatasetGovernanceError,
    DatasetGovernanceErrorCode,
    DatasetGovernanceRepository,
    DatasetGovernanceService,
    DatasetGovernanceValidationError,
    TransitionDatasetCandidateCommandV1,
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
    create_active_plant,
    create_actor,
    grant_access,
    revoke_access,
)

_DIGEST = "a" * 64


def _transition_command(
    actor,
    candidate_id,
    *,
    transition: str,
    expected_status: str,
    expected_version: int,
    confirmation_source: str | None = None,
    quality_tier: str | None = None,
    curator_run_id: uuid.UUID | None = None,
    curator_command_sha256: str | None = None,
) -> TransitionDatasetCandidateCommandV1:
    if confirmation_source == "curator_auto" and curator_command_sha256 is None:
        curator_command_sha256 = _DIGEST
    return TransitionDatasetCandidateCommandV1(
        actor_context=actor,
        candidate_id=candidate_id,
        transition=transition,
        expected_status=expected_status,
        expected_record_version=expected_version,
        confirmation_source=confirmation_source,
        quality_tier=quality_tier,
        curator_run_id=curator_run_id,
        curator_command_sha256=curator_command_sha256,
    )


def _create_candidate(
    database,
    boss,
    plant,
    *,
    source_kind: str = "photo_catalog_item",
    source_ref: uuid.UUID | None = None,
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
    return result.candidate_id


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


def _outcome(database, farm, boss, plant, *, outcome_id=None):
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
                evidence_refs=[f"manual_measurement:{uuid.uuid4()}"],
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


def _set_curator_run(database, candidate_id, *, curator_run_id, curator_command_sha256=_DIGEST):
    with database.session() as session, session.begin():
        row = session.get(DatasetCandidate, candidate_id)
        row.curator_decision = "selected"
        row.curator_run_id = curator_run_id
        row.curator_command_sha256 = curator_command_sha256
        row.curator_recorded_at = FT014_NOW


def _set_evidence(database, candidate_id, evidence_refs, *, follow_up_seen=False):
    with database.session() as session, session.begin():
        row = session.get(DatasetCandidate, candidate_id)
        row.evidence_refs = evidence_refs
        row.follow_up_seen = follow_up_seen


def _set_origin(database, candidate_id, origin: str):
    with database.session() as session, session.begin():
        row = session.get(DatasetCandidate, candidate_id)
        row.candidate_origin = origin


# ---------------------------------------------------------------------------
# Contract / structural rejection
# ---------------------------------------------------------------------------


def test_transition_command_structurally_rejects_assignment_fields(ft014_seed):
    _farm, boss, _membership, _plant = ft014_seed
    with pytest.raises(TypeError):
        TransitionDatasetCandidateCommandV1(
            actor_context=boss,
            candidate_id=uuid.uuid4(),
            transition="confirm",
            expected_status="candidate",
            expected_record_version=1,
            confirmation_source="human_review",
            can_train_on=True,
            candidate_status="confirmed",
            split="train",
        )


def test_transition_command_validates_source_and_transition_combinations(ft014_seed):
    _farm, boss, _membership, _plant = ft014_seed
    candidate_id = uuid.uuid4()
    with pytest.raises(DatasetGovernanceValidationError):
        _transition_command(
            boss, candidate_id, transition="confirm",
            expected_status="candidate", expected_version=1,
        )
    with pytest.raises(DatasetGovernanceValidationError):
        _transition_command(
            boss, candidate_id, transition="request_review",
            expected_status="candidate", expected_version=1,
            confirmation_source="human_review",
        )
    with pytest.raises(DatasetGovernanceValidationError):
        _transition_command(
            boss, candidate_id, transition="confirm",
            expected_status="candidate", expected_version=1,
            confirmation_source="curator_auto",
        )


def test_service_rejects_non_command_transition_handoff(ft014_seed, ft014_database):
    _farm, boss, _membership, _plant = ft014_seed
    with ft014_database.session() as session:
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceValidationError):
            service.transition_candidate({"candidate_id": uuid.uuid4()})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AC-002 legal transition matrix and derived can_train_on
# ---------------------------------------------------------------------------


def test_request_review_candidate_to_needs_review(ft014_seed, ft014_database):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.transition_candidate(
            _transition_command(
                boss, candidate_id, transition="request_review",
                expected_status="candidate", expected_version=1,
            )
        )
        assert result.result == "transitioned"
        assert result.from_status == "candidate"
        assert result.to_status == "needs_review"
        assert result.can_train_on is False
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == "needs_review"
        assert row.record_version == 2
        assert row.can_train_on is False
        assert len(row.event_refs) == 2
    assert len(appender.events) == 1
    assert appender.events[0].event_type == "dataset_candidate_reviewed"


def test_confirm_human_review_sets_confirmed_and_derives_trainability(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant, source_ref=photo_id)
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.transition_candidate(
            _transition_command(
                boss, candidate_id, transition="confirm",
                expected_status="candidate", expected_version=1,
                confirmation_source="human_review",
            )
        )
        assert result.to_status == "confirmed"
        assert result.can_train_on is True
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == "confirmed"
        assert row.confirmation_source == "human_review"
        assert row.quality_tier == "standard"
        assert row.can_train_on is True
        assert row.record_version == 2
        assert len(row.event_refs) == 2
    assert len(appender.events) == 1
    assert appender.events[0].payload_summary == {
        "from_status": "candidate",
        "to_status": "confirmed",
        "confirmation_source": "human_review",
        "quality_tier": "standard",
        "evidence_ref_count": 1,
        "can_train_on": True,
    }


def test_confirm_from_needs_review_expert_review(ft014_seed, ft014_database):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant, source_ref=photo_id)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        service.transition_candidate(
            _transition_command(
                boss, candidate_id, transition="request_review",
                expected_status="candidate", expected_version=1,
            )
        )
        result = service.transition_candidate(
            _transition_command(
                boss, candidate_id, transition="confirm",
                expected_status="needs_review", expected_version=2,
                confirmation_source="expert_review",
            )
        )
        assert result.to_status == "confirmed"
        assert result.can_train_on is True
        row = session.get(DatasetCandidate, candidate_id)
        assert row.confirmation_source == "expert_review"
        assert row.record_version == 3


@pytest.mark.parametrize("transition", ["reject", "exclude"])
def test_reject_and_exclude_are_terminal_and_never_trainable(
    ft014_seed, ft014_database, transition,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    expected_status = {"reject": "rejected", "exclude": "excluded"}[transition]
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        result = service.transition_candidate(
            _transition_command(
                boss, candidate_id, transition=transition,
                expected_status="candidate", expected_version=1,
            )
        )
        assert result.to_status == expected_status
        assert result.can_train_on is False
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == expected_status
        assert row.can_train_on is False


def test_confirmed_to_excluded_recomputes_trainability_false(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant, source_ref=photo_id)
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        service.transition_candidate(
            _transition_command(
                boss, candidate_id, transition="confirm",
                expected_status="candidate", expected_version=1,
                confirmation_source="human_review", quality_tier="gold",
            )
        )
        result = service.transition_candidate(
            _transition_command(
                boss, candidate_id, transition="exclude",
                expected_status="confirmed", expected_version=2,
            )
        )
        assert result.to_status == "excluded"
        assert result.can_train_on is False
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == "excluded"
        assert row.can_train_on is False
        assert row.quality_tier == "standard"
        assert row.confirmation_source == "human_review"
    assert len(appender.events) == 2
    assert all(e.event_type == "dataset_candidate_reviewed" for e in appender.events)


@pytest.mark.parametrize(
    ("from_status", "transition"),
    [
        ("confirmed", "confirm"),
        ("rejected", "confirm"),
        ("excluded", "confirm"),
        ("rejected", "request_review"),
        ("excluded", "request_review"),
        ("confirmed", "reject"),
        ("rejected", "exclude"),
        ("needs_review", "request_review"),
    ],
)
def test_illegal_and_terminal_transitions_are_forbidden(
    ft014_seed, ft014_database, from_status, transition,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    with ft014_database.session() as session, session.begin():
        row = session.get(DatasetCandidate, candidate_id)
        row.candidate_status = from_status
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        kwargs = {}
        if transition == "confirm":
            kwargs["confirmation_source"] = "human_review"
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition=transition,
                    expected_status=from_status, expected_version=1,
                    **kwargs,
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.TRANSITION_FORBIDDEN


# ---------------------------------------------------------------------------
# AC-002 stale / concurrent conflict and current-authority locks
# ---------------------------------------------------------------------------


def test_stale_expected_status_and_version_conflict(ft014_seed, ft014_database):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="request_review",
                    expected_status="needs_review", expected_version=1,
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.CANDIDATE_CONFLICT
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="request_review",
                    expected_status="candidate", expected_version=9,
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.CANDIDATE_CONFLICT


class _TransitionBarrierRepository(DatasetGovernanceRepository):
    def __init__(self, session, barrier: Barrier) -> None:
        super().__init__(session)
        self._barrier = barrier

    def candidate(self, candidate_id, *, for_update):
        if not for_update:
            self._barrier.wait(timeout=15)
        return super().candidate(candidate_id, for_update=for_update)


def test_concurrent_same_version_transition_commits_once(ft014_seed, ft014_database):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    barrier = Barrier(2)

    def attempt():
        try:
            with ft014_database.session() as session, session.begin():
                service = DatasetGovernanceService(
                    session,
                    repository=_TransitionBarrierRepository(session, barrier),
                    timeline_appender=TimelineRecorder(),
                )
                service.transition_candidate(
                    _transition_command(
                        boss, candidate_id, transition="request_review",
                        expected_status="candidate", expected_version=1,
                    )
                )
            return "ok"
        except DatasetGovernanceError as error:
            return error.code.value

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(lambda _item: attempt(), range(2)))
    assert results == ["dataset_candidate_conflict", "ok"]
    with ft014_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == "needs_review"
        assert row.record_version == 2
        assert len(row.event_refs) == 2


def test_archived_plant_and_revoked_grant_fail_closed(ft014_seed, ft014_database):
    farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    archive_plant(ft014_database, boss, plant_id=plant.plant_id)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="request_review",
                    expected_status="candidate", expected_version=1,
                )
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
            service.transition_candidate(
                _transition_command(
                    engineer, candidate_id, transition="request_review",
                    expected_status="candidate", expected_version=1,
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.CONTEXT_FORBIDDEN


# ---------------------------------------------------------------------------
# AC-003 forbidden evidence-kind matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden_kind",
    ["ui_feed", "timeline", "manifest", "raw_agent", "raw_companion"],
)
def test_forbidden_evidence_kinds_reject_confirm_with_unchanged_state(
    ft014_seed, ft014_database, forbidden_kind,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    _set_evidence(
        ft014_database,
        candidate_id,
        [{"kind": forbidden_kind, "ref": str(uuid.uuid4())}],
    )
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="confirm",
                    expected_status="candidate", expected_version=1,
                    confirmation_source="human_review",
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.EVIDENCE_INVALID
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == "candidate"
        assert row.can_train_on is False
        assert row.record_version == 1
        assert len(row.event_refs) == 1
    assert len(appender.events) == 0


# ---------------------------------------------------------------------------
# AC-004 evidence existence and same-Farm/Plant resolution matrix
# ---------------------------------------------------------------------------


def test_empty_evidence_refs_reject_confirm(ft014_seed, ft014_database):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    with ft014_database.session() as session, session.begin():
        repository = DatasetGovernanceRepository(session)
        assert repository.evidence_refs_resolve(
            farm_id=plant.farm_id,
            plant_id=plant.plant_id,
            evidence_refs=[],
        ) is False
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="confirm",
                    expected_status="candidate", expected_version=1,
                    confirmation_source="human_review",
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.EVIDENCE_INVALID


def test_unresolvable_evidence_ref_rejects_confirm(ft014_seed, ft014_database):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    _set_evidence(
        ft014_database,
        candidate_id,
        [{"kind": "photo", "ref": str(uuid.uuid4())}],
    )
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="confirm",
                    expected_status="candidate", expected_version=1,
                    confirmation_source="human_review",
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.EVIDENCE_INVALID


def test_cross_plant_evidence_ref_rejects_confirm(ft014_seed, ft014_database):
    farm, boss, _membership, plant = ft014_seed
    boss_two, _membership_two = create_actor(ft014_database, farm, "boss")
    plant_two = create_active_plant(
        ft014_database,
        boss_two,
        plant_key=f"ft014_crossplant_{uuid.uuid4().hex[:8]}",
    )
    other_photo = _photo(ft014_database, farm, boss_two, plant_two)
    candidate_id = _create_candidate(ft014_database, boss, plant)
    _set_evidence(
        ft014_database,
        candidate_id,
        [{"kind": "photo", "ref": str(other_photo)}],
    )
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="confirm",
                    expected_status="candidate", expected_version=1,
                    confirmation_source="human_review",
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.EVIDENCE_INVALID


def test_valid_canonical_same_farm_plant_evidence_permits_exact_confirm(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    check_in_id = _check_in(ft014_database, farm, boss, plant)
    measurement_id = _measurement(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant)
    _set_evidence(
        ft014_database,
        candidate_id,
        [
            {"kind": "photo", "ref": str(photo_id)},
            {"kind": "observation", "ref": str(check_in_id)},
            {"kind": "measurement", "ref": str(measurement_id)},
        ],
    )
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        result = service.transition_candidate(
            _transition_command(
                boss, candidate_id, transition="confirm",
                expected_status="candidate", expected_version=1,
                confirmation_source="human_review",
            )
        )
        assert result.to_status == "confirmed"
        assert result.can_train_on is True
        row = session.get(DatasetCandidate, candidate_id)
        assert row.can_train_on is True


# ---------------------------------------------------------------------------
# AC-008 agent_labeled origin-guard matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "confirmation_source",
    ["human_review", "expert_review", "batch_review", "curator_auto"],
)
def test_agent_labeled_confirm_rejected_all_sources(
    ft014_seed, ft014_database, confirmation_source,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    _set_origin(ft014_database, candidate_id, "agent_labeled")
    kwargs = {}
    if confirmation_source == "curator_auto":
        kwargs["curator_run_id"] = uuid.uuid4()
        kwargs["curator_command_sha256"] = _DIGEST
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="confirm",
                    expected_status="candidate", expected_version=1,
                    confirmation_source=confirmation_source, **kwargs,
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.TRANSITION_FORBIDDEN
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == "candidate"
        assert row.confirmation_source is None
        assert row.quality_tier == "standard"
        assert row.can_train_on is False
        assert row.record_version == 1
        assert len(row.event_refs) == 1
    assert len(appender.events) == 0


def test_agent_labeled_rejected_even_with_strong_evidence(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    outcome_id = _outcome(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant)
    _set_origin(ft014_database, candidate_id, "agent_labeled")
    _set_evidence(
        ft014_database,
        candidate_id,
        [
            {"kind": "photo", "ref": str(photo_id)},
            {"kind": "follow_up_outcome", "ref": str(outcome_id)},
        ],
        follow_up_seen=True,
    )
    curator_run_id = uuid.uuid4()
    _set_curator_run(ft014_database, candidate_id, curator_run_id=curator_run_id)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="confirm",
                    expected_status="candidate", expected_version=1,
                    confirmation_source="curator_auto",
                    curator_run_id=curator_run_id,
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.TRANSITION_FORBIDDEN


def test_raw_control_may_follow_only_allowed_confirm_branch(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant, source_ref=photo_id)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        result = service.transition_candidate(
            _transition_command(
                boss, candidate_id, transition="confirm",
                expected_status="candidate", expected_version=1,
                confirmation_source="human_review",
            )
        )
        assert result.to_status == "confirmed"
        assert result.can_train_on is True


# ---------------------------------------------------------------------------
# curator_auto strong-evidence policy and gold guard
# ---------------------------------------------------------------------------


def test_curator_auto_strong_evidence_confirms_and_derives_trainability(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    outcome_id = _outcome(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant)
    _set_evidence(
        ft014_database,
        candidate_id,
        [
            {"kind": "photo", "ref": str(photo_id)},
            {"kind": "follow_up_outcome", "ref": str(outcome_id)},
        ],
        follow_up_seen=True,
    )
    curator_run_id = uuid.uuid4()
    _set_curator_run(ft014_database, candidate_id, curator_run_id=curator_run_id)
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.transition_candidate(
            _transition_command(
                boss, candidate_id, transition="confirm",
                expected_status="candidate", expected_version=1,
                confirmation_source="curator_auto",
                curator_run_id=curator_run_id,
            )
        )
        assert result.to_status == "confirmed"
        assert result.can_train_on is True
        row = session.get(DatasetCandidate, candidate_id)
        assert row.confirmation_source == "curator_auto"
        assert row.quality_tier == "standard"
        assert row.can_train_on is True
    assert len(appender.events) == 1
    assert appender.events[0].payload_summary["confirmation_source"] == "curator_auto"


@pytest.mark.parametrize(
    ("kind_count", "follow_up_seen"),
    [
        (1, True),
        (2, False),
    ],
)
def test_curator_auto_weak_evidence_policy_violation(
    ft014_seed, ft014_database, kind_count, follow_up_seen,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    outcome_id = _outcome(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant)
    refs = [{"kind": "photo", "ref": str(photo_id)}]
    if kind_count == 2:
        refs.append({"kind": "follow_up_outcome", "ref": str(outcome_id)})
    _set_evidence(
        ft014_database,
        candidate_id,
        refs,
        follow_up_seen=follow_up_seen,
    )
    curator_run_id = uuid.uuid4()
    _set_curator_run(ft014_database, candidate_id, curator_run_id=curator_run_id)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="confirm",
                    expected_status="candidate", expected_version=1,
                    confirmation_source="curator_auto",
                    curator_run_id=curator_run_id,
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.CONFIRMATION_POLICY_VIOLATION


def test_curator_auto_requires_follow_up_outcome_and_distinct_kinds(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    other_photo = _photo(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant)
    _set_evidence(
        ft014_database,
        candidate_id,
        [
            {"kind": "photo", "ref": str(photo_id)},
            {"kind": "photo", "ref": str(other_photo)},
        ],
        follow_up_seen=False,
    )
    curator_run_id = uuid.uuid4()
    _set_curator_run(ft014_database, candidate_id, curator_run_id=curator_run_id)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="confirm",
                    expected_status="candidate", expected_version=1,
                    confirmation_source="curator_auto",
                    curator_run_id=curator_run_id,
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.CONFIRMATION_POLICY_VIOLATION


def test_curator_auto_never_grants_gold(ft014_seed, ft014_database):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    outcome_id = _outcome(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant)
    _set_evidence(
        ft014_database,
        candidate_id,
        [
            {"kind": "photo", "ref": str(photo_id)},
            {"kind": "follow_up_outcome", "ref": str(outcome_id)},
        ],
        follow_up_seen=True,
    )
    curator_run_id = uuid.uuid4()
    _set_curator_run(ft014_database, candidate_id, curator_run_id=curator_run_id)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="confirm",
                    expected_status="candidate", expected_version=1,
                    confirmation_source="curator_auto", quality_tier="gold",
                    curator_run_id=curator_run_id,
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.TRANSITION_FORBIDDEN
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == "candidate"
        assert row.quality_tier == "standard"


def test_curator_auto_stale_run_identity_rejects(ft014_seed, ft014_database):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    outcome_id = _outcome(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant)
    _set_evidence(
        ft014_database,
        candidate_id,
        [
            {"kind": "photo", "ref": str(photo_id)},
            {"kind": "follow_up_outcome", "ref": str(outcome_id)},
        ],
        follow_up_seen=True,
    )
    persisted_run = uuid.uuid4()
    _set_curator_run(ft014_database, candidate_id, curator_run_id=persisted_run)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="confirm",
                    expected_status="candidate", expected_version=1,
                    confirmation_source="curator_auto",
                    curator_run_id=uuid.uuid4(),
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.CONFIRMATION_POLICY_VIOLATION


def test_curator_auto_requires_persisted_selected_decision(
    ft014_seed, ft014_database,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    outcome_id = _outcome(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant)
    _set_evidence(
        ft014_database,
        candidate_id,
        [
            {"kind": "photo", "ref": str(photo_id)},
            {"kind": "follow_up_outcome", "ref": str(outcome_id)},
        ],
        follow_up_seen=True,
    )
    curator_run_id = uuid.uuid4()
    with ft014_database.session() as session, session.begin():
        row = session.get(DatasetCandidate, candidate_id)
        row.curator_decision = "deferred"
        row.curator_run_id = curator_run_id
        row.curator_command_sha256 = _DIGEST
        row.curator_recorded_at = FT014_NOW
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.transition_candidate(
                _transition_command(
                    boss, candidate_id, transition="confirm",
                    expected_status="candidate", expected_version=1,
                    confirmation_source="curator_auto",
                    curator_run_id=curator_run_id,
                )
            )
        assert excinfo.value.code is DatasetGovernanceErrorCode.CONFIRMATION_POLICY_VIOLATION


def test_review_confirm_may_grant_gold(ft014_seed, ft014_database):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant, source_ref=photo_id)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=TimelineRecorder())
        result = service.transition_candidate(
            _transition_command(
                boss, candidate_id, transition="confirm",
                expected_status="candidate", expected_version=1,
                confirmation_source="human_review", quality_tier="gold",
            )
        )
        assert result.to_status == "confirmed"
        assert result.can_train_on is True
        row = session.get(DatasetCandidate, candidate_id)
        assert row.quality_tier == "gold"
        assert row.can_train_on is True


# ---------------------------------------------------------------------------
# Audit: append rollback / commit-failure noise
# ---------------------------------------------------------------------------


def test_append_failure_rolls_back_transition(ft014_seed, ft014_database):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    appender = TimelineRecorder(fail_on="dataset_candidate_reviewed")
    with ft014_database.session() as session:
        with pytest.raises(DatasetGovernanceError) as excinfo:
            with session.begin():
                service = DatasetGovernanceService(session, timeline_appender=appender)
                service.transition_candidate(
                    _transition_command(
                        boss, candidate_id, transition="request_review",
                        expected_status="candidate", expected_version=1,
                    )
                )
        assert excinfo.value.code is DatasetGovernanceErrorCode.AUDIT_FAILED
    with ft014_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == "candidate"
        assert row.record_version == 1
        assert len(row.event_refs) == 1


def test_append_success_then_commit_failure_is_audit_noise(
    ft014_seed, ft014_database, tmp_path,
):
    _farm, boss, _membership, plant = ft014_seed
    candidate_id = _create_candidate(ft014_database, boss, plant)
    settings = AppSettings.from_env().model_copy(
        update={"local_timeline_root": str(tmp_path)}
    )
    appender = TimelineJsonlAppender(settings)
    with ft014_database.session() as session:
        session.begin()
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.transition_candidate(
            _transition_command(
                boss, candidate_id, transition="request_review",
                expected_status="candidate", expected_version=1,
            )
        )
        assert result.to_status == "needs_review"
        try:
            session.execute(text("SELECT 1 FROM nonexistent_probe_table"))
            session.commit()
        except Exception:
            session.rollback()
        else:
            session.rollback()

    with ft014_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
        assert row.candidate_status == "candidate"
        assert row.record_version == 1
        assert len(row.event_refs) == 1

    lines = (tmp_path / "timeline.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["event_type"] == "dataset_candidate_reviewed"


def test_reviewed_timeline_event_is_registered_redacted_canonical(
    ft014_seed, ft014_database, tmp_path,
):
    farm, boss, _membership, plant = ft014_seed
    photo_id = _photo(ft014_database, farm, boss, plant)
    candidate_id = _create_candidate(ft014_database, boss, plant, source_ref=photo_id)
    settings = AppSettings.from_env().model_copy(
        update={"local_timeline_root": str(tmp_path)}
    )
    appender = TimelineJsonlAppender(settings)
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.transition_candidate(
            _transition_command(
                boss, candidate_id, transition="confirm",
                expected_status="candidate", expected_version=1,
                confirmation_source="human_review",
            )
        )
        row = session.get(DatasetCandidate, candidate_id)
        assert row.event_refs[-1] == dict(result.event_ref)
        assert result.event_ref["event_type"] == "dataset_candidate_reviewed"

    lines = (tmp_path / "timeline.jsonl").read_text(encoding="utf-8").strip().splitlines()
    records = [json.loads(line) for line in lines]
    reviewed = [r for r in records if r["event_type"] == "dataset_candidate_reviewed"]
    assert len(reviewed) == 1
    record = reviewed[0]
    assert record["source_type"] == "dataset_candidate"
    assert record["source_id"] == str(candidate_id)
    assert record["payload_summary"] == {
        "from_status": "candidate",
        "to_status": "confirmed",
        "confirmation_source": "human_review",
        "quality_tier": "standard",
        "evidence_ref_count": 1,
        "can_train_on": True,
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

