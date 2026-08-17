"""FT-015-AC-014: Plant State request context redaction.

Proves through the ACTUAL Plant State assembler and provider spy that the
strict PlantStateProviderRequestV1 contains only registered authorized
Plant-state records, that configured secret/auth corpus values and forbidden
context classes cannot enter the outbound request, that hostile catalog row
values fail closed BEFORE provider I/O, and that unbound production still
fails closed.

Plant State has no free-text channel into the outbound request: every value is
a fixed constant, a canonical UUID, a closed-set member, or a UTC RFC 3339
timestamp, and the strict PlantStateInputRecordV1/PlantStateProviderRequestV1
allowlists reject hostile row values. Non-allowlisted DB columns (summary,
confirmation_source, confirmed_by_*, agent_id, run_id, message_id, record_kind,
version, created_at, updated_at) are never copied outbound.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
import uuid

import pytest

from backend.app.agent_runtime import ModelExecution
from backend.app.plant_state import (
    PlantStateCommand,
    PlantStateRecord,
    PlantStateRuntimeService,
)
from tests.backend.plant_operations.conftest import create_actor

BARE_CORPUS = [
    "corpus-plantstate-db-pw-7h2k",
    "corpus-plantstate-bearer-5c3m",
    "corpus-plantstate-cookie-8p1t",
    "corpus-plantstate-session-3m6z",
]
CORPUS_TOKEN = "corpus-plantstate-token-9x4f"
CORPUS_API_KEY = "corpus-plantstate-api-key-2v8n"
FORBIDDEN_HEADERS = [
    "session=corpus-plantstate-cookie-8p1t; HttpOnly",
    "Authorization: Bearer corpus-plantstate-bearer-5c3m",
    "corpus-plantstate-ui-feed-entry-4q1r",
    "corpus-plantstate-provider-history-6t9c",
]

LEAK_SUMMARY = (
    f"dbpw={BARE_CORPUS[0]} bearer={BARE_CORPUS[1]} "
    f"cookieval={BARE_CORPUS[2]} sess={BARE_CORPUS[3]} "
    + " ".join(FORBIDDEN_HEADERS)
)


class _Executor:
    model_ref = "test_provider:model_1"

    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return ModelExecution(
            model_ref=self.model_ref,
            result={
                "schema_version": 1,
                "runtime_decision": "speak",
                "assessment_kind": "conflict",
                "observation_key": "leaf_spots",
                "direction": "not_applicable",
                "summary": "Present and absent evidence remains contradictory.",
                "confidence": 0.8,
                "source_refs": list(request.source_refs),
                "reason_code": None,
            },
        )


def _command(actor, plant):
    return PlantStateCommand(
        run_id=uuid.uuid4(),
        requested_at=datetime.now(timezone.utc),
        actor_context=actor,
        plant_id=plant.plant_id,
    )


def _seed(database, farm, plant, *, summary, count=2, observation_key="leaf_spots",
          source_refs=None):
    now = datetime.now(timezone.utc)
    rows = []
    with database.session() as session, session.begin():
        for index in range(count):
            polarity = "present" if index % 2 == 0 else "absent"
            severity = "mild" if index % 2 == 0 else "none"
            row = PlantStateRecord(
                state_record_id=uuid.uuid4(),
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                record_kind="vision_observation",
                agent_id="vision_observation",
                run_id=uuid.uuid4(),
                message_id=uuid.uuid4(),
                observation_key=observation_key,
                polarity=polarity,
                severity=severity,
                assessment_kind=None,
                direction=None,
                summary=summary,
                confidence=Decimal("0.75000"),
                trust_status="observed",
                source_refs=source_refs or [f"photo:{uuid.uuid4()}"],
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


def _invoke(database, actor, plant, *, executor, timeline_append):
    with database.session() as session:
        return PlantStateRuntimeService(
            session,
            model_executor=executor,
            timeline_append=timeline_append,
        ).invoke(_command(actor, plant))


def test_request_carries_only_allowlist_and_exact_refs_with_source_unchanged(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    os.environ["AGRO_PLANTSTATE_CORPUS_TOKEN"] = CORPUS_TOKEN
    os.environ["AGRO_PLANTSTATE_CORPUS_API_KEY"] = CORPUS_API_KEY
    farm, boss, plant = ft009_seed
    rows = _seed(ft009_database, farm, plant, summary=LEAK_SUMMARY)
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
    assert outcome.state_candidate is not None
    assert outcome.state_candidate.assessment_kind == "conflict"
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

    expected_payload = {"schema_version", "agent_definition", "records", "source_refs"}
    assert set(payload) == expected_payload
    assert set(payload["agent_definition"]) == {
        "agent_id",
        "competence",
        "instructions",
        "allowed_decisions",
        "output_schema",
    }
    records = payload["records"]
    assert [record["record_type"] for record in records] == [
        "plant_state_record",
        "plant_state_record",
    ]
    assert set(records[0]["payload"]) == {
        "state_record_id",
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
    assert "summary" not in payload_text
    assert request.source_refs == tuple(
        f"plant_state_record:{item.state_record_id}" for item in rows
    )

    from sqlalchemy import select

    with ft009_database.session() as session:
        stored = list(
            session.scalars(
                select(PlantStateRecord).where(PlantStateRecord.plant_id == plant.plant_id)
            )
        )
        assert all(item.summary == LEAK_SUMMARY for item in stored)


@pytest.mark.parametrize(
    ("field", "hostile"),
    [
        ("observation_key", "corpus-plantstate-hostile-obs-key"),
        ("source_refs", [f"session:{uuid.uuid4()}"]),
        ("source_refs", ["https://corpus-plantstate.example/secret"]),
    ],
)
def test_hostile_row_values_fail_closed_before_provider_io(
    field,
    hostile,
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    kwargs = {field: hostile}
    _seed(ft009_database, farm, plant, summary="safe", **kwargs)
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


def test_unbound_production_still_fails_closed_without_io(
    ft009_database,
    ft009_seed,
    event_ref_factory,
):
    farm, boss, plant = ft009_seed
    _seed(ft009_database, farm, plant, summary="safe")
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
