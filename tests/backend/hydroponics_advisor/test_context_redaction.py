"""FT-015-AC-015: Hydroponics Advisor request context redaction.

Proves through the ACTUAL Advisor assembler and provider spy that the strict
HydroponicsAdvisorProviderRequestV1 contains only registered authorized
evidence and derived freshness data, that configured secret/auth corpus values
and forbidden context classes cannot reach the outbound request, that hostile
catalog values fail closed BEFORE provider I/O, and that missing-data policy,
freshness, refs, and unbound production remain unchanged.

The Advisor outbound free-text channels (DailyCheckIn.observation_text,
PlantStateRecord.observation_key) are sanitized with the shared `redact_text`
primitive (TASK-064) before provider I/O; only the outbound copy is sanitized
and persisted source values stay unchanged.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
import uuid

import pytest

from sqlalchemy import select

from backend.app.hydroponics_advisor import (
    DatabaseHydroponicsAdvisorInputAssembler,
    HydroponicsAdvisorCommandV1,
    HydroponicsAdvisorRuntimeService,
)
from backend.app.plant_operations.models import DailyCheckIn, ManualMeasurement
from backend.app.plant_state import PlantStateRecord
from tests.backend.plant_operations.conftest import create_actor

BARE_CORPUS = [
    "corpus-hydro-advisor-db-pw-7h2k",
    "corpus-hydro-advisor-bearer-5c3m",
    "corpus-hydro-advisor-cookie-8p1t",
    "corpus-hydro-advisor-session-3m6z",
]
CORPUS_TOKEN = "corpus-hydro-advisor-token-9x4f"
CORPUS_API_KEY = "corpus-hydro-advisor-api-key-2v8n"
FORBIDDEN_HEADERS = [
    "session=corpus-hydro-advisor-cookie-8p1t; HttpOnly",
    "Authorization: Bearer corpus-hydro-advisor-bearer-5c3m",
    "corpus-hydro-advisor-ui-feed-entry-4q1r",
    "corpus-hydro-advisor-provider-history-6t9c",
]

LEAK_TEXT = (
    f"dbpw={BARE_CORPUS[0]} bearer={BARE_CORPUS[1]} "
    f"cookieval={BARE_CORPUS[2]} sess={BARE_CORPUS[3]} "
    + " ".join(FORBIDDEN_HEADERS)
)
LEAK_KEY = FORBIDDEN_HEADERS[2]

ALL_SECRETS = tuple(
    BARE_CORPUS + FORBIDDEN_HEADERS + [CORPUS_TOKEN, CORPUS_API_KEY]
)


class _Executor:
    model_ref = "test_provider:advisor_v1"

    def __init__(self, *, kind="recommendation"):
        self.kind = kind
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        if self.kind == "measurement_request":
            return {
                "schema_version": 1,
                "runtime_decision": "speak",
                "advice_kind": "measurement_request",
                "candidate_output": None,
                "confidence": None,
                "requested_measurements": list(
                    request.analysis_freshness.missing_or_stale
                ),
                "source_refs": list(request.policy_source_refs()),
                "reason_code": "critical_measurements_required",
            }
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


def _command(actor, plant, *, goal="general_hydroponics_review"):
    return HydroponicsAdvisorCommandV1(
        run_id=uuid.uuid4(),
        requested_at=datetime.now(timezone.utc),
        actor_context=actor,
        plant_id=plant.plant_id,
        request_reason="manual_review",
        analysis_goal=goal,
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


def _seed(database, farm, actor, plant, *, now, state_source_refs=None,
          observation_text=LEAK_TEXT, observation_key=LEAK_KEY,
          with_measurement=True):
    with database.session() as session, session.begin():
        session.add(
            DailyCheckIn(
                check_in_id=uuid.uuid4(),
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                actor_account_id=actor.account_id,
                actor_membership_id=actor.membership_id,
                check_in_state="completed",
                observed_at=now - timedelta(hours=3),
                recorded_at=now - timedelta(hours=3),
                observation_state="observed",
                observation_text=observation_text,
                source_refs={},
                event_refs={},
                created_at=now - timedelta(hours=3),
            )
        )
        if with_measurement:
            session.add(
                _measurement_row(
                    farm,
                    actor,
                    plant,
                    measured_at=now - timedelta(hours=1),
                    ph=Decimal("6.50"),
                    ec=Decimal("1.250"),
                    now=now,
                )
            )
        else:
            session.add(
                _measurement_row(
                    farm,
                    actor,
                    plant,
                    measured_at=now - timedelta(hours=24, seconds=1),
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
                observation_key=observation_key,
                polarity="absent",
                severity="none",
                assessment_kind=None,
                direction=None,
                summary="No visible leaf spots.",
                confidence=Decimal("0.80000"),
                trust_status="observed",
                source_refs=state_source_refs or [f"photo:{uuid.uuid4()}"],
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


def _invoke(database, actor, plant, *, executor, timeline_append,
            goal="general_hydroponics_review"):
    with database.session() as session:
        return HydroponicsAdvisorRuntimeService(
            session,
            model_executor=executor,
            timeline_append=timeline_append,
            clock=lambda: datetime.now(timezone.utc).replace(microsecond=0),
            input_assembler=DatabaseHydroponicsAdvisorInputAssembler(
                session,
                secret_values=ALL_SECRETS,
            ),
        ).invoke(_command(actor, plant, goal=goal))


def test_request_contains_only_allowlist_and_excludes_corpus_with_source_unchanged(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    os.environ["AGRO_HYDRO_ADVISOR_CORPUS_TOKEN"] = CORPUS_TOKEN
    os.environ["AGRO_HYDRO_ADVISOR_CORPUS_API_KEY"] = CORPUS_API_KEY
    farm, boss, plant = ft009_seed
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _seed(ft009_database, farm, boss, plant, now=now)
    executor = _Executor()
    outcome = _invoke(
        ft009_database,
        boss,
        plant,
        executor=executor,
        timeline_append=event_ref_factory,
    )
    assert outcome.outcome_kind == "envelope_ready"
    assert outcome.message_envelope is not None
    assert outcome.message_envelope.publication_state == "pending_classification"
    assert outcome.message_envelope.consumable_by_agents is False
    assert len(executor.requests) == 1
    request = executor.requests[0]

    payload = request.as_provider_payload()
    payload_text = str(payload)
    for value in BARE_CORPUS + FORBIDDEN_HEADERS + [CORPUS_TOKEN, CORPUS_API_KEY]:
        assert value not in payload_text
        assert value not in repr(request)

    for attr_value in (
        str(boss.account_id),
        str(boss.session_id),
        str(boss.membership_id),
        str(boss.farm_id),
        boss.role_preset.value,
    ):
        assert attr_value not in payload_text

    assert set(payload) == {
        "schema_version",
        "agent_definition",
        "request_reason",
        "analysis_goal",
        "computed_at",
        "analysis_freshness",
        "records",
        "source_refs",
    }
    assert set(payload["agent_definition"]) == {
        "agent_id",
        "competence",
        "instructions",
        "allowed_decisions",
        "output_schema",
    }
    records = payload["records"]
    assert [record["record_type"] for record in records] == [
        "plant",
        "manual_measurement",
        "daily_checkin",
        "plant_state_record",
    ]
    assert set(records[0]["payload"]) == {"plant_id", "status"}
    assert set(records[1]["payload"]) == {
        "measurement_id",
        "measured_at",
        "recorded_at",
        "ph",
        "ec_ms_cm",
        "source_type",
        "trust_status",
    }
    assert set(records[2]["payload"]) == {
        "check_in_id",
        "observed_at",
        "recorded_at",
        "observation_state",
        "observation_text",
    }
    assert set(records[3]["payload"]) == {
        "state_record_id",
        "record_kind",
        "observation_key",
        "polarity",
        "severity",
        "assessment_kind",
        "direction",
        "trust_status",
        "observed_at",
        "recorded_at",
        "confidence",
        "source_refs",
    }
    assert "***" in records[2]["payload"]["observation_text"]
    assert "***" in records[3]["payload"]["observation_key"]
    freshness = payload["analysis_freshness"]
    assert freshness["window_hours"] == 24
    assert freshness["computed_at"] == payload["computed_at"]
    assert freshness["ph"]["status"] == "fresh"
    assert freshness["ec"]["status"] == "fresh"
    assert freshness["missing_or_stale"] == []
    assert freshness["ph"]["source_ref"] == records[1]["source_ref"]

    with ft009_database.session() as session:
        stored_check_in = session.scalar(
            select(DailyCheckIn).where(DailyCheckIn.plant_id == plant.plant_id)
        )
        stored_state = session.scalar(
            select(PlantStateRecord).where(PlantStateRecord.plant_id == plant.plant_id)
        )
    assert stored_check_in is not None
    assert stored_check_in.observation_text == LEAK_TEXT
    assert stored_state is not None
    assert stored_state.observation_key == LEAK_KEY


@pytest.mark.parametrize(
    "source_refs",
    [
        ["https://corpus-hydro-advisor.example/secret"],
        ["photo:not-a-uuid"],
    ],
)
def test_hostile_structured_values_fail_closed_before_provider_io(
    source_refs,
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _seed(
        ft009_database,
        farm,
        boss,
        plant,
        now=now,
        state_source_refs=source_refs,
    )
    executor = _Executor()
    outcome = _invoke(
        ft009_database,
        boss,
        plant,
        executor=executor,
        timeline_append=event_ref_factory,
    )
    assert outcome.outcome_kind == "context_denied"
    assert outcome.reason_code == "input_contract_violation"
    assert outcome.provider_call_status == "not_attempted"
    assert outcome.audit_status == "not_attempted"
    assert executor.requests == []
    assert event_ref_factory.events == []


def test_missing_data_policy_and_pending_handoff_regression(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _seed(
        ft009_database,
        farm,
        boss,
        plant,
        now=now,
        observation_text="Leaves inspected.",
        observation_key="leaf_spots",
        with_measurement=False,
    )
    executor = _Executor(kind="measurement_request")
    outcome = _invoke(
        ft009_database,
        boss,
        plant,
        executor=executor,
        timeline_append=event_ref_factory,
        goal="missing_data_review",
    )
    request = executor.requests[0]
    assert request.analysis_freshness.missing_or_stale == ("ph", "ec")
    assert request.analysis_freshness.ph.status == "missing"
    assert request.analysis_freshness.ec.status == "stale"
    assert outcome.outcome_kind == "envelope_ready"
    envelope = outcome.message_envelope
    assert envelope is not None
    assert envelope.candidate_claim_type == "task_request"
    assert envelope.candidate_output == (
        "Нужны свежие измерения pH и EC перед рекомендацией."
    )
    assert envelope.confidence == 1.0
    assert envelope.source_refs == request.policy_source_refs()
    assert envelope.publication_state == "pending_classification"
    assert envelope.consumable_by_agents is False
    assert request.policy_source_refs()[0] == f"plant:{plant.plant_id}"


def test_unbound_production_still_fails_closed_without_io(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _seed(ft009_database, farm, boss, plant, now=now)
    executor = _Executor()
    outcome = _invoke(
        ft009_database,
        boss,
        plant,
        executor=None,
        timeline_append=event_ref_factory,
    )
    assert outcome.outcome_kind == "runtime_not_configured"
    assert outcome.error_code == "AGENT_RUNTIME_NOT_CONFIGURED"
    assert outcome.provider_call_status == "not_attempted"
    assert outcome.audit_status == "not_attempted"
    assert executor.requests == []
    assert event_ref_factory.events == []
