"""FT-014-AC-012 wiring tests from Task & Follow-Up: record_outcome invokes the
Dataset-Governance-owned follow-up evidence association inside its own UoW, so
eligible source candidates gain exactly one typed Outcome ref while
unsupported/terminal/no-match controls stay unchanged."""

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
                captured_at=NOW,
                uploaded_at=NOW,
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
                observed_at=NOW,
                recorded_at=NOW,
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
                measured_at=NOW,
                recorded_at=NOW,
                ph=Decimal("6.10"),
                ec_ms_cm=None,
                source_type="manual_user",
                source_refs={},
                trust_status="confirmed",
                event_refs={},
            )
        )
    return measurement_id


def _candidate_for_source(database, *, source_kind: str, source_ref: uuid.UUID):
    with database.session() as session:
        return session.scalar(
            select(DatasetCandidate)
            .where(
                DatasetCandidate.source_kind == source_kind,
                DatasetCandidate.source_ref == source_ref,
            )
            .execution_options(populate_existing=True)
        )


def _record_outcome(database, boss, *, plant_id, follow_up_task_id, timeline,
                    value=OutcomeValue.IMPROVED, evidence_refs=()):
    with database.session() as session:
        service = TaskFollowUpService(
            session,
            timeline_appender=timeline,
            clock=lambda: NOW,
            dataset_governance=DatasetGovernanceService(
                session,
                timeline_appender=timeline,
                clock=lambda: FT014_NOW,
            ),
        )
        return service.record_outcome(
            RecordOutcomeCommandV1(
                actor_context=boss,
                plant_id=plant_id,
                follow_up_task_id=follow_up_task_id,
                request_id=uuid.uuid4(),
                value=value,
                evidence_refs=evidence_refs,
            )
        )


def test_ft014_ac012_record_outcome_associates_every_eligible_source_candidate(
    ft012_database,
):
    farm = seed_farm(ft012_database)
    boss, _ = create_actor(ft012_database, farm, "boss")
    plant = create_active_plant(ft012_database, boss, plant_key="ac012_all")
    timeline = TimelineRecorder()

    photo_id = _photo_source(ft012_database, farm, boss, plant)
    check_in_id = _check_in_source(ft012_database, farm, boss, plant)
    measurement_id = _measurement_source(ft012_database, farm, boss, plant)

    def create_candidate(source_kind, source_ref):
        with ft012_database.session() as session, session.begin():
            return DatasetGovernanceService(
                session, timeline_appender=timeline, clock=lambda: FT014_NOW
            ).record_dataset_evidence(
                RecordDatasetEvidenceCommandV1(
                    actor_context=boss,
                    plant_id=plant.plant_id,
                    source_kind=source_kind,
                    source_ref=source_ref,
                )
            ).candidate_id

    photo_candidate = create_candidate(
        SourceKind.PHOTO_CATALOG_ITEM, photo_id
    )
    check_in_candidate = create_candidate(SourceKind.DAILY_CHECK_IN, check_in_id)
    measurement_candidate = create_candidate(
        SourceKind.MANUAL_MEASUREMENT, measurement_id
    )

    follow_up = _open_follow_up(ft012_database, farm, boss, plant, timeline)
    result = _record_outcome(
        ft012_database,
        boss,
        plant_id=plant.plant_id,
        follow_up_task_id=follow_up.task_id,
        timeline=timeline,
        evidence_refs=(
            f"photo_catalog_item:{photo_id}",
            f"daily_checkin:{check_in_id}",
            f"manual_measurement:{measurement_id}",
        ),
    )
    outcome_id = result.outcome.outcome_id

    assert result.result == "created"
    for candidate_id in (
        photo_candidate,
        check_in_candidate,
        measurement_candidate,
    ):
        with ft012_database.session() as session:
            row = session.get(DatasetCandidate, candidate_id)
            assert row is not None
            assert row.evidence_refs[-1] == {
                "kind": "follow_up_outcome",
                "ref": str(outcome_id),
            }
            assert row.follow_up_seen is True
            assert row.record_version == 2
            assert row.can_train_on is False
            assert len(row.event_refs) == 2
    linked = [
        e for e in timeline.events if e.event_type == "dataset_candidate_evidence_linked"
    ]
    assert len(linked) == 3
    assert all(e.payload_summary["follow_up_seen"] is True for e in linked)
    assert all(e.payload_summary["can_train_on"] is False for e in linked)

    outcome_candidate = _candidate_for_source(
        ft012_database, source_kind="follow_up_outcome", source_ref=outcome_id
    )
    assert outcome_candidate is not None
    assert outcome_candidate.evidence_refs == [
        {"kind": "follow_up_outcome", "ref": str(outcome_id)}
    ]
    assert outcome_candidate.record_version == 1


def test_ft014_ac012_terminal_and_zero_match_controls_stay_unchanged(
    ft012_database,
):
    farm = seed_farm(ft012_database)
    boss, _ = create_actor(ft012_database, farm, "boss")
    plant = create_active_plant(ft012_database, boss, plant_key="ac012_ctrl")
    timeline = TimelineRecorder()

    confirmed_photo = _photo_source(ft012_database, farm, boss, plant)
    rejected_photo = _photo_source(ft012_database, farm, boss, plant)
    no_candidate_photo = _photo_source(ft012_database, farm, boss, plant)

    confirmed_candidate = _candidate_for_source(
        ft012_database, source_kind="photo_catalog_item", source_ref=confirmed_photo
    )
    if confirmed_candidate is None:
        with ft012_database.session() as session, session.begin():
            confirmed_candidate = DatasetGovernanceService(
                session, timeline_appender=timeline, clock=lambda: FT014_NOW
            ).record_dataset_evidence(
                RecordDatasetEvidenceCommandV1(
                    actor_context=boss,
                    plant_id=plant.plant_id,
                    source_kind=SourceKind.PHOTO_CATALOG_ITEM,
                    source_ref=confirmed_photo,
                )
            ).candidate_id
            row = session.get(DatasetCandidate, confirmed_candidate)
            row.candidate_status = "confirmed"
    rejected_candidate = _candidate_for_source(
        ft012_database, source_kind="photo_catalog_item", source_ref=rejected_photo
    )
    if rejected_candidate is None:
        with ft012_database.session() as session, session.begin():
            rejected_candidate = DatasetGovernanceService(
                session, timeline_appender=timeline, clock=lambda: FT014_NOW
            ).record_dataset_evidence(
                RecordDatasetEvidenceCommandV1(
                    actor_context=boss,
                    plant_id=plant.plant_id,
                    source_kind=SourceKind.PHOTO_CATALOG_ITEM,
                    source_ref=rejected_photo,
                )
            ).candidate_id
            row = session.get(DatasetCandidate, rejected_candidate)
            row.candidate_status = "rejected"

    follow_up = _open_follow_up(ft012_database, farm, boss, plant, timeline)
    result = _record_outcome(
        ft012_database,
        boss,
        plant_id=plant.plant_id,
        follow_up_task_id=follow_up.task_id,
        timeline=timeline,
        evidence_refs=(
            f"photo_catalog_item:{confirmed_photo}",
            f"photo_catalog_item:{rejected_photo}",
            f"photo_catalog_item:{no_candidate_photo}",
        ),
    )
    outcome_id = result.outcome.outcome_id
    assert result.result == "created"

    with ft012_database.session() as session:
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
    linked = [
        e for e in timeline.events if e.event_type == "dataset_candidate_evidence_linked"
    ]
    assert len(linked) == 0
    # Outcome candidate still created alone.
    assert (
        _candidate_for_source(
            ft012_database, source_kind="follow_up_outcome", source_ref=outcome_id
        )
        is not None
    )


def test_ft014_ac012_identical_retry_adds_no_association_and_public_result_unchanged(
    ft012_database,
):
    farm = seed_farm(ft012_database)
    boss, _ = create_actor(ft012_database, farm, "boss")
    plant = create_active_plant(ft012_database, boss, plant_key="ac012_idem")
    timeline = TimelineRecorder()

    photo_id = _photo_source(ft012_database, farm, boss, plant)
    with ft012_database.session() as session, session.begin():
        candidate_id = DatasetGovernanceService(
            session, timeline_appender=timeline, clock=lambda: FT014_NOW
        ).record_dataset_evidence(
            RecordDatasetEvidenceCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                source_kind=SourceKind.PHOTO_CATALOG_ITEM,
                source_ref=photo_id,
            )
        ).candidate_id

    follow_up = _open_follow_up(ft012_database, farm, boss, plant, timeline)
    command = RecordOutcomeCommandV1(
        actor_context=boss,
        plant_id=plant.plant_id,
        follow_up_task_id=follow_up.task_id,
        request_id=uuid.uuid4(),
        value=OutcomeValue.IMPROVED,
        evidence_refs=(f"photo_catalog_item:{photo_id}",),
    )
    with ft012_database.session() as session:
        first = TaskFollowUpService(
            session,
            timeline_appender=timeline,
            clock=lambda: NOW,
            dataset_governance=DatasetGovernanceService(
                session, timeline_appender=timeline, clock=lambda: FT014_NOW
            ),
        ).record_outcome(command)
    outcome_id = first.outcome.outcome_id
    with ft012_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
        assert row.record_version == 2
        assert [r for r in row.evidence_refs if r["kind"] == "follow_up_outcome"] == [
            {"kind": "follow_up_outcome", "ref": str(outcome_id)}
        ]

    timeline.events.clear()
    with ft012_database.session() as session:
        second = TaskFollowUpService(
            session,
            timeline_appender=timeline,
            clock=lambda: NOW,
            dataset_governance=DatasetGovernanceService(
                session, timeline_appender=timeline, clock=lambda: FT014_NOW
            ),
        ).record_outcome(command)
    assert second.result == "duplicate"
    assert second.outcome.outcome_id == outcome_id
    assert second.task.task_id == follow_up.task_id
    assert second.task.status == "completed"
    with ft012_database.session() as session:
        row = session.get(DatasetCandidate, candidate_id)
        assert row.record_version == 2
        assert len(row.evidence_refs) == 2
        assert len(row.event_refs) == 2
    assert timeline.events == []


def test_ft014_ac012_association_audit_failure_rolls_back_whole_transaction(
    ft012_database,
):
    farm = seed_farm(ft012_database)
    boss, _ = create_actor(ft012_database, farm, "boss")
    plant = create_active_plant(ft012_database, boss, plant_key="ac012_audit")
    recorder = TimelineRecorder(fail_on="dataset_candidate_evidence_linked")

    photo_id = _photo_source(ft012_database, farm, boss, plant)
    with ft012_database.session() as session, session.begin():
        candidate_id = DatasetGovernanceService(
            session, timeline_appender=recorder, clock=lambda: FT014_NOW
        ).record_dataset_evidence(
            RecordDatasetEvidenceCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                source_kind=SourceKind.PHOTO_CATALOG_ITEM,
                source_ref=photo_id,
            )
        ).candidate_id

    follow_up = _open_follow_up(ft012_database, farm, boss, plant, recorder)
    with ft012_database.session() as session, pytest.raises(TaskFollowUpError) as failed:
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
                evidence_refs=(f"photo_catalog_item:{photo_id}",),
            )
        )
    assert failed.value.code is TaskFollowUpErrorCode.TASK_AUDIT_FAILED
    with ft012_database.session() as session:
        stored = session.get(Task, follow_up.task_id)
        assert stored is not None and stored.status == "open"
        assert session.scalar(select(func.count(Outcome.outcome_id))) == 0
        row = session.get(DatasetCandidate, candidate_id)
        assert len(row.evidence_refs) == 1
        assert row.record_version == 1
        assert row.follow_up_seen is False


def test_ft014_ac012_archive_and_unauthorized_deny_before_any_write(
    ft012_database,
):
    farm = seed_farm(ft012_database)
    boss, _ = create_actor(ft012_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft012_database, farm, "engineer")
    consultant, consultant_membership = create_actor(
        ft012_database, farm, "consultant"
    )
    timeline = TimelineRecorder()

    revoked_plant = create_active_plant(ft012_database, boss, plant_key="ac012_rev")
    grant_access(
        ft012_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    revoke_access(
        ft012_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archived_plant = create_active_plant(ft012_database, boss, plant_key="ac012_arch")
    grant_access(
        ft012_database,
        boss,
        plant_id=archived_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archive_plant(ft012_database, boss, plant_id=archived_plant.plant_id)
    consultant_plant = create_active_plant(
        ft012_database, boss, plant_key="ac012_consult"
    )
    grant_access(
        ft012_database,
        boss,
        plant_id=consultant_plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )
    ungranted_plant = create_active_plant(
        ft012_database, boss, plant_key="ac012_ungranted"
    )

    for actor, plant in [
        (engineer, revoked_plant),
        (boss, archived_plant),
        (consultant, consultant_plant),
        (engineer, ungranted_plant),
    ]:
        with ft012_database.session() as session, pytest.raises(TaskFollowUpError) as denied:
            TaskFollowUpService(
                session, timeline_appender=timeline, clock=lambda: NOW
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

    with ft012_database.session() as session:
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
        assert session.scalar(select(func.count(Outcome.outcome_id))) == 0
    assert timeline.events == []
