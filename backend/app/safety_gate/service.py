"""Provider-neutral Safety classifier with guarded immutable persistence."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Protocol

from sqlalchemy.orm import Session

from ..agent_runtime.contracts import SafetyClassificationResultV1
from ..agent_runtime.service import DatabaseRuntimeAuthorizationGuard, ModelExecution
from .contracts import (
    SafetyClassificationOutcomeV1,
    SafetyGateClassificationCommandV1,
    SafetyGateModelCandidateV1,
    SafetyGateProviderRequestV1,
    SafetyGateValidationError,
    authoritative_classification,
    valid_model_ref,
)
from .models import SafetyClassification
from .repository import SafetyClassificationRepository


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
    ) -> None:
        self._session = session
        self._model_executor = model_executor
        self._clock = clock or _utc_now
        self._authorization_guard = authorization_guard or DatabaseRuntimeAuthorizationGuard(
            session,
            clock=self._clock,
        )
        self._repository = repository or SafetyClassificationRepository(session)

    def classify(
        self,
        command: SafetyGateClassificationCommandV1,
    ) -> SafetyClassificationOutcomeV1:
        if not isinstance(command, SafetyGateClassificationCommandV1):
            raise SafetyGateValidationError()
        envelope = command.message_envelope
        request = SafetyGateProviderRequestV1.from_envelope(envelope)
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
        except Exception:
            if self._session.in_transaction():
                self._session.rollback()
            return _no_result(
                command,
                outcome_kind="persistence_failed",
                error_code="SAFETY_CLASSIFICATION_PERSISTENCE_FAILED",
                provider_call_status=provider_call_status,
            )

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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "SafetyGateClassificationService",
    "SafetyGateModelExecutor",
]
