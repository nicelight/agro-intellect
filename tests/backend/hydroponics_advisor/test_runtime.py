from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from sqlalchemy import func, select

from backend.app.agent_runtime import ModelExecution
from backend.app.hydroponics_advisor import (
    HydroponicsAdvisorCommandV1,
    HydroponicsAdvisorRuntimeService,
)
from backend.app.plant_operations.models import DailyCheckIn, ManualMeasurement
from backend.app.plant_state import PlantStateRecord
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    grant_access,
    revoke_access,
)


class _Executor:
    model_ref = "test_provider:advisor_v1"

    def __init__(self, result_factory, *, before_return=None):
        self.result_factory = result_factory
        self.before_return = before_return
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        if self.before_return is not None:
            self.before_return()
        return ModelExecution(
            model_ref=self.model_ref,
            result=self.result_factory(request),
        )


class _FailingExecutor:
    model_ref = "test_provider:advisor_v1"

    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        raise TimeoutError("synthetic timeout credential=never-persist")


def _command(actor, plant, *, goal="missing_data_review"):
    return HydroponicsAdvisorCommandV1(
        run_id=uuid.uuid4(),
        requested_at=datetime.now(timezone.utc),
        actor_context=actor,
        plant_id=plant.plant_id,
        request_reason="manual_review",
        analysis_goal=goal,
    )


def _measurement_request(request):
    return {
        "schema_version": 1,
        "runtime_decision": "speak",
        "advice_kind": "measurement_request",
        "candidate_output": None,
        "confidence": None,
        "requested_measurements": list(request.analysis_freshness.missing_or_stale),
        "source_refs": list(request.policy_source_refs()),
        "reason_code": "critical_measurements_required",
    }


def _recommendation(request):
    return {
        "schema_version": 1,
        "runtime_decision": "speak",
        "advice_kind": "recommendation",
        "candidate_output": "<b>Opaque pending recommendation</b>",
        "confidence": 0.75,
        "requested_measurements": [],
        "source_refs": list(request.source_refs),
        "reason_code": None,
    }


def _seed_context(database, farm, actor, plant, *, now, ph_at=None, ec_at=None, combined=False):
    with database.session() as session, session.begin():
        check_in = DailyCheckIn(
            check_in_id=uuid.uuid4(),
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
            actor_account_id=actor.account_id,
            actor_membership_id=actor.membership_id,
            check_in_state="completed",
            observed_at=now - timedelta(hours=3),
            recorded_at=now - timedelta(hours=3),
            observation_state="observed",
            observation_text="Leaves inspected.",
            source_refs={},
            event_refs={},
            created_at=now - timedelta(hours=3),
        )
        session.add(check_in)
        if combined and ph_at is not None and ec_at is not None:
            session.add(
                _measurement_row(
                    farm,
                    actor,
                    plant,
                    measured_at=max(ph_at, ec_at),
                    ph=Decimal("6.50"),
                    ec=Decimal("1.250"),
                    now=now,
                )
            )
        else:
            if ph_at is not None:
                session.add(
                    _measurement_row(
                        farm,
                        actor,
                        plant,
                        measured_at=ph_at,
                        ph=Decimal("6.50"),
                        ec=None,
                        now=now,
                    )
                )
            if ec_at is not None:
                session.add(
                    _measurement_row(
                        farm,
                        actor,
                        plant,
                        measured_at=ec_at,
                        ph=None,
                        ec=Decimal("1.250"),
                        now=now,
                    )
                )
        session.add(
            PlantStateRecord(
                state_record_id=uuid.uuid4(),
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                record_kind="vision_observation",
                agent_id="vision_observation",
                run_id=uuid.uuid4(),
                message_id=uuid.uuid4(),
                observation_key="leaf_spots",
                polarity="absent",
                severity="none",
                assessment_kind=None,
                direction=None,
                summary="No visible leaf spots.",
                confidence=Decimal("0.80000"),
                trust_status="observed",
                source_refs=[f"photo:{uuid.uuid4()}"],
                observed_at=now - timedelta(hours=2),
                recorded_at=now - timedelta(hours=2),
                confirmation_source=None,
                confirmed_by_account_id=None,
                confirmed_by_membership_id=None,
                confirmed_at=None,
                version=1,
                created_at=now - timedelta(hours=2),
                updated_at=now - timedelta(hours=2),
            )
        )


def _measurement_row(farm, actor, plant, *, measured_at, ph, ec, now):
    return ManualMeasurement(
        measurement_id=uuid.uuid4(),
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        check_in_id=None,
        actor_account_id=actor.account_id,
        actor_membership_id=actor.membership_id,
        measured_at=measured_at,
        recorded_at=now - timedelta(minutes=1),
        ph=ph,
        ec_ms_cm=ec,
        provenance_note=None,
        source_type="manual_user",
        source_refs={},
        trust_status="confirmed",
        event_refs={},
        created_at=now - timedelta(minutes=1),
    )


def _state_count(database):
    with database.session() as session:
        return session.scalar(select(func.count(PlantStateRecord.state_record_id)))


def test_missing_ph_and_stale_ec_make_one_exact_pending_measurement_request(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _seed_context(
        ft009_database,
        farm,
        boss,
        plant,
        now=now,
        ec_at=now - timedelta(hours=24, seconds=1),
    )
    before_state = _state_count(ft009_database)
    executor = _Executor(_measurement_request)
    with ft009_database.session() as session:
        outcome = HydroponicsAdvisorRuntimeService(
            session,
            model_executor=executor,
            timeline_append=event_ref_factory,
            clock=lambda: now,
        ).invoke(_command(boss, plant))

    assert len(executor.requests) == 1
    request = executor.requests[0]
    assert request.analysis_freshness.missing_or_stale == ("ph", "ec")
    assert request.analysis_freshness.ph.status == "missing"
    assert request.analysis_freshness.ec.status == "stale"
    assert [record.record_type for record in request.records] == [
        "plant",
        "manual_measurement",
        "daily_checkin",
        "plant_state_record",
    ]
    assert outcome.outcome_kind == "envelope_ready"
    envelope = outcome.message_envelope
    assert envelope is not None
    assert envelope.candidate_claim_type == "task_request"
    assert envelope.candidate_output == "Нужны свежие измерения pH и EC перед рекомендацией."
    assert envelope.confidence == 1.0
    assert envelope.source_refs == request.policy_source_refs()
    assert envelope.publication_state == "pending_classification"
    assert envelope.consumable_by_agents is False
    assert _state_count(ft009_database) == before_state
    assert len(event_ref_factory.events) == 1
    event = event_ref_factory.events[0]
    assert event.payload_summary["outcome_kind"] == "envelope_ready"
    assert "candidate_output" not in event.payload_summary
    payload_text = str(request.as_provider_payload())
    for forbidden in (
        "session_id",
        "membership_id",
        "authorization_scope",
        "provider_history",
        "hidden_reasoning",
        "credential",
        "local_path",
    ):
        assert forbidden not in payload_text


def test_closed_24_hour_boundary_is_fresh_and_future_value_is_stale(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _seed_context(
        ft009_database,
        farm,
        boss,
        plant,
        now=now,
        ph_at=now - timedelta(hours=24),
        ec_at=now + timedelta(seconds=1),
    )
    executor = _Executor(_measurement_request)
    with ft009_database.session() as session:
        outcome = HydroponicsAdvisorRuntimeService(
            session,
            model_executor=executor,
            timeline_append=event_ref_factory,
            clock=lambda: now,
        ).invoke(_command(boss, plant))
    request = executor.requests[0]
    assert request.analysis_freshness.ph.status == "fresh"
    assert request.analysis_freshness.ec.status == "stale"
    assert request.analysis_freshness.missing_or_stale == ("ec",)
    assert outcome.message_envelope is not None
    assert outcome.message_envelope.candidate_output == (
        "Нужно свежее измерение EC перед рекомендацией."
    )


def test_fresh_combined_measurement_keeps_both_context_rows_and_pending_text(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _seed_context(
        ft009_database,
        farm,
        boss,
        plant,
        now=now,
        ph_at=now - timedelta(hours=1),
        ec_at=now - timedelta(hours=1),
        combined=True,
    )
    executor = _Executor(_recommendation)
    with ft009_database.session() as session:
        outcome = HydroponicsAdvisorRuntimeService(
            session,
            model_executor=executor,
            timeline_append=event_ref_factory,
            clock=lambda: now,
        ).invoke(_command(boss, plant, goal="general_hydroponics_review"))
    request = executor.requests[0]
    assert request.analysis_freshness.missing_or_stale == ()
    assert request.analysis_freshness.ph.source_ref == request.analysis_freshness.ec.source_ref
    assert [record.record_type for record in request.records] == [
        "plant",
        "manual_measurement",
        "daily_checkin",
        "plant_state_record",
    ]
    assert outcome.outcome_kind == "envelope_ready"
    assert outcome.message_envelope is not None
    assert outcome.message_envelope.candidate_claim_type == "recommendation"
    assert outcome.message_envelope.candidate_output == (
        "<b>Opaque pending recommendation</b>"
    )
    assert outcome.message_envelope.publication_state == "pending_classification"
    assert outcome.message_envelope.consumable_by_agents is False


def test_advice_or_silence_is_invalid_while_critical_data_is_unavailable(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _seed_context(ft009_database, farm, boss, plant, now=now)
    for factory in (
        _recommendation,
        lambda _request: {
            "schema_version": 1,
            "runtime_decision": "silent",
            "advice_kind": None,
            "candidate_output": None,
            "confidence": None,
            "requested_measurements": [],
            "source_refs": [],
            "reason_code": "insufficient_evidence",
        },
    ):
        with ft009_database.session() as session:
            outcome = HydroponicsAdvisorRuntimeService(
                session,
                model_executor=_Executor(factory),
                timeline_append=event_ref_factory,
                clock=lambda: now,
            ).invoke(_command(boss, plant))
        assert outcome.outcome_kind == "output_invalid"
        assert outcome.message_envelope is None


def test_unbound_timeout_invalid_output_and_audit_failure_are_closed_and_redacted(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _seed_context(ft009_database, farm, boss, plant, now=now)
    with ft009_database.session() as session:
        unbound = HydroponicsAdvisorRuntimeService(
            session,
            model_executor=None,
            timeline_append=event_ref_factory,
            clock=lambda: now,
        ).invoke(_command(boss, plant))
    assert unbound.outcome_kind == "runtime_not_configured"
    assert unbound.provider_call_status == "not_attempted"
    assert event_ref_factory.events == []

    with ft009_database.session() as session:
        failed = HydroponicsAdvisorRuntimeService(
            session,
            model_executor=_FailingExecutor(),
            timeline_append=event_ref_factory,
            clock=lambda: now,
        ).invoke(_command(boss, plant))
    assert failed.outcome_kind == "provider_failed"
    assert "never-persist" not in str(event_ref_factory.events[-1])

    invalid_executor = _Executor(
        lambda request: {**_measurement_request(request), "raw_response": "secret"}
    )
    with ft009_database.session() as session:
        invalid = HydroponicsAdvisorRuntimeService(
            session,
            model_executor=invalid_executor,
            timeline_append=event_ref_factory,
            clock=lambda: now,
        ).invoke(_command(boss, plant))
    assert invalid.outcome_kind == "output_invalid"
    assert "raw_response" not in str(event_ref_factory.events[-1])

    def failed_audit(_event):
        raise RuntimeError("audit secret should not escape")

    with ft009_database.session() as session:
        unaudited = HydroponicsAdvisorRuntimeService(
            session,
            model_executor=_Executor(_measurement_request),
            timeline_append=failed_audit,
            clock=lambda: now,
        ).invoke(_command(boss, plant))
    assert unaudited.outcome_kind == "audit_failed"
    assert unaudited.message_envelope is None
    assert unaudited.event_ref is None


def test_post_io_revoke_and_archive_deny_handoff_without_replay(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _seed_context(ft009_database, farm, boss, plant, now=now)
    engineer, membership = create_actor(ft009_database, farm, "engineer")
    grant_access(
        ft009_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    revoke_executor = _Executor(
        _measurement_request,
        before_return=lambda: revoke_access(
            ft009_database,
            boss,
            plant_id=plant.plant_id,
            membership_id=membership.membership_id,
        ),
    )
    with ft009_database.session() as session:
        revoked = HydroponicsAdvisorRuntimeService(
            session,
            model_executor=revoke_executor,
            timeline_append=event_ref_factory,
            clock=lambda: now,
        ).invoke(_command(engineer, plant))
    assert revoked.outcome_kind == "publication_guard_denied"
    assert revoked.message_envelope is None

    archive_executor = _Executor(
        _measurement_request,
        before_return=lambda: archive_plant(
            ft009_database,
            boss,
            plant_id=plant.plant_id,
        ),
    )
    with ft009_database.session() as session:
        archived = HydroponicsAdvisorRuntimeService(
            session,
            model_executor=archive_executor,
            timeline_append=event_ref_factory,
            clock=lambda: now,
        ).invoke(_command(boss, plant))
    assert archived.outcome_kind == "publication_guard_denied"
    assert archived.message_envelope is None
    assert len(archive_executor.requests) == 1
