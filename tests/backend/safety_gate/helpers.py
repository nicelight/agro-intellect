from __future__ import annotations

from datetime import datetime, timezone
import uuid

from backend.app.agent_runtime import (
    CurrentAuthorizationScope,
    MessageEnvelopeV1,
    ModelExecution,
    RuntimeDecision,
)
from backend.app.safety_gate import SafetyGateClassificationCommandV1


class RecordingExecutor:
    model_ref = "test_provider:safety_v1"

    def __init__(self, result, *, before_return=None, transaction_probe=None):
        self.result = result
        self.before_return = before_return
        self.transaction_probe = transaction_probe
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        if self.transaction_probe is not None:
            self.transaction_probe()
        if self.before_return is not None:
            self.before_return()
        result = self.result(request) if callable(self.result) else self.result
        return ModelExecution(model_ref=self.model_ref, result=result)


class FailingExecutor:
    model_ref = "test_provider:safety_v1"

    def __init__(self, *, before_raise=None):
        self.before_raise = before_raise
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        if self.before_raise is not None:
            self.before_raise()
        raise TimeoutError("synthetic provider failure credential=must-not-leak")


def envelope_for(
    actor,
    plant,
    *,
    message_id=None,
    candidate_output="Добавьте питательный раствор вручную.",
    agent_id="hydroponics_advisor",
    candidate_claim_type="recommendation",
    grant_id=None,
):
    source = "boss_role" if actor.role_preset.value == "boss" else "plant_access_grant"
    scope = CurrentAuthorizationScope(
        farm_id=actor.farm_id,
        plant_id=plant.plant_id,
        role_preset=actor.role_preset.value,
        operation_kind="normal_read",
        permission_source=source,
        grant_id=None if source == "boss_role" else grant_id,
    )
    return MessageEnvelopeV1(
        message_id=message_id or uuid.uuid4(),
        run_id=uuid.uuid4(),
        agent_id=agent_id,
        created_at=datetime.now(timezone.utc),
        farm_id=actor.farm_id,
        plant_id=plant.plant_id,
        runtime_decision=RuntimeDecision.SPEAK,
        candidate_claim_type=candidate_claim_type,
        confidence=0.75,
        source_refs=(f"plant:{plant.plant_id}",),
        candidate_output=candidate_output,
        authorization_scope=scope,
    )


def command_for(actor, envelope):
    return SafetyGateClassificationCommandV1(
        classification_run_id=uuid.uuid4(),
        requested_at=datetime.now(timezone.utc),
        actor_context=actor,
        message_envelope=envelope,
    )


def candidate(
    classification="physical_action",
    *,
    task_kind=None,
    action_kind="ec_adjustment",
):
    if classification != "physical_action":
        action_kind = None
    return {
        "schema_version": 1,
        "candidate_classification": classification,
        "safe_task_kind": task_kind,
        "physical_action_kind": action_kind,
    }
