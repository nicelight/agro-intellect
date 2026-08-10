from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app import AppSettings
from backend.app.dataset_governance import (
    DatasetCandidate,
    DatasetGovernanceError,
    DatasetGovernanceErrorCode,
    DatasetGovernanceService,
    DatasetGovernanceValidationError,
    RecordDatasetEvidenceCommandV1,
)
from backend.app.timeline import TimelineJsonlAppender
from tests.backend.dataset_governance.conftest import (
    TimelineRecorder,
    make_creation_command,
)


def test_created_candidate_has_exact_non_trainable_defaults(ft014_seed, ft014_database):
    farm, boss, _membership, plant = ft014_seed
    source_ref = uuid.uuid4()
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.record_dataset_evidence(
            make_creation_command(
                boss,
                plant_id=plant.plant_id,
                source_ref=source_ref,
            )
        )
        assert result.result == "created"
        row = session.get(DatasetCandidate, result.candidate_id)
        assert row is not None
        assert row.candidate_id == result.candidate_id
        assert row.farm_id == farm.farm_id
        assert row.plant_id == plant.plant_id
        assert row.candidate_status == "candidate"
        assert row.candidate_origin == "raw"
        assert row.quality_tier == "standard"
        assert row.split is None
        assert row.confirmation_source is None
        assert row.can_train_on is False
        assert row.corrected is False
        assert row.follow_up_seen is False
        assert row.record_version == 1
        assert row.source_kind == "photo_catalog_item"
        assert row.source_ref == source_ref
        assert row.evidence_refs == [{"kind": "photo", "ref": str(source_ref)}]
        assert row.curator_decision is None
        assert row.curator_notes_ref is None
        assert row.curator_run_id is None
        assert row.curator_command_sha256 is None
        assert row.curator_recorded_at is None
        assert len(row.event_refs) == 1
        assert len(appender.events) == 1
    with ft014_database.session() as session:
        assert session.get(DatasetCandidate, result.candidate_id) is not None


def test_follow_up_outcome_source_sets_follow_up_seen(ft014_seed, ft014_database):
    _farm, boss, _membership, plant = ft014_seed
    source_ref = uuid.uuid4()
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.record_dataset_evidence(
            make_creation_command(
                boss,
                plant_id=plant.plant_id,
                source_kind="follow_up_outcome",
                source_ref=source_ref,
            )
        )
        row = session.get(DatasetCandidate, result.candidate_id)
        assert row.follow_up_seen is True
        assert row.evidence_refs == [
            {"kind": "follow_up_outcome", "ref": str(source_ref)}
        ]


def test_creation_appends_one_redacted_dataset_candidate_created_ref(
    ft014_seed,
    ft014_database,
    tmp_path,
):
    _farm, boss, _membership, plant = ft014_seed
    settings = AppSettings.from_env().model_copy(
        update={"local_timeline_root": str(tmp_path)}
    )
    appender = TimelineJsonlAppender(settings)
    source_ref = uuid.uuid4()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.record_dataset_evidence(
            make_creation_command(
                boss,
                plant_id=plant.plant_id,
                source_ref=source_ref,
            )
        )
        row = session.get(DatasetCandidate, result.candidate_id)
        assert row.event_refs == [dict(result.event_ref)]
        ref = row.event_refs[0]
        assert set(ref) == {
            "timeline_event_id",
            "timeline_ref",
            "event_type",
            "created_at",
        }
        assert ref["event_type"] == "dataset_candidate_created"
        assert ref["timeline_ref"] == f"timeline.jsonl#{ref['timeline_event_id']}"

    lines = (tmp_path / "timeline.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event_type"] == "dataset_candidate_created"
    assert record["source_type"] == "dataset_candidate"
    assert record["source_id"] == str(result.candidate_id)
    assert record["payload_summary"] == {
        "source_kind": "photo_catalog_item",
        "candidate_origin": "raw",
        "candidate_status": "candidate",
        "evidence_ref_count": 1,
        "quality_tier": "standard",
        "can_train_on": False,
    }
    assert record["source_refs"] == {
        "record_refs": [
            f"dataset_candidate:{result.candidate_id}",
            f"photo_catalog_item:{source_ref}",
        ]
    }
    assert record["actor_ref"]["account_id"] == str(boss.account_id)
    assert record["actor_ref"]["membership_id"] == str(boss.membership_id)
    assert record["redaction_status"] == "clean"
    assert "can_train_on" in json.dumps(record)


def test_same_source_identity_is_idempotent_and_new_source_uuid_is_new_evidence(
    ft014_seed,
    ft014_database,
):
    _farm, boss, _membership, plant = ft014_seed
    source_ref = uuid.uuid4()
    appender = TimelineRecorder()
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        first = service.record_dataset_evidence(
            make_creation_command(
                boss,
                plant_id=plant.plant_id,
                source_ref=source_ref,
            )
        )
        assert first.result == "created"
        duplicate = service.record_dataset_evidence(
            make_creation_command(
                boss,
                plant_id=plant.plant_id,
                source_ref=source_ref,
            )
        )
        assert duplicate.result == "duplicate"
        assert duplicate.candidate_id == first.candidate_id
        assert duplicate.event_ref == first.event_ref

        other = service.record_dataset_evidence(
            make_creation_command(boss, plant_id=plant.plant_id)
        )
        assert other.result == "created"
        assert other.candidate_id != first.candidate_id

        count = session.scalar(
            select(func.count()).select_from(DatasetCandidate)
        )
        assert count == 2
    assert len(appender.events) == 2


def test_caller_authority_fields_are_structurally_rejected(ft014_seed):
    _farm, boss, _membership, plant = ft014_seed
    with pytest.raises(TypeError):
        RecordDatasetEvidenceCommandV1(
            actor_context=boss,
            plant_id=plant.plant_id,
            source_kind="photo_catalog_item",
            source_ref=uuid.uuid4(),
            candidate_status="confirmed",
            quality_tier="gold",
            can_train_on=True,
            split="train",
            confirmation_source="human_review",
        )


def test_service_rejects_non_command_handoff(ft014_seed, ft014_database):
    _farm, boss, _membership, plant = ft014_seed
    with ft014_database.session() as session:
        service = DatasetGovernanceService(
            session,
            timeline_appender=TimelineRecorder(),
        )
        with pytest.raises(DatasetGovernanceValidationError):
            service.record_dataset_evidence(  # type: ignore[arg-type]
                {"actor_context": boss, "plant_id": plant.plant_id}
            )


def test_append_failure_rolls_back_candidate(ft014_seed, ft014_database):
    _farm, boss, _membership, plant = ft014_seed
    appender = TimelineRecorder(fail_on="dataset_candidate_created")
    with ft014_database.session() as session, session.begin():
        service = DatasetGovernanceService(session, timeline_appender=appender)
        with pytest.raises(DatasetGovernanceError) as excinfo:
            service.record_dataset_evidence(
                make_creation_command(boss, plant_id=plant.plant_id)
            )
        assert (
            excinfo.value.code is DatasetGovernanceErrorCode.AUDIT_FAILED
        )
    with ft014_database.session() as session:
        count = session.scalar(select(func.count()).select_from(DatasetCandidate))
        assert count == 0


def test_append_success_then_commit_failure_is_audit_noise(
    ft014_seed,
    ft014_database,
    tmp_path,
):
    _farm, boss, _membership, plant = ft014_seed
    settings = AppSettings.from_env().model_copy(
        update={"local_timeline_root": str(tmp_path)}
    )
    appender = TimelineJsonlAppender(settings)
    with ft014_database.session() as session:
        session.begin()
        service = DatasetGovernanceService(session, timeline_appender=appender)
        result = service.record_dataset_evidence(
            make_creation_command(boss, plant_id=plant.plant_id)
        )
        assert result.result == "created"
        try:
            session.execute(text("SELECT 1 FROM nonexistent_probe_table"))
            session.commit()
        except SQLAlchemyError:
            session.rollback()
        else:
            session.rollback()

    with ft014_database.session() as session:
        count = session.scalar(select(func.count()).select_from(DatasetCandidate))
        assert count == 0

    lines = (tmp_path / "timeline.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event_type"] == "dataset_candidate_created"
