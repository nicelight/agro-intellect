from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest
from sqlalchemy import select

from backend.app.agent_runtime import ModelExecution
from backend.app.plant_state import (
    PlantStateCommand,
    PlantStateRecord,
    PlantStateRuntimeService,
)
from tests.backend.plant_operations.conftest import (
    create_actor,
    grant_access,
    revoke_access,
)


class _Executor:
    model_ref = "test_provider:model_1"

    def __init__(self, result_factory, *, before_return=None):
        self.result_factory = result_factory
        self.before_return = before_return
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        if self.before_return:
            self.before_return()
        return ModelExecution(
            model_ref=self.model_ref,
            result=self.result_factory(request),
        )


class _FailingExecutor:
    model_ref = "test_provider:model_1"

    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        raise TimeoutError("synthetic provider timeout secret=do-not-log")


def _command(actor, plant):
    return PlantStateCommand(
        run_id=uuid.uuid4(),
        requested_at=datetime.now(timezone.utc),
        actor_context=actor,
        plant_id=plant.plant_id,
    )


def _seed_records(database, farm, plant, *, count=2, opposing=True):
    now = datetime.now(timezone.utc)
    rows = []
    with database.session() as session, session.begin():
        for index in range(count):
            polarity = "present"
            severity = "mild" if index == 0 else "moderate"
            if opposing and index == 1:
                polarity = "absent"
                severity = "none"
            row = PlantStateRecord(
                state_record_id=uuid.uuid4(),
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                record_kind="vision_observation",
                agent_id="vision_observation",
                run_id=uuid.uuid4(),
                message_id=uuid.uuid4(),
                observation_key="leaf_spots",
                polarity=polarity,
                severity=severity,
                assessment_kind=None,
                direction=None,
                summary=f"Synthetic record {index}",
                confidence=Decimal("0.75000"),
                trust_status="observed",
                source_refs=[f"photo:{uuid.uuid4()}"],
                observed_at=now + timedelta(seconds=index),
                recorded_at=now + timedelta(seconds=index),
                confirmation_source=None,
                confirmed_by_account_id=None,
                confirmed_by_membership_id=None,
                confirmed_at=None,
                version=1,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            rows.append(row)
    return rows


def _conflict(request):
    return {
        "schema_version": 1,
        "runtime_decision": "speak",
        "assessment_kind": "conflict",
        "observation_key": "leaf_spots",
        "direction": "not_applicable",
        "summary": "Present and absent evidence remains contradictory.",
        "confidence": 0.8,
        "source_refs": list(request.source_refs),
        "reason_code": None,
    }


def test_fake_spy_reads_latest_records_and_returns_pending_conflict_candidate(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    rows = _seed_records(ft009_database, farm, plant)
    executor = _Executor(_conflict)
    with ft009_database.session() as session:
        outcome = PlantStateRuntimeService(
            session,
            model_executor=executor,
            timeline_append=event_ref_factory,
        ).invoke(_command(boss, plant))
    assert outcome.outcome_kind == "envelope_ready"
    assert outcome.message_envelope is not None
    assert outcome.message_envelope.publication_state == "pending_classification"
    assert outcome.message_envelope.consumable_by_agents is False
    assert outcome.message_envelope.candidate_claim_type == "hypothesis"
    assert outcome.state_candidate is not None
    assert outcome.state_candidate.assessment_kind == "conflict"
    request = executor.requests[0]
    assert request.source_refs == tuple(
        f"plant_state_record:{item.state_record_id}" for item in rows
    )
    payload = request.as_provider_payload()
    for forbidden in (
        "confirmed_by_account_id",
        "session_id",
        "membership_id",
        "authorization_scope",
        "provider_payload",
        "hidden_reasoning",
    ):
        assert forbidden not in str(payload)
    event = event_ref_factory.events[-1]
    assert event.payload_summary["outcome_kind"] == "envelope_ready"
    assert "summary" not in event.payload_summary
    assert "candidate_output" not in event.payload_summary


def test_latest_four_oldest_to_newest_and_structural_mislabel_is_invalid(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    rows = _seed_records(ft009_database, farm, plant, count=5, opposing=False)

    def invalid(request):
        value = _conflict(request)
        return value

    executor = _Executor(invalid)
    with ft009_database.session() as session:
        outcome = PlantStateRuntimeService(
            session,
            model_executor=executor,
            timeline_append=event_ref_factory,
        ).invoke(_command(boss, plant))
    assert executor.requests[0].source_refs == tuple(
        f"plant_state_record:{item.state_record_id}" for item in rows[-4:]
    )
    assert outcome.outcome_kind == "output_invalid"
    assert outcome.message_envelope is None
    assert outcome.state_candidate is None


def test_unbound_timeout_malformed_and_post_io_revocation_fail_closed(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    _seed_records(ft009_database, farm, plant)
    with ft009_database.session() as session:
        unbound = PlantStateRuntimeService(
            session,
            model_executor=None,
            timeline_append=event_ref_factory,
        ).invoke(_command(boss, plant))
    assert unbound.outcome_kind == "runtime_not_configured"
    assert unbound.provider_call_status == "not_attempted"

    with ft009_database.session() as session:
        failed = PlantStateRuntimeService(
            session,
            model_executor=_FailingExecutor(),
            timeline_append=event_ref_factory,
        ).invoke(_command(boss, plant))
    assert failed.outcome_kind == "provider_failed"
    assert failed.message_envelope is None
    assert "do-not-log" not in str(event_ref_factory.events[-1])

    malformed = _Executor(lambda request: {**_conflict(request), "secret": "raw"})
    with ft009_database.session() as session:
        invalid = PlantStateRuntimeService(
            session,
            model_executor=malformed,
            timeline_append=event_ref_factory,
        ).invoke(_command(boss, plant))
    assert invalid.outcome_kind == "output_invalid"
    assert "raw" not in str(event_ref_factory.events[-1])

    engineer, membership = create_actor(ft009_database, farm, "engineer")
    grant_access(
        ft009_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    race = _Executor(
        _conflict,
        before_return=lambda: revoke_access(
            ft009_database,
            boss,
            plant_id=plant.plant_id,
            membership_id=membership.membership_id,
        ),
    )
    with ft009_database.session() as session:
        denied = PlantStateRuntimeService(
            session,
            model_executor=race,
            timeline_append=event_ref_factory,
        ).invoke(_command(engineer, plant))
    assert denied.outcome_kind == "publication_guard_denied"
    assert denied.message_envelope is None
    assert denied.state_candidate is None
