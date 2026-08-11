"""Provider-neutral Dataset Agents advisory-only runtime (AD-011).

The Dataset Governance Agent assesses exactly one authorized candidate through
the registered ``dataset_advisory_v1`` route; it persists no Dataset field. The
Training Data Curator Agent runs the one explicit internal curator application
command over one candidate, persists only the current-run advisory allowlist
(or nothing for silence), and consumes a selected result through the
server-owned ``curator_auto`` gate in one atomic unit of work. Production
remains unbound and fails closed with no fake, canned, or fallback result.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Protocol
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..timeline import TimelineEvent, TimelineJsonlAppender
from .contracts import (
    CandidateTransition,
    ConfirmationSource,
    DatasetGovernanceError,
    DatasetGovernanceErrorCode,
    DatasetGovernanceValidationError,
    QualityTier,
    TransitionDatasetCandidateCommandV1,
)
from .models import DatasetCandidate
from .repository import CurrentDatasetScope, DatasetGovernanceRepository
from .runtime_contracts import (
    CURATOR_DECISIONS,
    DATASET_AGENT_AUDIT_FAILED,
    DATASET_AGENT_CONTEXT_DENIED,
    DATASET_AGENT_OUTPUT_INVALID,
    DATASET_AGENT_POST_IO_GUARD_DENIED,
    DATASET_AGENT_PROVIDER_FAILED,
    DATASET_AGENT_RUNTIME_NOT_CONFIGURED,
    DATASET_CONFIRMATION_POLICY_VIOLATION,
    DatasetAgentCommandV1,
    DatasetAgentRuntimeOutcomeV1,
    DatasetGovernanceAssessmentV1,
    DatasetGovernanceCandidateSnapshotV1,
    DatasetGovernancePolicyContextV1,
    DatasetGovernanceProviderRequestV1,
    DatasetGovernanceRuntimeValidationError,
    STRONG_EVIDENCE_POLICY_V1,
    TrainingDataCuratorDecisionV1,
    TrainingDataCuratorProviderRequestV1,
)
from .service import DatasetGovernanceService

_MODEL_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9._-]{1,127}\Z")


class DatasetGovernanceModelExecutor(Protocol):
    model_ref: str

    def execute(
        self,
        request: DatasetGovernanceProviderRequestV1,
    ) -> Mapping[str, object]: ...


class TrainingDataCuratorModelExecutor(Protocol):
    model_ref: str

    def execute(
        self,
        request: TrainingDataCuratorProviderRequestV1,
    ) -> Mapping[str, object]: ...


TimelineAppender = Callable[[TimelineEvent], Mapping[str, object]]
Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class _PreparedRun:
    request: DatasetGovernanceProviderRequestV1
    candidate_record_version: int
    candidate_ref: str


class DatasetGovernanceRuntimeService:
    """Runs one explicit internal Dataset Governance Agent attempt."""

    def __init__(
        self,
        session: Session,
        *,
        model_executor: DatasetGovernanceModelExecutor | None = None,
        repository: DatasetGovernanceRepository | None = None,
        timeline_append: TimelineAppender | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._session = session
        self._model_executor = model_executor
        self._repository = repository or DatasetGovernanceRepository(session)
        self._timeline_append = timeline_append or TimelineJsonlAppender()
        self._clock = clock or _utc_now

    def run(self, command: DatasetAgentCommandV1) -> DatasetAgentRuntimeOutcomeV1:
        if (
            not isinstance(command, DatasetAgentCommandV1)
            or command.agent_id != "dataset_governance"
        ):
            raise DatasetGovernanceValidationError()

        prepared = self._prepare(command)
        if isinstance(prepared, DatasetAgentRuntimeOutcomeV1):
            return prepared

        self._end_database_transaction()
        executor = self._model_executor
        model_ref = _executor_model_ref(executor)
        if executor is None or model_ref is None:
            return self._audit(
                command,
                prepared=prepared,
                model_ref=None,
                outcome_kind="runtime_not_configured",
                status="failed",
                reason_code="runtime_not_configured",
                error_code=DATASET_AGENT_RUNTIME_NOT_CONFIGURED,
                provider_call_status="not_attempted",
                validated_result=None,
            )

        try:
            execution = executor.execute(prepared.request)
        except Exception:
            return self._audit(
                command,
                prepared=prepared,
                model_ref=model_ref,
                outcome_kind="provider_failed",
                status="failed",
                reason_code="provider_failed",
                error_code=DATASET_AGENT_PROVIDER_FAILED,
                provider_call_status="failed",
                validated_result=None,
            )

        try:
            result = DatasetGovernanceAssessmentV1.from_untrusted(
                _execution_result(execution, expected_model_ref=model_ref),
                request=prepared.request,
            )
        except DatasetGovernanceRuntimeValidationError:
            return self._audit(
                command,
                prepared=prepared,
                model_ref=model_ref,
                outcome_kind="output_invalid",
                status="blocked",
                reason_code="output_invalid",
                error_code=DATASET_AGENT_OUTPUT_INVALID,
                provider_call_status="completed",
                validated_result=None,
            )

        self._end_database_transaction()
        try:
            self._post_io_guard(command, prepared)
        except _PostIoGuardDenied:
            return self._audit(
                command,
                prepared=prepared,
                model_ref=model_ref,
                outcome_kind="post_io_guard_denied",
                status="blocked",
                reason_code="post_io_guard_denied",
                error_code=DATASET_AGENT_POST_IO_GUARD_DENIED,
                provider_call_status="completed",
                validated_result=None,
            )
        self._end_database_transaction()

        return self._audit(
            command,
            prepared=prepared,
            model_ref=model_ref,
            outcome_kind="advisory_ready",
            status="advisory_ready",
            reason_code="advisory_ready",
            error_code=None,
            provider_call_status="completed",
            validated_result=result,
        )

    def invoke(self, command: DatasetAgentCommandV1) -> DatasetAgentRuntimeOutcomeV1:
        return self.run(command)

    def _prepare(
        self,
        command: DatasetAgentCommandV1,
    ) -> _PreparedRun | DatasetAgentRuntimeOutcomeV1:
        """Revalidate current authority and build the strict provider request."""
        try:
            scope = self._require_current_scope(command)
            candidate = self._require_candidate(command, scope)
        except _ContextDenied:
            return self._audit(
                command,
                prepared=None,
                model_ref=None,
                outcome_kind="context_denied",
                status="blocked",
                reason_code="context_denied",
                error_code=DATASET_AGENT_CONTEXT_DENIED,
                provider_call_status="not_attempted",
                validated_result=None,
            )
        try:
            request = DatasetGovernanceProviderRequestV1(
                run_id=command.run_id,
                requested_at=command.requested_at,
                plant_id=command.plant_id,
                candidate_id=candidate.candidate_id,
                candidate=_candidate_snapshot(candidate),
                policy_context=DatasetGovernancePolicyContextV1(
                    strong_evidence_policy=STRONG_EVIDENCE_POLICY_V1,
                    agent_labeled_guard=True,
                ),
            )
        except DatasetGovernanceRuntimeValidationError:
            return self._audit(
                command,
                prepared=None,
                model_ref=None,
                outcome_kind="context_denied",
                status="blocked",
                reason_code="context_denied",
                error_code=DATASET_AGENT_CONTEXT_DENIED,
                provider_call_status="not_attempted",
                validated_result=None,
            )
        return _PreparedRun(
            request=request,
            candidate_record_version=candidate.record_version,
            candidate_ref=f"dataset_candidate:{candidate.candidate_id}",
        )

    def _require_current_scope(
        self,
        command: DatasetAgentCommandV1,
    ) -> CurrentDatasetScope:
        scope = self._repository.current_scope(
            command.actor_context,
            plant_id=command.plant_id,
            for_update=False,
        )
        if scope is None or scope.plant_status != "active":
            raise _ContextDenied()
        return scope

    def _require_candidate(
        self,
        command: DatasetAgentCommandV1,
        scope: CurrentDatasetScope,
    ) -> DatasetCandidate:
        candidate = self._repository.candidate(
            command.candidate_id,
            for_update=False,
        )
        if (
            candidate is None
            or candidate.farm_id != scope.farm_id
            or candidate.plant_id != command.plant_id
        ):
            raise _ContextDenied()
        return candidate

    def _post_io_guard(
        self,
        command: DatasetAgentCommandV1,
        prepared: _PreparedRun,
    ) -> None:
        try:
            scope = self._require_current_scope(command)
            candidate = self._require_candidate(command, scope)
        except _ContextDenied:
            raise _PostIoGuardDenied() from None
        if candidate.record_version != prepared.candidate_record_version:
            raise _PostIoGuardDenied()

    def _audit(
        self,
        command: DatasetAgentCommandV1,
        *,
        prepared: _PreparedRun | None,
        model_ref: str | None,
        outcome_kind: str,
        status: str,
        reason_code: str,
        error_code: str | None,
        provider_call_status: str,
        validated_result: object | None,
    ) -> DatasetAgentRuntimeOutcomeV1:
        if prepared is None:
            candidate_refs: list[str] = []
            candidate_ref_count = 0
        else:
            candidate_refs = [prepared.candidate_ref]
            candidate_ref_count = 1
        event = _runtime_event(
            command=command,
            model_ref=model_ref,
            outcome_kind=outcome_kind,
            status=status,
            reason_code=reason_code,
            error_code=error_code,
            provider_call_status=provider_call_status,
            curator_gate_result="not_applicable",
            candidate_refs=candidate_refs,
            candidate_ref_count=candidate_ref_count,
        )
        try:
            event_ref = self._timeline_append(event)
            if not _event_ref_is_valid(event_ref):
                raise ValueError("Timeline append returned an invalid ref.")
        except Exception:
            return DatasetAgentRuntimeOutcomeV1(
                run_id=command.run_id,
                agent_id=command.agent_id,
                candidate_id=command.candidate_id,
                outcome_kind="audit_failed",
                status="failed",
                reason_code="audit_failed",
                error_code=DATASET_AGENT_AUDIT_FAILED,
                validated_result=None,
                event_ref=None,
                model_ref=model_ref,
                provider_call_status=provider_call_status,
                audit_status="failed",
                curator_gate_result="not_applicable",
            )
        return DatasetAgentRuntimeOutcomeV1(
            run_id=command.run_id,
            agent_id=command.agent_id,
            candidate_id=command.candidate_id,
            outcome_kind=outcome_kind,
            status=status,
            reason_code=reason_code,
            error_code=error_code,
            validated_result=validated_result,
            event_ref=dict(event_ref),
            model_ref=model_ref,
            provider_call_status=provider_call_status,
            audit_status="appended",
            curator_gate_result="not_applicable",
        )

    def _end_database_transaction(self) -> None:
        if self._session.in_transaction():
            self._session.rollback()


@dataclass(frozen=True, slots=True)
class _CuratorPreparedRun:
    request: TrainingDataCuratorProviderRequestV1
    candidate_record_version: int
    candidate_ref: str


class TrainingDataCuratorRuntimeService:
    """Runs one explicit internal Training Data Curator attempt (AD-011).

    This is the one explicit internal curator application command over one
    existing authorized candidate. Deferred/rejected results persist only the
    current-run advisory allowlist; silence persists nothing; a selected result
    is consumed atomically by the server-side ``curator_auto`` gate in the same
    PostgreSQL unit of work, and a policy/audit/guard failure rolls the advisory
    and lifecycle change back together.
    """

    def __init__(
        self,
        session: Session,
        *,
        model_executor: TrainingDataCuratorModelExecutor | None = None,
        repository: DatasetGovernanceRepository | None = None,
        timeline_append: TimelineAppender | None = None,
        clock: Clock | None = None,
        governance_service: DatasetGovernanceService | None = None,
    ) -> None:
        self._session = session
        self._model_executor = model_executor
        self._repository = repository or DatasetGovernanceRepository(session)
        self._timeline_append = timeline_append or TimelineJsonlAppender()
        self._clock = clock or _utc_now
        self._governance = governance_service or DatasetGovernanceService(
            session,
            timeline_appender=self._timeline_append,
            repository=self._repository,
            clock=self._clock,
        )

    def run(self, command: DatasetAgentCommandV1) -> DatasetAgentRuntimeOutcomeV1:
        if (
            not isinstance(command, DatasetAgentCommandV1)
            or command.agent_id != "training_data_curator"
        ):
            raise DatasetGovernanceValidationError()

        prepared = self._prepare(command)
        if isinstance(prepared, DatasetAgentRuntimeOutcomeV1):
            return prepared

        self._end_database_transaction()
        executor = self._model_executor
        model_ref = _executor_model_ref(executor)
        if executor is None or model_ref is None:
            return self._audit(
                command,
                prepared=prepared,
                model_ref=None,
                outcome_kind="runtime_not_configured",
                status="failed",
                reason_code="runtime_not_configured",
                error_code=DATASET_AGENT_RUNTIME_NOT_CONFIGURED,
                provider_call_status="not_attempted",
                validated_result=None,
                curator_gate_result="not_applicable",
                advisory_persisted=False,
                lifecycle_changed=False,
            )

        try:
            execution = executor.execute(prepared.request)
        except Exception:
            return self._audit(
                command,
                prepared=prepared,
                model_ref=model_ref,
                outcome_kind="provider_failed",
                status="failed",
                reason_code="provider_failed",
                error_code=DATASET_AGENT_PROVIDER_FAILED,
                provider_call_status="failed",
                validated_result=None,
                curator_gate_result="not_applicable",
                advisory_persisted=False,
                lifecycle_changed=False,
            )

        try:
            result = TrainingDataCuratorDecisionV1.from_untrusted(
                _execution_result(execution, expected_model_ref=model_ref),
                request=prepared.request,
            )
        except DatasetGovernanceRuntimeValidationError:
            return self._audit(
                command,
                prepared=prepared,
                model_ref=model_ref,
                outcome_kind="output_invalid",
                status="blocked",
                reason_code="output_invalid",
                error_code=DATASET_AGENT_OUTPUT_INVALID,
                provider_call_status="completed",
                validated_result=None,
                curator_gate_result="not_applicable",
                advisory_persisted=False,
                lifecycle_changed=False,
            )

        self._end_database_transaction()
        try:
            candidate = self._post_io_guard(command, prepared)
        except _PostIoGuardDenied:
            return self._audit(
                command,
                prepared=prepared,
                model_ref=model_ref,
                outcome_kind="post_io_guard_denied",
                status="blocked",
                reason_code="post_io_guard_denied",
                error_code=DATASET_AGENT_POST_IO_GUARD_DENIED,
                provider_call_status="completed",
                validated_result=None,
                curator_gate_result="not_applicable",
                advisory_persisted=False,
                lifecycle_changed=False,
            )

        if result.curator_decision == "silent":
            return self._audit(
                command,
                prepared=prepared,
                model_ref=model_ref,
                outcome_kind="model_silent",
                status="silent",
                reason_code="model_silent",
                error_code=None,
                provider_call_status="completed",
                validated_result=result,
                curator_gate_result="not_requested",
                advisory_persisted=False,
                lifecycle_changed=False,
            )

        try:
            self._persist_advisory(command, candidate, result)
            if result.curator_decision == "selected":
                self._apply_curator_gate(command, candidate)
            selected = result.curator_decision == "selected"
        except DatasetGovernanceError as governance_error:
            self._end_database_transaction()
            if governance_error.code is DatasetGovernanceErrorCode.AUDIT_FAILED:
                return DatasetAgentRuntimeOutcomeV1(
                    run_id=command.run_id,
                    agent_id=command.agent_id,
                    candidate_id=command.candidate_id,
                    outcome_kind="audit_failed",
                    status="failed",
                    reason_code="audit_failed",
                    error_code=DATASET_AGENT_AUDIT_FAILED,
                    validated_result=None,
                    event_ref=None,
                    model_ref=model_ref,
                    provider_call_status="completed",
                    audit_status="failed",
                    curator_gate_result="not_applicable",
                )
            if governance_error.code is DatasetGovernanceErrorCode.CONTEXT_FORBIDDEN:
                return self._audit(
                    command,
                    prepared=prepared,
                    model_ref=model_ref,
                    outcome_kind="post_io_guard_denied",
                    status="blocked",
                    reason_code="post_io_guard_denied",
                    error_code=DATASET_AGENT_POST_IO_GUARD_DENIED,
                    provider_call_status="completed",
                    validated_result=None,
                    curator_gate_result="not_applicable",
                    advisory_persisted=False,
                    lifecycle_changed=False,
                )
            return self._audit(
                command,
                prepared=prepared,
                model_ref=model_ref,
                outcome_kind="policy_blocked",
                status="blocked",
                reason_code="policy_blocked",
                error_code=DATASET_CONFIRMATION_POLICY_VIOLATION,
                provider_call_status="completed",
                validated_result=None,
                curator_gate_result="policy_blocked",
                advisory_persisted=False,
                lifecycle_changed=False,
            )
        except (SQLAlchemyError, TypeError, ValueError):
            self._end_database_transaction()
            return self._audit(
                command,
                prepared=prepared,
                model_ref=model_ref,
                outcome_kind="policy_blocked",
                status="blocked",
                reason_code="policy_blocked",
                error_code=DATASET_CONFIRMATION_POLICY_VIOLATION,
                provider_call_status="completed",
                validated_result=None,
                curator_gate_result="policy_blocked",
                advisory_persisted=False,
                lifecycle_changed=False,
            )

        return self._audit(
            command,
            prepared=prepared,
            model_ref=model_ref,
            outcome_kind="advisory_ready",
            status="advisory_ready",
            reason_code="advisory_ready",
            error_code=None,
            provider_call_status="completed",
            validated_result=result,
            curator_gate_result="confirmed" if selected else "not_requested",
            advisory_persisted=True,
            lifecycle_changed=selected,
        )

    def invoke(self, command: DatasetAgentCommandV1) -> DatasetAgentRuntimeOutcomeV1:
        return self.run(command)

    def _prepare(
        self,
        command: DatasetAgentCommandV1,
    ) -> _CuratorPreparedRun | DatasetAgentRuntimeOutcomeV1:
        """Revalidate current authority and build the strict curator request."""
        try:
            scope = self._require_current_scope(command, for_update=False)
            candidate = self._require_candidate(command, scope, for_update=False)
        except _ContextDenied:
            return self._audit(
                command,
                prepared=None,
                model_ref=None,
                outcome_kind="context_denied",
                status="blocked",
                reason_code="context_denied",
                error_code=DATASET_AGENT_CONTEXT_DENIED,
                provider_call_status="not_attempted",
                validated_result=None,
                curator_gate_result="not_applicable",
                advisory_persisted=False,
                lifecycle_changed=False,
            )
        try:
            request = TrainingDataCuratorProviderRequestV1(
                run_id=command.run_id,
                requested_at=command.requested_at,
                plant_id=command.plant_id,
                candidate_id=candidate.candidate_id,
                candidate=_candidate_snapshot(candidate),
                policy_context=DatasetGovernancePolicyContextV1(
                    strong_evidence_policy=STRONG_EVIDENCE_POLICY_V1,
                    agent_labeled_guard=True,
                ),
            )
        except DatasetGovernanceRuntimeValidationError:
            return self._audit(
                command,
                prepared=None,
                model_ref=None,
                outcome_kind="context_denied",
                status="blocked",
                reason_code="context_denied",
                error_code=DATASET_AGENT_CONTEXT_DENIED,
                provider_call_status="not_attempted",
                validated_result=None,
                curator_gate_result="not_applicable",
                advisory_persisted=False,
                lifecycle_changed=False,
            )
        return _CuratorPreparedRun(
            request=request,
            candidate_record_version=candidate.record_version,
            candidate_ref=f"dataset_candidate:{candidate.candidate_id}",
        )

    def _require_current_scope(
        self,
        command: DatasetAgentCommandV1,
        *,
        for_update: bool,
    ) -> CurrentDatasetScope:
        scope = self._repository.current_scope(
            command.actor_context,
            plant_id=command.plant_id,
            for_update=for_update,
        )
        if scope is None or scope.plant_status != "active":
            raise _ContextDenied()
        return scope

    def _require_candidate(
        self,
        command: DatasetAgentCommandV1,
        scope: CurrentDatasetScope,
        *,
        for_update: bool,
    ) -> DatasetCandidate:
        candidate = self._repository.candidate(
            command.candidate_id,
            for_update=for_update,
        )
        if (
            candidate is None
            or candidate.farm_id != scope.farm_id
            or candidate.plant_id != command.plant_id
        ):
            raise _ContextDenied()
        return candidate

    def _post_io_guard(
        self,
        command: DatasetAgentCommandV1,
        prepared: _CuratorPreparedRun,
    ) -> DatasetCandidate:
        """Re-lock current authority/Plant and the candidate after provider I/O.

        Uses ``FOR UPDATE`` locks, revalidates the exact candidate version, and
        rejects a candidate that already persists a curator run (stale/
        duplicate-run) before any advisory or gate write.
        """
        try:
            scope = self._require_current_scope(command, for_update=True)
            candidate = self._require_candidate(command, scope, for_update=True)
        except _ContextDenied:
            raise _PostIoGuardDenied() from None
        if candidate.record_version != prepared.candidate_record_version:
            raise _PostIoGuardDenied()
        if candidate.curator_run_id is not None:
            raise _PostIoGuardDenied()
        return candidate

    def _persist_advisory(
        self,
        command: DatasetAgentCommandV1,
        candidate: DatasetCandidate,
        result: TrainingDataCuratorDecisionV1,
    ) -> None:
        """Persist only the exact current-run advisory allowlist and its
        all-or-none run identity; never lifecycle/quality/split/confirmation/
        evidence/trainability fields."""
        now = self._clock()
        candidate.curator_decision = result.curator_decision
        candidate.curator_notes_ref = result.curator_notes_ref
        candidate.curator_run_id = command.run_id
        candidate.curator_command_sha256 = command.command_sha256
        candidate.curator_recorded_at = now
        candidate.record_version += 1
        candidate.updated_at = now
        self._session.flush()

    def _apply_curator_gate(self, command: DatasetAgentCommandV1, candidate: DatasetCandidate) -> None:
        """Consume a selected run through the server-owned transition authority.

        The advisory write has already flushed, so ``candidate.record_version``
        is the post-advisory value. The transition re-locks the candidate and
        revalidates the strong-evidence policy and exact run identity; a policy
        failure raises and the runtime rolls the whole unit of work back.
        """
        transition = TransitionDatasetCandidateCommandV1(
            actor_context=command.actor_context,
            candidate_id=command.candidate_id,
            transition=CandidateTransition.CONFIRM,
            expected_status=candidate.candidate_status,
            expected_record_version=candidate.record_version,
            confirmation_source=ConfirmationSource.CURATOR_AUTO,
            quality_tier=QualityTier.STANDARD,
            curator_run_id=command.run_id,
            curator_command_sha256=command.command_sha256,
        )
        self._governance.transition_candidate(transition)

    def _audit(
        self,
        command: DatasetAgentCommandV1,
        *,
        prepared: _CuratorPreparedRun | None,
        model_ref: str | None,
        outcome_kind: str,
        status: str,
        reason_code: str,
        error_code: str | None,
        provider_call_status: str,
        validated_result: object | None,
        curator_gate_result: str,
        advisory_persisted: bool,
        lifecycle_changed: bool,
    ) -> DatasetAgentRuntimeOutcomeV1:
        if prepared is None:
            candidate_refs: list[str] = []
            candidate_ref_count = 0
        else:
            candidate_refs = [prepared.candidate_ref]
            candidate_ref_count = 1
        event = _runtime_event(
            command=command,
            model_ref=model_ref,
            outcome_kind=outcome_kind,
            status=status,
            reason_code=reason_code,
            error_code=error_code,
            provider_call_status=provider_call_status,
            curator_gate_result=curator_gate_result,
            candidate_refs=candidate_refs,
            candidate_ref_count=candidate_ref_count,
            advisory_persisted=advisory_persisted,
            lifecycle_changed=lifecycle_changed,
        )
        try:
            event_ref = self._timeline_append(event)
            if not _event_ref_is_valid(event_ref):
                raise ValueError("Timeline append returned an invalid ref.")
        except Exception:
            self._end_database_transaction()
            return DatasetAgentRuntimeOutcomeV1(
                run_id=command.run_id,
                agent_id=command.agent_id,
                candidate_id=command.candidate_id,
                outcome_kind="audit_failed",
                status="failed",
                reason_code="audit_failed",
                error_code=DATASET_AGENT_AUDIT_FAILED,
                validated_result=None,
                event_ref=None,
                model_ref=model_ref,
                provider_call_status=provider_call_status,
                audit_status="failed",
                curator_gate_result=curator_gate_result,
            )
        return DatasetAgentRuntimeOutcomeV1(
            run_id=command.run_id,
            agent_id=command.agent_id,
            candidate_id=command.candidate_id,
            outcome_kind=outcome_kind,
            status=status,
            reason_code=reason_code,
            error_code=error_code,
            validated_result=validated_result,
            event_ref=dict(event_ref),
            model_ref=model_ref,
            provider_call_status=provider_call_status,
            audit_status="appended",
            curator_gate_result=curator_gate_result,
        )

    def _end_database_transaction(self) -> None:
        if self._session.in_transaction():
            self._session.rollback()


class _ContextDenied(RuntimeError):
    pass


class _PostIoGuardDenied(RuntimeError):
    pass


def _candidate_snapshot(candidate: DatasetCandidate) -> DatasetGovernanceCandidateSnapshotV1:
    kinds = tuple(sorted({str(item.get("kind")) for item in candidate.evidence_refs}))
    return DatasetGovernanceCandidateSnapshotV1(
        candidate_status=candidate.candidate_status,
        candidate_origin=candidate.candidate_origin,
        quality_tier=candidate.quality_tier,
        follow_up_seen=candidate.follow_up_seen,
        corrected=candidate.corrected,
        evidence_ref_count=len(candidate.evidence_refs),
        evidence_kinds=kinds,
    )


def _runtime_event(
    *,
    command: DatasetAgentCommandV1,
    model_ref: str | None,
    outcome_kind: str,
    status: str,
    reason_code: str,
    error_code: str | None,
    provider_call_status: str,
    curator_gate_result: str,
    candidate_refs: list[str],
    candidate_ref_count: int,
    advisory_persisted: bool = False,
    lifecycle_changed: bool = False,
) -> TimelineEvent:
    return TimelineEvent(
        farm_id=command.actor_context.farm_id,
        plant_id=command.plant_id,
        actor_ref={
            "account_id": str(command.actor_context.account_id),
            "membership_id": str(command.actor_context.membership_id),
            "role_preset": command.actor_context.role_preset.value,
        },
        event_type="dataset_agent_runtime_decided",
        source_type="dataset_agent_attempt",
        source_id=command.run_id,
        source_refs={"candidate_refs": candidate_refs},
        payload_summary={
            "agent_id": command.agent_id,
            "model_ref": model_ref,
            "outcome_kind": outcome_kind,
            "status": status,
            "reason_code": reason_code,
            "error_code": error_code,
            "provider_call_status": provider_call_status,
            "curator_gate_result": curator_gate_result,
            "candidate_ref_count": candidate_ref_count,
            "advisory_persisted": advisory_persisted,
            "lifecycle_changed": lifecycle_changed,
        },
    )


def _executor_model_ref(executor: DatasetGovernanceModelExecutor | None) -> str | None:
    if executor is None:
        return None
    value = getattr(executor, "model_ref", None)
    return value if isinstance(value, str) and _MODEL_REF_RE.fullmatch(value) else None


def _execution_result(execution: object, *, expected_model_ref: str) -> object:
    if isinstance(execution, Mapping):
        return execution
    if isinstance(execution, tuple) and len(execution) == 2:
        model_ref, result = execution
        if model_ref == expected_model_ref and isinstance(result, Mapping):
            return result
    return None


def _event_ref_is_valid(value: object) -> bool:
    if (
        not isinstance(value, Mapping)
        or set(value)
        != {"timeline_event_id", "timeline_ref", "event_type", "created_at"}
        or value.get("event_type") != "dataset_agent_runtime_decided"
    ):
        return False
    try:
        uuid.UUID(str(value.get("timeline_event_id")))
    except (TypeError, ValueError):
        return False
    return (
        isinstance(value.get("timeline_ref"), str)
        and str(value.get("timeline_ref")).startswith("timeline.jsonl#")
        and isinstance(value.get("created_at"), str)
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "DatasetGovernanceModelExecutor",
    "DatasetGovernanceRuntimeService",
    "TimelineAppender",
    "TrainingDataCuratorModelExecutor",
    "TrainingDataCuratorRuntimeService",
]
