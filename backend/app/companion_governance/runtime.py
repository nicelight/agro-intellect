"""Explicit provider-neutral Companion orchestration."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Protocol
import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.models import Plant
from ..agent_runtime.contracts import (
    AgentRuntimeOutcomeV1,
    AgentRuntimeValidationError,
    CurrentAuthorizationScope,
    MessageEnvelopeV1,
    RuntimeDecision,
    SafetyClassificationResultV1,
)
from ..agent_runtime.service import ModelExecution
from ..core.redaction import redact_text
from ..plant_operations.models import DailyCheckIn, ManualMeasurement
from ..safety_gate import (
    SafetyClassificationOutcomeV1,
    SafetyGateClassificationCommandV1,
    SafetyGateClassificationService,
    SafetyGateModelExecutor,
)
from ..timeline import TimelineEvent, TimelineJsonlAppender
from .contracts import (
    CompanionGovernanceError,
    CompanionGovernanceErrorCode,
    PersistCompanionProposalCommandV1,
)
from .models import CompanionHumanAttention, CompanionIssue, CompanionProposal
from .repository import CompanionGovernanceRepository, CurrentGovernanceScope
from .runtime_contracts import (
    CompanionInputRecordV1,
    CompanionModelResultV1,
    CompanionProviderRequestV1,
    CompanionRunCommandV1,
    CompanionRunResultV1,
    CompanionRuntimeValidationError,
)
from .service import CompanionGovernanceService


_MODEL_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9._-]{1,127}\Z")
_ENVELOPE_REF_RE = re.compile(
    r"^(plant|companion_issue|daily_checkin|manual_measurement):"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


class CompanionModelExecutor(Protocol):
    model_ref: str

    def execute(
        self,
        request: CompanionProviderRequestV1,
    ) -> ModelExecution | Mapping[str, object]: ...


class CompanionClassificationService(Protocol):
    def classify(
        self,
        command: SafetyGateClassificationCommandV1,
    ) -> SafetyClassificationOutcomeV1: ...


class CompanionInputDenied(RuntimeError):
    def __init__(self, failure_code: str, reason_code: str = "context_denied") -> None:
        self.failure_code = failure_code
        self.reason_code = reason_code
        super().__init__("Companion input context is unavailable.")


@dataclass(frozen=True, slots=True)
class AssembledCompanionInputV1:
    request: CompanionProviderRequestV1


class DatabaseCompanionInputAssembler:
    """Load only the exact current Plant/issue/check-in/measurement snapshot."""

    def __init__(
        self,
        session: Session,
        *,
        repository: CompanionGovernanceRepository | None = None,
        secret_values: Iterable[str] = (),
    ) -> None:
        self._session = session
        self._repository = repository or CompanionGovernanceRepository(session)
        self._secret_values = tuple(secret_values)

    def assemble(
        self,
        command: CompanionRunCommandV1,
    ) -> AssembledCompanionInputV1:
        scope = _run_scope(
            self._repository.current_scope(
                command.actor_context,
                plant_id=command.plant_id,
                for_update=False,
            )
        )
        plant = self._session.scalar(
            select(Plant)
            .where(
                Plant.farm_id == scope.farm_id,
                Plant.plant_id == scope.plant_id,
            )
            .execution_options(populate_existing=True)
        )
        if plant is None or plant.status != "active":
            raise CompanionInputDenied("COMPANION_PLANT_NOT_ACTIVE")

        records = [_plant_record(plant)]
        if command.issue_id is not None:
            issue = self._repository.issue(
                command.issue_id,
                plant_id=scope.plant_id,
                farm_id=scope.farm_id,
                for_update=False,
            )
            if issue is None:
                raise CompanionInputDenied("COMPANION_COMMAND_FORBIDDEN")
            if issue.status != "open":
                raise CompanionInputDenied("COMPANION_ISSUE_NOT_OPEN")
            if issue.record_version != command.expected_issue_version:
                raise CompanionInputDenied("COMPANION_VERSION_CONFLICT")
            records.append(_issue_record(issue))

        check_in = self._session.scalar(
            select(DailyCheckIn)
            .where(
                DailyCheckIn.farm_id == scope.farm_id,
                DailyCheckIn.plant_id == scope.plant_id,
                DailyCheckIn.check_in_state == "completed",
            )
            .order_by(DailyCheckIn.recorded_at.desc(), DailyCheckIn.check_in_id.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        measurement = self._session.scalar(
            select(ManualMeasurement)
            .where(
                ManualMeasurement.farm_id == scope.farm_id,
                ManualMeasurement.plant_id == scope.plant_id,
                ManualMeasurement.source_type == "manual_user",
                ManualMeasurement.trust_status == "confirmed",
                or_(
                    ManualMeasurement.ph.is_not(None),
                    ManualMeasurement.ec_ms_cm.is_not(None),
                ),
            )
            .order_by(
                ManualMeasurement.measured_at.desc(),
                ManualMeasurement.measurement_id.desc(),
            )
            .limit(1)
            .execution_options(populate_existing=True)
        )
        try:
            if check_in is not None:
                records.append(_check_in_record(check_in))
            if measurement is not None:
                records.append(_measurement_record(measurement))
            request = CompanionProviderRequestV1(
                target_mode=(
                    "existing_issue" if command.issue_id is not None else "new_issue"
                ),
                records=tuple(
                    _sanitized_record(record, secret_values=self._secret_values)
                    for record in records
                ),
            )
        except (CompanionRuntimeValidationError, TypeError, ValueError):
            raise CompanionInputDenied(
                "COMPANION_READ_INCONSISTENT",
                "input_contract_violation",
            ) from None
        return AssembledCompanionInputV1(request=request)


class _CompanionMessageEnvelopeV1(MessageEnvelopeV1):
    __slots__ = ()

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not _uuid4(self.message_id)
            or not _uuid4(self.run_id)
            or self.agent_id != "companion"
            or not _utc_datetime(self.created_at)
            or not isinstance(self.farm_id, uuid.UUID)
            or not isinstance(self.plant_id, uuid.UUID)
            or self.runtime_decision is not RuntimeDecision.SPEAK
            or self.candidate_claim_type not in {"task_request", "team_signal"}
            or isinstance(self.confidence, bool)
            or not isinstance(self.confidence, int | float)
            or not 0 <= float(self.confidence) <= 1
            or not isinstance(self.candidate_output, str)
            or self.candidate_output != self.candidate_output.strip()
            or not 1 <= len(self.candidate_output) <= 2000
            or not 1 <= len(self.source_refs) <= 4
            or len(self.source_refs) != len(set(self.source_refs))
            or any(_ENVELOPE_REF_RE.fullmatch(ref) is None for ref in self.source_refs)
            or self.publication_state != "pending_classification"
            or self.consumable_by_agents is not False
            or not isinstance(self.authorization_scope, CurrentAuthorizationScope)
            or self.authorization_scope.farm_id != self.farm_id
            or self.authorization_scope.plant_id != self.plant_id
        ):
            raise AgentRuntimeValidationError()


@dataclass(frozen=True, slots=True)
class _ModelStage:
    outcome: AgentRuntimeOutcomeV1 | None
    request: CompanionProviderRequestV1 | None
    result: CompanionModelResultV1 | None
    model_ref: str | None
    failure_code: str | None = None
    failure_stage: str = "runtime"


TimelineAppender = Callable[[TimelineEvent], Mapping[str, object]]
Clock = Callable[[], datetime]


class CompanionRuntimeService:
    """Run Companion, classify its pending envelope, then call the sole writer."""

    def __init__(
        self,
        session: Session,
        *,
        model_executor: CompanionModelExecutor | None = None,
        safety_classifier_executor: SafetyGateModelExecutor | None = None,
        input_assembler: DatabaseCompanionInputAssembler | None = None,
        classification_service: CompanionClassificationService | None = None,
        governance_service: CompanionGovernanceService | None = None,
        repository: CompanionGovernanceRepository | None = None,
        timeline_append: TimelineAppender | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._session = session
        self._model_executor = model_executor
        self._clock = clock or _utc_now
        self._repository = repository or CompanionGovernanceRepository(session)
        self._input_assembler = input_assembler or DatabaseCompanionInputAssembler(
            session,
            repository=self._repository,
        )
        self._timeline_append = timeline_append or TimelineJsonlAppender()
        self._classification_service = (
            classification_service
            or SafetyGateClassificationService(
                session,
                model_executor=safety_classifier_executor,
                clock=self._clock,
            )
        )
        self._governance_service = governance_service or CompanionGovernanceService(
            session,
            timeline_appender=self._timeline_append,
            clock=self._clock,
        )

    def run(self, command: CompanionRunCommandV1) -> CompanionRunResultV1:
        if not isinstance(command, CompanionRunCommandV1):
            raise CompanionRuntimeValidationError()
        fingerprint = companion_run_fingerprint(command)
        early = self._committed_duplicate(command, fingerprint)
        if early is not None:
            return early

        stage = self._invoke_model(command)
        if stage.outcome is not None:
            return _failed_from_stage(command.run_id, stage)
        assert stage.request is not None and stage.result is not None
        assert stage.model_ref is not None

        guarded = self._finalize_runtime(
            command,
            request=stage.request,
            result=stage.result,
            model_ref=stage.model_ref,
        )
        if isinstance(guarded, CompanionRunResultV1):
            return guarded
        outcome, envelope = guarded

        self._rollback()
        try:
            classified = self._classification_service.classify(
                SafetyGateClassificationCommandV1(
                    classification_run_id=uuid.uuid4(),
                    requested_at=_as_utc(self._clock()),
                    actor_context=command.actor_context,
                    message_envelope=envelope,
                )
            )
        except Exception:
            classified = None
        self._rollback()
        if classified is None:
            return _failed(
                command.run_id,
                outcome,
                "SAFETY_CLASSIFICATION_PERSISTENCE_FAILED",
                "classification",
            )
        if not classified.authoritative:
            code = {
                "classification_conflict": "SAFETY_CLASSIFICATION_CONFLICT",
                "guard_denied": "SAFETY_CLASSIFICATION_GUARD_DENIED",
                "persistence_failed": "SAFETY_CLASSIFICATION_PERSISTENCE_FAILED",
            }.get(
                classified.outcome_kind,
                "SAFETY_CLASSIFICATION_PERSISTENCE_FAILED",
            )
            return _failed(command.run_id, outcome, code, "classification")
        classification = classified.classification_result
        if classification is None:
            return _failed(
                command.run_id,
                outcome,
                "SAFETY_CLASSIFICATION_PERSISTENCE_FAILED",
                "classification",
            )
        if (
            self._classification_consumer_route(envelope, classification)
            != "companion_governance_hold"
        ):
            return _failed(
                command.run_id,
                outcome,
                "SAFETY_CLASSIFICATION_CONFLICT",
                "classification",
            )
        classification_ref = f"safety_classification:{classification.message_id}"
        route_reason = _classification_disposition(stage.result, classification)
        if route_reason is not None:
            return CompanionRunResultV1(
                run_id=command.run_id,
                runtime_outcome=outcome,
                route_status="not_governable",
                classification_ref=classification_ref,
                issue_ref=None,
                attention_ref=None,
                proposal_ref=None,
                reason_code=route_reason,
                failure_code=None,
                failure_stage=None,
            )

        assert stage.result.attention_summary is not None
        assert stage.result.proposal_summary is not None
        assert stage.result.proposal_text is not None
        assert stage.result.proposed_effect is not None
        assert stage.result.suggested_resolution is not None
        try:
            persisted = self._governance_service.persist_companion_proposal(
                PersistCompanionProposalCommandV1(
                    actor_context=command.actor_context,
                    run_id=command.run_id,
                    message_id=envelope.message_id,
                    plant_id=command.plant_id,
                    target_issue_id=command.issue_id,
                    expected_issue_version=command.expected_issue_version,
                    issue_summary_text=stage.result.issue_summary,
                    attention_summary_text=stage.result.attention_summary,
                    proposal_summary=stage.result.proposal_summary,
                    proposal_text=stage.result.proposal_text,
                    rationale_text=stage.result.rationale_text,
                    proposed_effect=stage.result.proposed_effect,
                    task_display_text=stage.result.task_display_text,
                    suggested_resolution=stage.result.suggested_resolution,
                    provider_input_refs=stage.request.source_refs,
                    run_request_fingerprint=fingerprint,
                )
            )
        except CompanionGovernanceError as error:
            self._rollback()
            if error.code is CompanionGovernanceErrorCode.VERSION_CONFLICT:
                duplicate = self._committed_duplicate(command, fingerprint)
                if duplicate is not None and duplicate.route_status == "proposal_duplicate":
                    return duplicate
            return _failed(
                command.run_id,
                outcome,
                error.code.value,
                "governance",
                classification_ref=classification_ref,
            )
        except Exception:
            self._rollback()
            return _failed(
                command.run_id,
                outcome,
                "COMPANION_PERSISTENCE_FAILED",
                "governance",
                classification_ref=classification_ref,
            )
        return CompanionRunResultV1(
            run_id=command.run_id,
            runtime_outcome=(
                outcome if persisted.result == "created" else None
            ),
            route_status=(
                "proposal_created"
                if persisted.result == "created"
                else "proposal_duplicate"
            ),
            classification_ref=f"safety_classification:{persisted.classification_message_id}",
            issue_ref=f"companion_issue:{persisted.issue_id}",
            attention_ref=f"companion_attention:{persisted.attention_id}",
            proposal_ref=f"companion_proposal:{persisted.proposal_id}",
            reason_code=None,
            failure_code=None,
            failure_stage=None,
        )

    def invoke(self, command: CompanionRunCommandV1) -> CompanionRunResultV1:
        return self.run(command)

    def _committed_duplicate(
        self,
        command: CompanionRunCommandV1,
        fingerprint: str,
    ) -> CompanionRunResultV1 | None:
        self._rollback()
        try:
            scope = _run_scope(
                self._repository.current_scope(
                    command.actor_context,
                    plant_id=command.plant_id,
                    for_update=False,
                )
            )
            proposal = self._repository.proposal_by_run(
                command.run_id,
                for_update=False,
            )
            if proposal is None:
                self._rollback()
                return None
            if proposal.run_request_fingerprint != fingerprint:
                self._rollback()
                return _failed(
                    command.run_id,
                    _context_denied(command.run_id),
                    "COMPANION_VERSION_CONFLICT",
                    "governance",
                )
            issue = self._repository.issue(
                proposal.issue_id,
                plant_id=scope.plant_id,
                farm_id=scope.farm_id,
                for_update=False,
            )
            attention = self._repository.attention(
                proposal.attention_id,
                for_update=False,
            )
            classification = self._repository.classification(
                proposal.source_classification_message_id,
                for_update=False,
            )
            valid = (
                issue is not None
                and attention is not None
                and proposal.farm_id == scope.farm_id
                and proposal.plant_id == scope.plant_id
                and attention.issue_id == issue.issue_id
                and classification is not None
                and classification.message_id
                == proposal.source_classification_message_id
                and classification.origin_agent_id == "companion"
                and classification.farm_id == scope.farm_id
                and classification.plant_id == scope.plant_id
                and classification.provider_status == "completed"
                and (
                    (
                        proposal.proposed_effect
                        in {"discussion_only", "none"}
                        and classification.classification == "safe_information"
                        and classification.safe_task_kind is None
                    )
                    or (
                        proposal.proposed_effect
                        in {"check", "measurement", "follow_up"}
                        and classification.classification == "safe_task_request"
                        and classification.safe_task_kind == proposal.proposed_effect
                    )
                )
            )
            if not valid:
                self._rollback()
                return _failed(
                    command.run_id,
                    _context_denied(command.run_id, "input_contract_violation"),
                    "COMPANION_READ_INCONSISTENT",
                    "governance",
                )
            result = CompanionRunResultV1(
                run_id=command.run_id,
                runtime_outcome=None,
                route_status="proposal_duplicate",
                classification_ref=f"safety_classification:{classification.message_id}",
                issue_ref=f"companion_issue:{issue.issue_id}",
                attention_ref=f"companion_attention:{attention.attention_id}",
                proposal_ref=f"companion_proposal:{proposal.proposal_id}",
                reason_code=None,
                failure_code=None,
                failure_stage=None,
            )
            self._rollback()
            return result
        except CompanionInputDenied as denied:
            self._rollback()
            return _failed(
                command.run_id,
                _context_denied(command.run_id, denied.reason_code),
                denied.failure_code,
                "governance",
            )
        except Exception:
            self._rollback()
            return _failed(
                command.run_id,
                _context_denied(command.run_id, "input_contract_violation"),
                "COMPANION_READ_INCONSISTENT",
                "governance",
            )

    def _invoke_model(self, command: CompanionRunCommandV1) -> _ModelStage:
        try:
            assembled = self._input_assembler.assemble(command)
        except CompanionInputDenied as denied:
            self._rollback()
            return _ModelStage(
                _context_denied(command.run_id, denied.reason_code),
                None,
                None,
                None,
                denied.failure_code,
                "governance",
            )
        except Exception:
            self._rollback()
            return _ModelStage(
                _context_denied(command.run_id, "input_contract_violation"),
                None,
                None,
                None,
                "COMPANION_READ_INCONSISTENT",
                "runtime",
            )
        self._rollback()
        executor = self._model_executor
        model_ref = getattr(executor, "model_ref", None)
        if (
            executor is None
            or not isinstance(model_ref, str)
            or _MODEL_REF_RE.fullmatch(model_ref) is None
        ):
            return _ModelStage(_not_configured(command.run_id), None, None, None)
        try:
            execution = executor.execute(assembled.request)
        except Exception:
            return _ModelStage(
                self._audit(
                    command,
                    assembled.request,
                    model_ref,
                    outcome_kind="provider_failed",
                    status="failed",
                    final_decision=None,
                    reason_code="provider_failed",
                    error_code="AGENT_PROVIDER_FAILED",
                    provider_call_status="failed",
                    result=None,
                    envelope=None,
                ),
                None,
                None,
                None,
            )
        try:
            result = CompanionModelResultV1.from_untrusted(
                _execution_result(execution, expected_model_ref=model_ref),
                request=assembled.request,
            )
        except CompanionRuntimeValidationError:
            return _ModelStage(
                self._audit(
                    command,
                    assembled.request,
                    model_ref,
                    outcome_kind="output_invalid",
                    status="blocked",
                    final_decision=None,
                    reason_code="output_invalid",
                    error_code="AGENT_OUTPUT_INVALID",
                    provider_call_status="completed",
                    result=None,
                    envelope=None,
                ),
                None,
                None,
                None,
            )
        return _ModelStage(None, assembled.request, result, model_ref)

    def _finalize_runtime(
        self,
        command: CompanionRunCommandV1,
        *,
        request: CompanionProviderRequestV1,
        result: CompanionModelResultV1,
        model_ref: str,
    ) -> tuple[AgentRuntimeOutcomeV1, MessageEnvelopeV1] | CompanionRunResultV1:
        failure = self._post_io_failure(command)
        if failure is not None:
            outcome = self._audit(
                command,
                request,
                model_ref,
                outcome_kind="publication_guard_denied",
                status="blocked",
                final_decision=None,
                reason_code="publication_guard_denied",
                error_code="AGENT_PUBLICATION_BLOCKED",
                provider_call_status="completed",
                result=result,
                envelope=None,
            )
            return _failed(command.run_id, outcome, failure, "governance")
        if result.runtime_decision == "silent":
            assert result.reason_code is not None
            outcome = self._audit(
                command,
                request,
                model_ref,
                outcome_kind="model_silent",
                status="silent",
                final_decision="silent",
                reason_code=result.reason_code,
                error_code=None,
                provider_call_status="completed",
                result=result,
                envelope=None,
            )
            if outcome.outcome_kind == "audit_failed":
                return _failed(
                    command.run_id,
                    outcome,
                    "AGENT_AUDIT_FAILED",
                    "runtime",
                )
            return CompanionRunResultV1(
                run_id=command.run_id,
                runtime_outcome=outcome,
                route_status="silent",
                classification_ref=None,
                issue_ref=None,
                attention_ref=None,
                proposal_ref=None,
                reason_code=result.reason_code,
                failure_code=None,
                failure_stage=None,
            )
        scope = self._current_scope(command)
        if scope is None:
            outcome = self._audit(
                command,
                request,
                model_ref,
                outcome_kind="publication_guard_denied",
                status="blocked",
                final_decision=None,
                reason_code="publication_guard_denied",
                error_code="AGENT_PUBLICATION_BLOCKED",
                provider_call_status="completed",
                result=result,
                envelope=None,
            )
            return _failed(
                command.run_id,
                outcome,
                "COMPANION_COMMAND_FORBIDDEN",
                "governance",
            )
        envelope = _message_envelope(
            command,
            scope=scope,
            result=result,
            created_at=_as_utc(self._clock()),
        )
        outcome = self._audit(
            command,
            request,
            model_ref,
            outcome_kind="envelope_ready",
            status="envelope_ready",
            final_decision="speak",
            reason_code="envelope_ready",
            error_code=None,
            provider_call_status="completed",
            result=result,
            envelope=envelope,
        )
        if outcome.outcome_kind == "audit_failed":
            return _failed(
                command.run_id,
                outcome,
                "AGENT_AUDIT_FAILED",
                "runtime",
            )
        return outcome, envelope

    def _post_io_failure(self, command: CompanionRunCommandV1) -> str | None:
        self._rollback()
        try:
            scope = _run_scope(
                self._repository.current_scope(
                    command.actor_context,
                    plant_id=command.plant_id,
                    for_update=False,
                )
            )
            if command.issue_id is not None:
                issue = self._repository.issue(
                    command.issue_id,
                    plant_id=scope.plant_id,
                    farm_id=scope.farm_id,
                    for_update=False,
                )
                if issue is None:
                    return "COMPANION_COMMAND_FORBIDDEN"
                if issue.status != "open":
                    return "COMPANION_ISSUE_NOT_OPEN"
                if issue.record_version != command.expected_issue_version:
                    return "COMPANION_VERSION_CONFLICT"
            return None
        except CompanionInputDenied as denied:
            return denied.failure_code
        except Exception:
            return "COMPANION_COMMAND_FORBIDDEN"
        finally:
            self._rollback()

    def _classification_consumer_route(
        self,
        envelope: MessageEnvelopeV1,
        classification: SafetyClassificationResultV1,
    ) -> str | None:
        """Derive the sole Companion hold from committed matching evidence."""

        self._rollback()
        try:
            row = self._repository.classification(
                classification.message_id,
                for_update=False,
            )
            if (
                envelope.agent_id != "companion"
                or classification.message_id != envelope.message_id
                or row is None
                or row.message_id != envelope.message_id
                or row.farm_id != envelope.farm_id
                or row.plant_id != envelope.plant_id
                or row.origin_agent_id != envelope.agent_id
                or row.classifier_version != classification.classifier_version
                or row.classification != classification.classification
                or row.safe_task_kind != classification.safe_task_kind
                or row.reason_code != classification.reason_code
                or row.provider_status
                not in {"completed", "not_configured", "failed", "invalid"}
            ):
                return None
            return "companion_governance_hold"
        except Exception:
            return None
        finally:
            self._rollback()

    def _current_scope(
        self,
        command: CompanionRunCommandV1,
    ) -> CurrentAuthorizationScope | None:
        self._rollback()
        try:
            scope = _run_scope(
                self._repository.current_scope(
                    command.actor_context,
                    plant_id=command.plant_id,
                    for_update=False,
                )
            )
            return CurrentAuthorizationScope(
                farm_id=scope.farm_id,
                plant_id=scope.plant_id,
                role_preset=scope.role_preset,
                operation_kind="normal_read",
                permission_source=scope.permission_source,
                grant_id=scope.grant_id,
            )
        except Exception:
            return None
        finally:
            self._rollback()

    def _audit(
        self,
        command: CompanionRunCommandV1,
        request: CompanionProviderRequestV1,
        model_ref: str,
        *,
        outcome_kind: str,
        status: str,
        final_decision: str | None,
        reason_code: str,
        error_code: str | None,
        provider_call_status: str,
        result: CompanionModelResultV1 | None,
        envelope: MessageEnvelopeV1 | None,
    ) -> AgentRuntimeOutcomeV1:
        event = TimelineEvent(
            farm_id=command.actor_context.farm_id,
            plant_id=command.plant_id,
            actor_ref={
                "account_id": str(command.actor_context.account_id),
                "membership_id": str(command.actor_context.membership_id),
                "role_preset": command.actor_context.role_preset.value,
            },
            event_type="agent_runtime_decided",
            source_type="agent_runtime_attempt",
            source_id=command.run_id,
            source_refs={"input_refs": list(request.source_refs)},
            payload_summary={
                "agent_id": "companion",
                "model_ref": model_ref,
                "outcome_kind": outcome_kind,
                "candidate_decision": result.runtime_decision if result else None,
                "final_decision": final_decision,
                "outcome_status": status,
                "reason_code": reason_code,
                "error_code": error_code,
                "message_id": str(envelope.message_id) if envelope else None,
                "candidate_claim_type": (
                    envelope.candidate_claim_type if envelope else None
                ),
                "source_ref_count": len(request.source_refs),
            },
        )
        try:
            event_ref = self._timeline_append(event)
            if not _event_ref_valid(event_ref):
                raise ValueError
        except Exception:
            return AgentRuntimeOutcomeV1(
                run_id=command.run_id,
                outcome_kind="audit_failed",
                status="failed",
                final_decision=None,
                reason_code="audit_failed",
                error_code="AGENT_AUDIT_FAILED",
                message_envelope=None,
                event_ref=None,
                model_ref=model_ref,
                provider_call_status=provider_call_status,
                audit_status="failed",
            )
        return AgentRuntimeOutcomeV1(
            run_id=command.run_id,
            outcome_kind=outcome_kind,
            status=status,
            final_decision=final_decision,
            reason_code=reason_code,
            error_code=error_code,
            message_envelope=envelope,
            event_ref=dict(event_ref),
            model_ref=model_ref,
            provider_call_status=provider_call_status,
            audit_status="appended",
        )

    def _rollback(self) -> None:
        if self._session.in_transaction():
            self._session.rollback()


def companion_run_fingerprint(command: CompanionRunCommandV1) -> str:
    if not isinstance(command, CompanionRunCommandV1):
        raise CompanionRuntimeValidationError()
    value = {
        "schema_version": 1,
        "run_id": str(command.run_id),
        "plant_id": str(command.plant_id),
        "issue_id": str(command.issue_id) if command.issue_id else None,
        "expected_issue_version": command.expected_issue_version,
    }
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _run_scope(scope: CurrentGovernanceScope | None) -> CurrentGovernanceScope:
    if scope is None:
        raise CompanionInputDenied("COMPANION_COMMAND_FORBIDDEN")
    if scope.plant_status != "active":
        raise CompanionInputDenied("COMPANION_PLANT_NOT_ACTIVE")
    if not scope.can_operate or scope.role_preset not in {"boss", "engineer"}:
        raise CompanionInputDenied("COMPANION_COMMAND_FORBIDDEN")
    return scope


def _plant_record(row: Plant) -> CompanionInputRecordV1:
    return CompanionInputRecordV1(
        record_type="plant",
        source_ref=f"plant:{row.plant_id}",
        payload={"plant_id": str(row.plant_id), "status": "active"},
    )


def _sanitized_record(
    record: CompanionInputRecordV1,
    *,
    secret_values: tuple[str, ...],
) -> CompanionInputRecordV1:
    """Return the outbound record copy with configured secret values removed.

    Only the outbound copy is sanitized; the service-side source payload and
    the persisted rows remain unchanged. A sanitizer failure fails closed.
    """

    payload = {
        key: redact_text(value, extra_secrets=secret_values)
        if isinstance(value, str)
        else value
        for key, value in record.payload.items()
    }
    return CompanionInputRecordV1(
        record_type=record.record_type,
        source_ref=record.source_ref,
        payload=payload,
    )


def _issue_record(row: CompanionIssue) -> CompanionInputRecordV1:
    return CompanionInputRecordV1(
        record_type="companion_issue",
        source_ref=f"companion_issue:{row.issue_id}",
        payload={
            "issue_id": str(row.issue_id),
            "status": row.status,
            "record_version": row.record_version,
            "is_focused": row.is_focused,
            "summary_text": row.summary_text,
        },
    )


def _check_in_record(row: DailyCheckIn) -> CompanionInputRecordV1:
    return CompanionInputRecordV1(
        record_type="daily_checkin",
        source_ref=f"daily_checkin:{row.check_in_id}",
        payload={
            "check_in_id": str(row.check_in_id),
            "observed_at": _timestamp(row.observed_at),
            "recorded_at": _timestamp(row.recorded_at),
            "observation_state": row.observation_state,
            "observation_text": row.observation_text,
        },
    )


def _measurement_record(row: ManualMeasurement) -> CompanionInputRecordV1:
    return CompanionInputRecordV1(
        record_type="manual_measurement",
        source_ref=f"manual_measurement:{row.measurement_id}",
        payload={
            "measurement_id": str(row.measurement_id),
            "measured_at": _timestamp(row.measured_at),
            "recorded_at": _timestamp(row.recorded_at),
            "ph": f"{row.ph:.2f}" if row.ph is not None else None,
            "ec_ms_cm": f"{row.ec_ms_cm:.3f}" if row.ec_ms_cm is not None else None,
            "source_type": "manual_user",
            "trust_status": "confirmed",
        },
    )


def _message_envelope(
    command: CompanionRunCommandV1,
    *,
    scope: CurrentAuthorizationScope,
    result: CompanionModelResultV1,
    created_at: datetime,
) -> MessageEnvelopeV1:
    assert result.proposal_text is not None
    assert result.proposed_effect is not None
    assert result.confidence is not None
    return _CompanionMessageEnvelopeV1(
        message_id=uuid.uuid4(),
        run_id=command.run_id,
        agent_id="companion",
        created_at=created_at,
        farm_id=scope.farm_id,
        plant_id=scope.plant_id,
        runtime_decision=RuntimeDecision.SPEAK,
        candidate_claim_type=(
            "task_request"
            if result.proposed_effect in {"check", "measurement", "follow_up"}
            else "team_signal"
        ),
        confidence=result.confidence,
        source_refs=result.source_refs,
        candidate_output=result.proposal_text,
        authorization_scope=scope,
    )


def _classification_disposition(result, classification) -> str | None:
    if classification.classification == "physical_action":
        return "physical_action_not_allowed"
    if classification.classification == "blocked_uncertain":
        return "classification_uncertain"
    if result.proposed_effect in {"discussion_only", "none"}:
        return (
            None
            if classification.classification == "safe_information"
            and classification.safe_task_kind is None
            else "classification_mismatch"
        )
    return (
        None
        if classification.classification == "safe_task_request"
        and classification.safe_task_kind == result.proposed_effect
        else "classification_mismatch"
    )


def _failed_from_stage(
    run_id: uuid.UUID,
    stage: _ModelStage,
) -> CompanionRunResultV1:
    assert stage.outcome is not None
    return _failed(
        run_id,
        stage.outcome,
        stage.failure_code or stage.outcome.error_code or "AGENT_CONTEXT_DENIED",
        stage.failure_stage,
    )


def _failed(
    run_id: uuid.UUID,
    outcome: AgentRuntimeOutcomeV1,
    code: str,
    stage: str,
    *,
    classification_ref: str | None = None,
) -> CompanionRunResultV1:
    return CompanionRunResultV1(
        run_id=run_id,
        runtime_outcome=outcome,
        route_status="failed",
        classification_ref=classification_ref,
        issue_ref=None,
        attention_ref=None,
        proposal_ref=None,
        reason_code=None,
        failure_code=code,
        failure_stage=stage,
    )


def _context_denied(
    run_id: uuid.UUID,
    reason_code: str = "context_denied",
) -> AgentRuntimeOutcomeV1:
    safe_reason = (
        reason_code
        if reason_code in {"context_denied", "input_contract_violation"}
        else "context_denied"
    )
    return AgentRuntimeOutcomeV1(
        run_id=run_id,
        outcome_kind="context_denied",
        status="blocked",
        final_decision=None,
        reason_code=safe_reason,
        error_code="AGENT_CONTEXT_DENIED",
        message_envelope=None,
        event_ref=None,
        model_ref=None,
        provider_call_status="not_attempted",
        audit_status="not_attempted",
    )


def _not_configured(run_id: uuid.UUID) -> AgentRuntimeOutcomeV1:
    return AgentRuntimeOutcomeV1(
        run_id=run_id,
        outcome_kind="runtime_not_configured",
        status="failed",
        final_decision=None,
        reason_code="runtime_not_configured",
        error_code="AGENT_RUNTIME_NOT_CONFIGURED",
        message_envelope=None,
        event_ref=None,
        model_ref=None,
        provider_call_status="not_attempted",
        audit_status="not_attempted",
    )


def _execution_result(execution: object, *, expected_model_ref: str) -> object:
    if isinstance(execution, ModelExecution):
        return execution.result if execution.model_ref == expected_model_ref else None
    return execution if isinstance(execution, Mapping) else None


def _event_ref_valid(value: object) -> bool:
    if (
        not isinstance(value, Mapping)
        or set(value)
        != {"timeline_event_id", "timeline_ref", "event_type", "created_at"}
        or not _uuid_text(value["timeline_event_id"])
        or value["timeline_ref"] != f"timeline.jsonl#{value['timeline_event_id']}"
        or value["event_type"] != "agent_runtime_decided"
        or not isinstance(value["created_at"], str)
    ):
        return False
    try:
        created_at = datetime.fromisoformat(value["created_at"])
    except ValueError:
        return False
    return _utc_datetime(created_at) and created_at.isoformat() == value["created_at"]


def _uuid_text(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def _uuid4(value: object) -> bool:
    return isinstance(value, uuid.UUID) and value.version == 4


def _utc_datetime(value: object) -> bool:
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() == timezone.utc.utcoffset(value)
    )


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "AssembledCompanionInputV1",
    "CompanionClassificationService",
    "CompanionInputDenied",
    "CompanionModelExecutor",
    "CompanionRuntimeService",
    "DatabaseCompanionInputAssembler",
    "companion_run_fingerprint",
]
