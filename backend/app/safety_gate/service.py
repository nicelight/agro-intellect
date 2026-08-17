"""Provider-neutral Safety classifier with guarded immutable persistence."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Protocol
import uuid

from sqlalchemy.orm import Session

from ..agent_chat.contracts import UIFeedEventV1, timestamp_text
from ..agent_chat.models import UIFeedEvent
from ..agent_runtime.contracts import SafetyClassificationResultV1
from ..agent_runtime.service import DatabaseRuntimeAuthorizationGuard, ModelExecution
from ..core.redaction import redact_text
from .contracts import (
    SUPPORTED_PHYSICAL_ACTION_KINDS,
    UNSUPPORTED_PHYSICAL_ACTION_KINDS,
    SafetyActionDecisionCommandV1,
    SafetyActionDecisionOutcomeV1,
    SafetyClassificationOutcomeV1,
    SafetyGateClassificationCommandV1,
    SafetyGateMessageCandidateV1,
    SafetyGateModelCandidateV1,
    SafetyGateProviderRequestV1,
    SafetyGateValidationError,
    authoritative_classification,
    valid_model_ref,
)
from .models import SafetyActionDecision, SafetyClassification
from .repository import (
    CurrentGuardLockUnavailable,
    SafetyActionDecisionRepository,
    SafetyClassificationRepository,
)


_CURRENT_GUARD_LOCK_ATTEMPTS = 3  # Write-transaction attempts; never provider I/O.


class SafetyGateModelExecutor(Protocol):
    model_ref: str

    def execute(
        self,
        request: SafetyGateProviderRequestV1,
    ) -> ModelExecution | Mapping[str, object]: ...


class SafetyGateClassificationService:
    """Persist one project-owned result and perform no downstream dispatch."""

    def __init__(
        self,
        session: Session,
        *,
        model_executor: SafetyGateModelExecutor | None = None,
        authorization_guard: DatabaseRuntimeAuthorizationGuard | None = None,
        repository: SafetyClassificationRepository | None = None,
        clock=None,
        secret_values: Iterable[str] = (),
    ) -> None:
        self._session = session
        self._model_executor = model_executor
        self._clock = clock or _utc_now
        self._authorization_guard = authorization_guard or DatabaseRuntimeAuthorizationGuard(
            session,
            clock=self._clock,
        )
        self._repository = repository or SafetyClassificationRepository(session)
        self._secret_values = tuple(secret_values)

    def classify(
        self,
        command: SafetyGateClassificationCommandV1,
    ) -> SafetyClassificationOutcomeV1:
        if not isinstance(command, SafetyGateClassificationCommandV1):
            raise SafetyGateValidationError()
        envelope = command.message_envelope
        request = SafetyGateProviderRequestV1.from_envelope(envelope)
        try:
            request = _sanitized_request(
                request,
                secret_values=self._secret_values,
            )
        except (SafetyGateValidationError, ValueError):
            self._end_transaction()
            return _no_result(
                command,
                outcome_kind="guard_denied",
                error_code="SAFETY_CLASSIFICATION_GUARD_DENIED",
            )
        input_sha256 = _digest(envelope.as_value())

        scope = self._current_scope(command)
        if scope is None:
            self._end_transaction()
            return _no_result(
                command,
                outcome_kind="guard_denied",
                error_code="SAFETY_CLASSIFICATION_GUARD_DENIED",
            )
        try:
            existing = self._repository.get(envelope.message_id)
        except Exception:
            self._end_transaction()
            return _no_result(
                command,
                outcome_kind="persistence_failed",
                error_code="SAFETY_CLASSIFICATION_PERSISTENCE_FAILED",
            )
        self._end_transaction()
        if existing is not None:
            if existing.input_sha256 != input_sha256:
                return _conflict(command)
            return _authoritative_outcome(
                command,
                existing,
                outcome_kind="classification_idempotent",
                effect="evidence_duplicate",
                provider_call_status="not_attempted",
                error_code=None,
            )

        provider_status, model_ref, provider_call_status, raw_candidate = self._invoke(
            request
        )
        candidate: SafetyGateModelCandidateV1 | None = None
        error_code: str | None = None
        if provider_status == "completed":
            try:
                candidate = SafetyGateModelCandidateV1.from_untrusted(raw_candidate)
            except SafetyGateValidationError:
                provider_status = "invalid"
                error_code = "SAFETY_CLASSIFIER_OUTPUT_INVALID"
        elif provider_status == "not_configured":
            error_code = "SAFETY_CLASSIFIER_NOT_CONFIGURED"
        elif provider_status == "failed":
            error_code = "SAFETY_CLASSIFIER_PROVIDER_FAILED"

        result, physical_action_kind = authoritative_classification(
            message_id=envelope.message_id,
            candidate=candidate,
        )
        result_sha256 = _result_digest(
            result,
            physical_action_kind=physical_action_kind,
            provider_status=provider_status,
        )
        row = SafetyClassification(
            message_id=envelope.message_id,
            farm_id=envelope.farm_id,
            plant_id=envelope.plant_id,
            origin_agent_id=envelope.agent_id,
            classifier_version=result.classifier_version,
            classification=result.classification,
            safe_task_kind=result.safe_task_kind,
            reason_code=result.reason_code,
            physical_action_kind=physical_action_kind,
            provider_status=provider_status,
            model_ref=model_ref,
            input_sha256=input_sha256,
            result_sha256=result_sha256,
        )

        write = None
        for lock_attempt in range(_CURRENT_GUARD_LOCK_ATTEMPTS):
            try:
                with self._session.begin():
                    if self._current_scope(command) is None:
                        return _no_result(
                            command,
                            outcome_kind="guard_denied",
                            error_code="SAFETY_CLASSIFICATION_GUARD_DENIED",
                            provider_call_status=provider_call_status,
                        )
                    self._repository.lock_current_guard_rows(
                        command.actor_context,
                        plant_id=envelope.plant_id,
                    )
                    if self._current_scope(command) is None:
                        return _no_result(
                            command,
                            outcome_kind="guard_denied",
                            error_code="SAFETY_CLASSIFICATION_GUARD_DENIED",
                            provider_call_status=provider_call_status,
                        )
                    write = self._repository.persist_first(row)
                break
            except CurrentGuardLockUnavailable:
                if self._session.in_transaction():
                    self._session.rollback()
                if lock_attempt + 1 < _CURRENT_GUARD_LOCK_ATTEMPTS:
                    continue
            except Exception:
                if self._session.in_transaction():
                    self._session.rollback()
            return _no_result(
                command,
                outcome_kind="persistence_failed",
                error_code="SAFETY_CLASSIFICATION_PERSISTENCE_FAILED",
                provider_call_status=provider_call_status,
            )

        assert write is not None

        if write.status == "conflict":
            return _conflict(
                command,
                provider_status=provider_status,
                model_ref=model_ref,
                provider_call_status=provider_call_status,
            )
        return _authoritative_outcome(
            command,
            write.row,
            outcome_kind=(
                "classification_persisted"
                if write.status == "inserted"
                else "classification_idempotent"
            ),
            effect=(
                "evidence_written"
                if write.status == "inserted"
                else "evidence_duplicate"
            ),
            provider_call_status=provider_call_status,
            error_code=error_code if write.status == "inserted" else None,
        )

    def run(
        self,
        command: SafetyGateClassificationCommandV1,
    ) -> SafetyClassificationOutcomeV1:
        return self.classify(command)

    def _invoke(
        self,
        request: SafetyGateProviderRequestV1,
    ) -> tuple[str, str | None, str, object]:
        executor = self._model_executor
        model_ref = getattr(executor, "model_ref", None)
        if executor is None or not valid_model_ref(model_ref):
            return "not_configured", None, "not_attempted", None
        assert isinstance(model_ref, str)
        if self._session.in_transaction():
            raise RuntimeError("Provider I/O cannot run inside a database transaction.")
        try:
            execution = executor.execute(request)
        except Exception:
            return "failed", model_ref, "failed", None
        if isinstance(execution, ModelExecution):
            raw = execution.result if execution.model_ref == model_ref else None
        else:
            raw = execution if isinstance(execution, Mapping) else None
        return "completed", model_ref, "completed", raw

    def _current_scope(self, command: SafetyGateClassificationCommandV1):
        envelope = command.message_envelope
        try:
            scope = self._authorization_guard.current_scope(
                command.actor_context,
                plant_id=envelope.plant_id,
            )
        except Exception:
            return None
        if (
            scope is None
            or scope.farm_id != envelope.farm_id
            or scope.plant_id != envelope.plant_id
            or command.actor_context.farm_id != envelope.farm_id
        ):
            return None
        return scope

    def _end_transaction(self) -> None:
        if self._session.in_transaction():
            self._session.rollback()


class SafetyActionDecisionService:
    """Persist one terminal W2 decision and one inert projection atomically."""

    def __init__(
        self,
        session: Session,
        *,
        authorization_guard: DatabaseRuntimeAuthorizationGuard | None = None,
        repository: SafetyActionDecisionRepository | None = None,
        clock=None,
    ) -> None:
        self._session = session
        self._clock = clock or _utc_now
        self._authorization_guard = authorization_guard or DatabaseRuntimeAuthorizationGuard(
            session,
            clock=self._clock,
        )
        self._repository = repository or SafetyActionDecisionRepository(session)

    def evaluate(
        self,
        command: SafetyActionDecisionCommandV1,
    ) -> SafetyActionDecisionOutcomeV1:
        if not isinstance(command, SafetyActionDecisionCommandV1):
            raise SafetyGateValidationError()
        try:
            preliminary = self._repository.get_classification(
                command.classification_message_id
            )
        except Exception:
            self._end_transaction()
            return _no_decision(command, "persistence_failed", "SAFETY_DECISION_PERSISTENCE_FAILED")
        self._end_transaction()
        if preliminary is None:
            return _no_decision(command, "classification_ineligible", "SAFETY_DECISION_CLASSIFICATION_INELIGIBLE")

        for lock_attempt in range(_CURRENT_GUARD_LOCK_ATTEMPTS):
            try:
                with self._session.begin():
                    self._repository.lock_current_guard_rows(
                        command.actor_context,
                        plant_id=preliminary.plant_id,
                    )
                    scope = self._current_scope(
                        command,
                        farm_id=preliminary.farm_id,
                        plant_id=preliminary.plant_id,
                    )
                    if scope is None:
                        return _no_decision(command, "guard_denied", "SAFETY_DECISION_GUARD_DENIED")
                    classification = self._repository.get_classification(
                        command.classification_message_id,
                        for_update=True,
                    )
                    if not _eligible_classification(classification, preliminary):
                        return _no_decision(command, "classification_ineligible", "SAFETY_DECISION_CLASSIFICATION_INELIGIBLE")
                    assert classification is not None

                    existing = self._repository.get_decision(
                        classification.message_id,
                        for_update=True,
                    )
                    if existing is not None:
                        if existing.decision_id != command.decision_id:
                            return _no_decision(command, "decision_conflict", "SAFETY_DECISION_CONFLICT")
                        if (
                            existing.actor_account_id != command.actor_context.account_id
                            or existing.actor_membership_id
                            != command.actor_context.membership_id
                            or not self._projection_is_exact(existing)
                        ):
                            return _no_decision(command, "persistence_failed", "SAFETY_DECISION_PERSISTENCE_FAILED")
                        return _decision_outcome(existing, "decision_idempotent", "evidence_duplicate")

                    evaluated_at = _aware_utc(self._clock())
                    decision = self._build_decision(
                        command,
                        classification,
                        scope=scope,
                        evaluated_at=evaluated_at,
                    )
                    projection = _projection_row(decision)
                    write = self._repository.persist_first(decision, projection)
                    if write.status == "conflict":
                        return _no_decision(command, "decision_conflict", "SAFETY_DECISION_CONFLICT")
                    if write.status == "identical":
                        if not self._projection_is_exact(write.row):
                            return _no_decision(command, "persistence_failed", "SAFETY_DECISION_PERSISTENCE_FAILED")
                        return _decision_outcome(write.row, "decision_idempotent", "evidence_duplicate")
                return _decision_outcome(
                    decision,
                    "decision_persisted",
                    "decision_and_projection_written",
                )
            except CurrentGuardLockUnavailable:
                if self._session.in_transaction():
                    self._session.rollback()
                if lock_attempt + 1 < _CURRENT_GUARD_LOCK_ATTEMPTS:
                    continue
            except _EvidenceInvalid:
                if self._session.in_transaction():
                    self._session.rollback()
                return _no_decision(command, "evidence_invalid", "SAFETY_DECISION_EVIDENCE_INVALID")
            except Exception:
                if self._session.in_transaction():
                    self._session.rollback()
            return _no_decision(command, "persistence_failed", "SAFETY_DECISION_PERSISTENCE_FAILED")
        return _no_decision(command, "persistence_failed", "SAFETY_DECISION_PERSISTENCE_FAILED")

    def run(
        self,
        command: SafetyActionDecisionCommandV1,
    ) -> SafetyActionDecisionOutcomeV1:
        return self.evaluate(command)

    def _current_scope(self, command, *, farm_id, plant_id):
        try:
            scope = self._authorization_guard.current_scope(
                command.actor_context,
                plant_id=plant_id,
            )
        except Exception:
            return None
        if (
            scope is None
            or scope.farm_id != farm_id
            or scope.plant_id != plant_id
            or scope.role_preset != command.actor_context.role_preset.value
            or command.actor_context.farm_id != farm_id
        ):
            return None
        return scope

    def _build_decision(self, command, classification, *, scope, evaluated_at):
        action_kind = classification.physical_action_kind
        if action_kind in UNSUPPORTED_PHYSICAL_ACTION_KINDS:
            return _decision_row(
                command,
                classification,
                scope=scope,
                evaluated_at=evaluated_at,
                action_kind=action_kind,
                safety_status="safety_blocked",
                reason_code="unsupported_action",
                summary_text="Действие не поддерживается безопасным процессом MVP.",
            )
        if action_kind not in SUPPORTED_PHYSICAL_ACTION_KINDS:
            raise _EvidenceInvalid
        if not self._can_approve(command, scope=scope, plant_id=classification.plant_id):
            return _decision_row(
                command,
                classification,
                scope=scope,
                evaluated_at=evaluated_at,
                action_kind=action_kind,
                safety_status="safety_blocked",
                reason_code="approval_authority_missing",
                summary_text="Действие заблокировано: у текущего пользователя нет права подтверждения.",
            )

        ph = self._repository.latest_ph_measurement(
            farm_id=classification.farm_id,
            plant_id=classification.plant_id,
        )
        ec = self._repository.latest_ec_measurement(
            farm_id=classification.farm_id,
            plant_id=classification.plant_id,
        )
        _validate_measurement(ph, classification, field="ph")
        _validate_measurement(ec, classification, field="ec")
        ph_status = _freshness_status(ph, evaluated_at)
        ec_status = _freshness_status(ec, evaluated_at)
        evidence = {
            "ph_measurement_id": ph.measurement_id if ph is not None else None,
            "ec_measurement_id": ec.measurement_id if ec is not None else None,
            "ph_status": ph_status,
            "ec_status": ec_status,
            "ph_measured_at": _aware_utc(ph.measured_at) if ph is not None else None,
            "ec_measured_at": _aware_utc(ec.measured_at) if ec is not None else None,
        }
        if ph_status != "fresh" or ec_status != "fresh":
            return _decision_row(
                command,
                classification,
                scope=scope,
                evaluated_at=evaluated_at,
                action_kind=action_kind,
                safety_status="needs_fresh_evidence",
                reason_code="approval_input_missing_or_stale",
                summary_text="Перед предложением действия нужны свежие измерения pH и EC.",
                **evidence,
            )
        expires_at = min(
            evidence["ph_measured_at"] + timedelta(hours=2),
            evidence["ec_measured_at"] + timedelta(hours=2),
        )
        summaries = {
            "ph_adjustment": "Предложена ручная корректировка pH. Требуется решение уполномоченного пользователя.",
            "ec_adjustment": "Предложена ручная корректировка EC питательного раствора. Требуется решение уполномоченного пользователя.",
            "solution_change": "Предложена ручная замена питательного раствора. Требуется решение уполномоченного пользователя.",
        }
        return _decision_row(
            command,
            classification,
            scope=scope,
            evaluated_at=evaluated_at,
            action_kind=action_kind,
            safety_status="pending_human_approval",
            reason_code="ready_for_human_approval",
            summary_text=summaries[action_kind],
            expires_at=expires_at,
            **evidence,
        )

    def _can_approve(self, command, *, scope, plant_id) -> bool:
        if scope.role_preset == "boss":
            return scope.permission_source == "boss_role" and scope.grant_id is None
        if scope.role_preset != "engineer" or scope.permission_source != "plant_access_grant":
            return False
        grant = self._repository.current_grant(
            command.actor_context,
            plant_id=plant_id,
        )
        return (
            grant is not None
            and grant.grant_id == scope.grant_id
            and grant.status == "active"
            and grant.plant_approve_actions is True
        )

    def _projection_is_exact(self, decision: SafetyActionDecision) -> bool:
        projection = self._repository.get_projection(decision.decision_id)
        if projection is None:
            return False
        expected = _projection_value(decision)
        actual = _projection_model_value(projection)
        try:
            UIFeedEventV1.from_untrusted(actual)
        except Exception:
            return False
        return actual == expected

    def _end_transaction(self) -> None:
        if self._session.in_transaction():
            self._session.rollback()


class _EvidenceInvalid(RuntimeError):
    pass


def _authoritative_outcome(
    command: SafetyGateClassificationCommandV1,
    row: SafetyClassification,
    *,
    outcome_kind: str,
    effect: str,
    provider_call_status: str,
    error_code: str | None,
) -> SafetyClassificationOutcomeV1:
    result = SafetyClassificationResultV1.from_untrusted(
        {
            "schema_version": 1,
            "message_id": str(row.message_id),
            "classifier_version": row.classifier_version,
            "classification": row.classification,
            "safe_task_kind": row.safe_task_kind,
            "reason_code": row.reason_code,
        }
    )
    return SafetyClassificationOutcomeV1(
        classification_run_id=command.classification_run_id,
        outcome_kind=outcome_kind,
        authoritative=True,
        effect=effect,
        classification_result=result,
        physical_action_kind=row.physical_action_kind,
        provider_status=row.provider_status,
        model_ref=row.model_ref,
        provider_call_status=provider_call_status,
        error_code=error_code,
    )


def _conflict(
    command: SafetyGateClassificationCommandV1,
    *,
    provider_status: str | None = None,
    model_ref: str | None = None,
    provider_call_status: str = "not_attempted",
) -> SafetyClassificationOutcomeV1:
    result, _action_kind = authoritative_classification(
        message_id=command.message_envelope.message_id,
        candidate=None,
    )
    return SafetyClassificationOutcomeV1(
        classification_run_id=command.classification_run_id,
        outcome_kind="classification_conflict",
        authoritative=False,
        effect="no_effect",
        classification_result=result,
        physical_action_kind=None,
        provider_status=provider_status,
        model_ref=model_ref,
        provider_call_status=provider_call_status,
        error_code="SAFETY_CLASSIFICATION_CONFLICT",
    )


def _no_result(
    command: SafetyGateClassificationCommandV1,
    *,
    outcome_kind: str,
    error_code: str,
    provider_call_status: str = "not_attempted",
) -> SafetyClassificationOutcomeV1:
    return SafetyClassificationOutcomeV1(
        classification_run_id=command.classification_run_id,
        outcome_kind=outcome_kind,
        authoritative=False,
        effect="no_effect",
        classification_result=None,
        physical_action_kind=None,
        provider_status=None,
        model_ref=None,
        provider_call_status=provider_call_status,
        error_code=error_code,
    )


def _sanitized_request(
    request: SafetyGateProviderRequestV1,
    *,
    secret_values: tuple[str, ...],
) -> SafetyGateProviderRequestV1:
    """Return the outbound request copy with configured secret values removed.

    Only the outbound copy is sanitized; the service-side envelope and the
    persisted rows remain unchanged. A sanitizer failure fails closed at the
    caller before any provider I/O.
    """

    candidate = request.message_candidate
    output = redact_text(candidate.candidate_output, extra_secrets=secret_values)
    if output == candidate.candidate_output:
        return request
    return SafetyGateProviderRequestV1(
        agent_definition=request.agent_definition,
        message_candidate=SafetyGateMessageCandidateV1(
            message_id=candidate.message_id,
            origin_agent_id=candidate.origin_agent_id,
            runtime_decision=candidate.runtime_decision,
            candidate_claim_type=candidate.candidate_claim_type,
            candidate_output=output,
        ),
    )


def _digest(value: Mapping[str, object]) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(serialized).hexdigest()


def _result_digest(
    result: SafetyClassificationResultV1,
    *,
    physical_action_kind: str | None,
    provider_status: str,
) -> str:
    return _digest(
        {
            "classification_result": result.as_value(),
            "physical_action_kind": physical_action_kind,
            "provider_status": provider_status,
        }
    )


def _eligible_classification(
    row: SafetyClassification | None,
    preliminary: SafetyClassification,
) -> bool:
    return (
        isinstance(row, SafetyClassification)
        and row.message_id == preliminary.message_id
        and row.farm_id == preliminary.farm_id
        and row.plant_id == preliminary.plant_id
        and row.classification == "physical_action"
        and row.reason_code == "physical_action_detected"
        and row.physical_action_kind
        in SUPPORTED_PHYSICAL_ACTION_KINDS | UNSUPPORTED_PHYSICAL_ACTION_KINDS
        and row.origin_agent_id != "companion"
    )


def _decision_row(
    command: SafetyActionDecisionCommandV1,
    classification: SafetyClassification,
    *,
    scope,
    evaluated_at: datetime,
    action_kind: str,
    safety_status: str,
    reason_code: str,
    summary_text: str,
    ph_measurement_id=None,
    ec_measurement_id=None,
    ph_status=None,
    ec_status=None,
    ph_measured_at=None,
    ec_measured_at=None,
    expires_at=None,
) -> SafetyActionDecision:
    actor = command.actor_context
    return SafetyActionDecision(
        decision_id=command.decision_id,
        classification_message_id=classification.message_id,
        farm_id=classification.farm_id,
        plant_id=classification.plant_id,
        actor_account_id=actor.account_id,
        actor_membership_id=actor.membership_id,
        actor_role_preset=scope.role_preset,
        permission_source=scope.permission_source,
        grant_id=scope.grant_id,
        action_kind=action_kind,
        safety_status=safety_status,
        reason_code=reason_code,
        ph_measurement_id=ph_measurement_id,
        ec_measurement_id=ec_measurement_id,
        ph_status=ph_status,
        ec_status=ec_status,
        ph_measured_at=ph_measured_at,
        ec_measured_at=ec_measured_at,
        expires_at=expires_at,
        evaluated_at=evaluated_at,
        created_at=evaluated_at,
        summary_text=summary_text,
    )


def _validate_measurement(row, classification, *, field: str) -> None:
    if row is None:
        return
    value = row.ph if field == "ph" else row.ec_ms_cm
    if (
        row.farm_id != classification.farm_id
        or row.plant_id != classification.plant_id
        or value is None
        or not isinstance(row.measurement_id, uuid.UUID)
    ):
        raise _EvidenceInvalid
    _aware_utc(row.measured_at)


def _freshness_status(row, evaluated_at: datetime) -> str:
    if row is None:
        return "missing"
    measured_at = _aware_utc(row.measured_at)
    return (
        "fresh"
        if evaluated_at - timedelta(hours=2) <= measured_at <= evaluated_at
        else "stale"
    )


def _projection_value(decision: SafetyActionDecision) -> dict[str, object]:
    evidence_refs = list(
        dict.fromkeys(
            f"manual_measurement:{measurement_id}"
            for measurement_id in (
                decision.ph_measurement_id,
                decision.ec_measurement_id,
            )
            if measurement_id is not None
        )
    )
    freshness = None
    if decision.ph_status is not None and decision.ec_status is not None:
        freshness = {
            "purpose": "approval_input",
            "window_hours": 2,
            "computed_at": timestamp_text(decision.evaluated_at),
            "ph": _freshness_item(
                decision.ph_status,
                decision.ph_measurement_id,
                decision.ph_measured_at,
            ),
            "ec": _freshness_item(
                decision.ec_status,
                decision.ec_measurement_id,
                decision.ec_measured_at,
            ),
        }
    value = {
        "schema_version": 1,
        "ui_event_id": str(decision.decision_id),
        "created_at": timestamp_text(decision.created_at),
        "farm_id": str(decision.farm_id),
        "plant_id": str(decision.plant_id),
        "source_type": "safety",
        "source_id": str(decision.decision_id),
        "source_refs": [
            f"message_envelope:{decision.classification_message_id}",
            f"safety_classification:{decision.classification_message_id}",
            *evidence_refs,
        ],
        "display_kind": "safety_status",
        "display_payload": {
            "payload_kind": "safety_status",
            "decision_ref": f"safety_decision:{decision.decision_id}",
            "classification_ref": f"safety_classification:{decision.classification_message_id}",
            "action_kind": decision.action_kind,
            "safety_status": decision.safety_status,
            "reason_code": decision.reason_code,
            "summary_text": decision.summary_text,
            "evidence_refs": evidence_refs,
            "approval_input_freshness": freshness,
            "expires_at": timestamp_text(decision.expires_at)
            if decision.expires_at is not None
            else None,
        },
        "visible_to_roles": ["boss", "engineer"],
        "visible_to_agents": False,
        "consumable_by_agents": False,
    }
    return UIFeedEventV1.from_untrusted(value).as_value()


def _freshness_item(status, measurement_id, measured_at) -> dict[str, object]:
    return {
        "status": status,
        "source_ref": f"manual_measurement:{measurement_id}"
        if measurement_id is not None
        else None,
        "measured_at": timestamp_text(measured_at) if measured_at is not None else None,
    }


def _projection_row(decision: SafetyActionDecision) -> UIFeedEvent:
    value = _projection_value(decision)
    return UIFeedEvent(
        ui_event_id=decision.decision_id,
        farm_id=decision.farm_id,
        plant_id=decision.plant_id,
        created_at=decision.created_at,
        source_type="safety",
        source_id=str(decision.decision_id),
        source_refs=value["source_refs"],
        display_kind="safety_status",
        display_payload=value["display_payload"],
        visible_to_roles=["boss", "engineer"],
        visible_to_agents=False,
        consumable_by_agents=False,
        agent_id=None,
        roster_version=None,
    )


def _projection_model_value(row: UIFeedEvent) -> dict[str, object]:
    return {
        "schema_version": 1,
        "ui_event_id": str(row.ui_event_id),
        "created_at": timestamp_text(row.created_at),
        "farm_id": str(row.farm_id),
        "plant_id": str(row.plant_id),
        "source_type": row.source_type,
        "source_id": row.source_id,
        "source_refs": row.source_refs,
        "display_kind": row.display_kind,
        "display_payload": row.display_payload,
        "visible_to_roles": row.visible_to_roles,
        "visible_to_agents": row.visible_to_agents,
        "consumable_by_agents": row.consumable_by_agents,
    }


def _decision_outcome(
    decision: SafetyActionDecision,
    outcome_kind: str,
    effect: str,
) -> SafetyActionDecisionOutcomeV1:
    return SafetyActionDecisionOutcomeV1(
        decision_id=decision.decision_id,
        classification_message_id=decision.classification_message_id,
        outcome_kind=outcome_kind,
        authoritative=True,
        effect=effect,
        action_kind=decision.action_kind,
        safety_status=decision.safety_status,
        reason_code=decision.reason_code,
        expires_at=_aware_utc(decision.expires_at)
        if decision.expires_at is not None
        else None,
        error_code=None,
    )


def _no_decision(
    command: SafetyActionDecisionCommandV1,
    outcome_kind: str,
    error_code: str,
) -> SafetyActionDecisionOutcomeV1:
    return SafetyActionDecisionOutcomeV1(
        decision_id=None,
        classification_message_id=command.classification_message_id,
        outcome_kind=outcome_kind,
        authoritative=False,
        effect="no_effect",
        action_kind=None,
        safety_status=None,
        reason_code=None,
        expires_at=None,
        error_code=error_code,
    )


def _aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise _EvidenceInvalid
    normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    if normalized.utcoffset() is None:
        raise _EvidenceInvalid
    return normalized.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "SafetyActionDecisionService",
    "SafetyGateClassificationService",
    "SafetyGateModelExecutor",
]
