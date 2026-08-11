"""FT-014-AC-012 wiring tests from the Dataset Governance side: record_outcome
invokes associate_follow_up_evidence in the same UoW, so eligible source
candidates gain exactly one typed Outcome ref while confirmed/terminal,
unsupported, and no-match controls stay unchanged and the separate Outcome
candidate is untouched."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
import uuid

import pytest
from sqlalchemy import func, select

from backend.app.dataset_governance import (
    DatasetCandidate,
    DatasetGovernanceService,
    RecordDatasetEvidenceCommandV1,
    SourceKind,
)
from backend.app.photo_intake import PhotoCatalogItem
from backend.app.plant_operations import DailyCheckIn, ManualMeasurement
from backend.app.task_follow_up import (
    CompleteTaskCommandV1,
    Outcome,
    OutcomeValue,
    RecordOutcomeCommandV1,
    Task,
    TaskFollowUpError,
    TaskFollowUpErrorCode,
    TaskFollowUpService,
)
from tests.backend.dataset_governance.conftest import FT014_NOW, TimelineRecorder
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    create_active_plant,
    grant_access,
    revoke_access,
    seed_farm,
)
from tests.backend.task_follow_up.test_domain_loop import (
    NOW,
    _approval_command,
    _measurement,
    _pending_decision,
)

_DIGEST = "a" * 64


def _open_follow_up(database, farm, boss, plant, timeline):
    decision_id, _ph, _ec = _pending_decision(
        database,
        farm,
        boss,
        plant,
        expires_at=NOW + timedelta(hours=1),
    )
    with database.session() as session:
        service = TaskFollowUpService(
            session, timeline_appender=timeline, clock=lambda: NOW
        )
        service.materialize_pending_approval(decision_id)
        action = service.decide_approval(
            _approval_command(boss, plant, decision_id)
        ).action_task
    with database.session() as session:
        follow_up = TaskFollowUpService(
            session, timeline_appender=timeline, clock=lambda: NOW
        ).complete_task(
            CompleteTaskCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                task_id=action.task_id,
                request_id=uuid.uuid4(),
            )
        ).follow_up_task
    assert follow_up is not None and follow_up.status == "open"
    return follow_up


def _photo_source(database, farm, boss, plant):
    photo_id = uuid.uuid4()
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


def _check_in_source(database, farm, boss, plant):
    check_in_id = uuid.uuid4()
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


def _measurement_source(database, farm, boss, plant):
    measurement_id = uuid.uuid4()
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


def _create_candidate(database, boss, plant, *, source_kind, source_ref,
                      status="candidate", recorder=None):
    recorder = recorder or TimelineRecorder()
    with database.session() as session, session.begin():
        service = DatasetGovernanceService(
            session, timeline_appender=recorder, clock=lambda: FT014_NOW
        )
        result = service.record_dataset_evidence(
            RecordDatasetEvidenceCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                source_kind=source_kind,
                source_ref=source_ref,
            )
        )
        if status != "candidate":
            row = session.get(DatasetCandidate, result.candidate_id)
            row.candidate_status = status
    return result.candidate_id


def test_ft014_ac012_wiring_enriches_all_eligible_kinds_in_same_uow(ft014_database):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_ac012_all")
    recorder = TimelineRecorder()

    photo_id = _photo_source(ft014_database, farm, boss, plant)
    check_in_id = _check_in_source(ft014_database, farm, boss, plant)
    measurement_id = _measurement_source(ft014_database, farm, boss, plant)
    photo_candidate = _create_candidate(
        ft014_database, boss, plant, source_kind=SourceKind.PHOTO_CATALOG_ITEM,
        source_ref=photo_id,
    )
    check_in_candidate = _create_candidate(
        ft014_database, boss, plant, source_kind=SourceKind.DAILY_CHECK_IN,
        source_ref=check_in_id,
    )
    measurement_candidate = _create_candidate(
        ft014_database, boss, plant, source_kind=SourceKind.MANUAL_MEASUREMENT,
        source_ref=measurement_id,
    )

    follow_up = _open_follow_up(ft014_database, farm, boss, plant, recorder)
    with ft014_database.session() as session:
        result = TaskFollowUpService(
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
                evidence_refs=(
                    f"photo_catalog_item:{photo_id}",
                    f"daily_checkin:{check_in_id}",
                    f"manual_measurement:{measurement_id}",
                ),
            )
        )
    outcome_id = result.outcome.outcome_id
    assert result.result == "created"

    for candidate_id in (
        photo_candidate,
        check_in_candidate,
        measurement_candidate,
    ):
        with ft014_database.session() as session:
            row = session.get(DatasetCandidate, candidate_id)
            assert row.evidence_refs[-1] == {
                "kind": "follow_up_outcome",
                "ref": str(outcome_id),
            }
            assert row.follow_up_seen is True
            assert row.record_version == 2
            assert len(row.event_refs) == 2
    linked = [
        e for e in recorder.events
        if e.event_type == "dataset_candidate_evidence_linked"
    ]
    assert len(linked) == 3

    with ft014_database.session() as session:
        outcome_candidate = session.scalar(
            select(DatasetCandidate).where(
                DatasetCandidate.source_ref == outcome_id
            )
        )
        assert outcome_candidate is not None
        assert outcome_candidate.source_kind == "follow_up_outcome"
        assert outcome_candidate.evidence_refs == [
            {"kind": "follow_up_outcome", "ref": str(outcome_id)}
        ]
        assert outcome_candidate.record_version == 1


def test_ft014_ac012_wiring_confirmed_terminal_and_missing_controls(ft014_database):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_ac012_ctrl")
    recorder = TimelineRecorder()

    confirmed_photo = _photo_source(ft014_database, farm, boss, plant)
    rejected_photo = _photo_source(ft014_database, farm, boss, plant)
    no_candidate_photo = _photo_source(ft014_database, farm, boss, plant)
    confirmed_candidate = _create_candidate(
        ft014_database, boss, plant, source_kind=SourceKind.PHOTO_CATALOG_ITEM,
        source_ref=confirmed_photo, status="confirmed",
    )
    rejected_candidate = _create_candidate(
        ft014_database, boss, plant, source_kind=SourceKind.PHOTO_CATALOG_ITEM,
        source_ref=rejected_photo, status="rejected",
    )

    follow_up = _open_follow_up(ft014_database, farm, boss, plant, recorder)
    with ft014_database.session() as session:
        result = TaskFollowUpService(
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
                evidence_refs=(
                    f"photo_catalog_item:{confirmed_photo}",
                    f"photo_catalog_item:{rejected_photo}",
                    f"photo_catalog_item:{no_candidate_photo}",
                ),
            )
        )
    outcome_id = result.outcome.outcome_id
    assert result.result == "created"

    with ft014_database.session() as session:
        confirmed_row = session.get(DatasetCandidate, confirmed_candidate)
        assert len(confirmed_row.evidence_refs) == 1
        assert confirmed_row.record_version == 1
        assert confirmed_row.follow_up_seen is False
        rejected_row = session.get(DatasetCandidate, rejected_candidate)
        assert len(rejected_row.evidence_refs) == 1
        assert rejected_row.record_version == 1
        assert rejected_row.follow_up_seen is False
        assert (
            session.scalar(
                select(func.count(DatasetCandidate.candidate_id)).where(
                    DatasetCandidate.source_ref == no_candidate_photo
                )
            )
            == 0
        )
        outcome_candidate = session.scalar(
            select(DatasetCandidate).where(
                DatasetCandidate.source_ref == outcome_id
            )
        )
        assert outcome_candidate is not None
        assert outcome_candidate.record_version == 1
    assert len(
        [e for e in recorder.events if e.event_type == "dataset_candidate_evidence_linked"]
    ) == 0


def test_ft014_ac012_wiring_unsupported_ref_fails_closed_and_rolls_back(
    ft014_database,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_ac012_bad")
    recorder = TimelineRecorder()

    follow_up = _open_follow_up(ft014_database, farm, boss, plant, recorder)
    with ft014_database.session() as session, pytest.raises(TaskFollowUpError) as failed:
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
                evidence_refs=(f"arbitrary_evidence:{uuid.uuid4()}",),
            )
        )
    assert failed.value.code is TaskFollowUpErrorCode.TASK_EVIDENCE_REQUIRED
    with ft014_database.session() as session:
        stored = session.get(Task, follow_up.task_id)
        assert stored is not None and stored.status == "open"
        assert session.scalar(select(func.count(Outcome.outcome_id))) == 0
        assert session.scalar(
            select(func.count(DatasetCandidate.candidate_id))
        ) == 0


def test_ft014_ac012_wiring_archive_and_unauthorized_no_candidate_no_outcome(
    ft014_database,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft014_database, farm, "engineer")
    consultant, consultant_membership = create_actor(
        ft014_database, farm, "consultant"
    )
    recorder = TimelineRecorder()

    revoked_plant = create_active_plant(
        ft014_database, boss, plant_key="wire_ac012_revoked"
    )
    grant_access(
        ft014_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    revoke_access(
        ft014_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archived_plant = create_active_plant(
        ft014_database, boss, plant_key="wire_ac012_archived"
    )
    grant_access(
        ft014_database,
        boss,
        plant_id=archived_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archive_plant(ft014_database, boss, plant_id=archived_plant.plant_id)
    consultant_plant = create_active_plant(
        ft014_database, boss, plant_key="wire_ac012_consultant"
    )
    grant_access(
        ft014_database,
        boss,
        plant_id=consultant_plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )
    ungranted_plant = create_active_plant(
        ft014_database, boss, plant_key="wire_ac012_ungranted"
    )

    for actor, plant in [
        (engineer, revoked_plant),
        (boss, archived_plant),
        (consultant, consultant_plant),
        (engineer, ungranted_plant),
    ]:
        with ft014_database.session() as session, pytest.raises(TaskFollowUpError) as denied:
            TaskFollowUpService(
                session, timeline_appender=recorder, clock=lambda: NOW
            ).record_outcome(
                RecordOutcomeCommandV1(
                    actor_context=actor,
                    plant_id=plant.plant_id,
                    follow_up_task_id=uuid.uuid4(),
                    request_id=uuid.uuid4(),
                    value=OutcomeValue.NO_DATA,
                    evidence_refs=(),
                )
            )
        assert denied.value.code in {
            TaskFollowUpErrorCode.TASK_SCOPE_NOT_FOUND,
            TaskFollowUpErrorCode.TASK_COMMAND_FORBIDDEN,
            TaskFollowUpErrorCode.TASK_PLANT_NOT_ACTIVE,
        }

    with ft014_database.session() as session:
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
        assert session.scalar(select(func.count(Outcome.outcome_id))) == 0
    assert recorder.events == []
