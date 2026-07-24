"""Atomic W1 proposal authority and retained Companion read model."""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
import json
import uuid

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..timeline import TimelineAppendError, TimelineEvent, TimelineJsonlAppender
from .contracts import (
    CompanionGovernanceError,
    CompanionGovernanceErrorCode,
    CompanionGovernanceValidationError,
    CompanionIssueDetailV1,
    IssueStackPageV1,
    PersistCompanionProposalCommandV1,
    ProposalEffect,
    ProposalPersistenceResultV1,
    timestamp_text,
)
from .integrity import (
    validate_w1_current_pair,
    validate_w1_issue_graph,
    validate_w1_proposal_edge,
)
from .models import CompanionHumanAttention, CompanionIssue, CompanionProposal
from .projections import (
    apply_canonical_proposal_projection,
    attention_ui_event,
    new_ui_model,
    proposal_ui_event,
    require_canonical_pending_proposal_projection,
)
from .repository import CompanionGovernanceRepository, CurrentGovernanceScope


class CompanionGovernanceService:
    def __init__(
        self,
        session: Session,
        *,
        timeline_appender: Callable[[TimelineEvent], dict[str, object]] | None = None,
        repository: CompanionGovernanceRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or CompanionGovernanceRepository(session)
        self._timeline = timeline_appender or TimelineJsonlAppender()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def persist_companion_proposal(
        self,
        command: PersistCompanionProposalCommandV1,
    ) -> ProposalPersistenceResultV1:
        if not isinstance(command, PersistCompanionProposalCommandV1):
            raise CompanionGovernanceValidationError()
        if self._session.in_transaction():
            self._session.rollback()
        try:
            with self._session.begin():
                scope = self._require_write_scope(command)
                classification = self._repository.classification(
                    command.message_id,
                    for_update=True,
                )
                if not _classification_matches(command, classification, scope):
                    raise CompanionGovernanceError(
                        CompanionGovernanceErrorCode.EFFECT_INVALID
                    )

                existing = self._repository.proposal_by_run(
                    command.run_id,
                    for_update=True,
                )
                if existing is not None:
                    existing_issue = self._repository.issue(
                        existing.issue_id,
                        plant_id=scope.plant_id,
                        farm_id=scope.farm_id,
                        for_update=True,
                    )
                    existing_attention = self._repository.attention(
                        existing.attention_id,
                        for_update=True,
                    )
                    if (
                        existing_issue is not None
                        and existing_attention is not None
                        and _proposal_matches_command(
                            existing,
                            command,
                            scope,
                            issue=existing_issue,
                        )
                    ):
                        validate_w1_proposal_edge(
                            existing_issue,
                            existing_attention,
                            existing,
                        )
                        return _result(existing, result="duplicate")
                    raise CompanionGovernanceError(
                        CompanionGovernanceErrorCode.VERSION_CONFLICT
                    )

                now = self._clock()
                proposal_id = uuid.uuid4()
                focused = self._repository.focused_issue(
                    command.plant_id,
                    for_update=True,
                )
                issue = self._prepare_issue(
                    command,
                    scope=scope,
                    focused=focused,
                    now=now,
                    proposal_id=proposal_id,
                )
                active_attention = self._repository.active_attention(
                    issue.issue_id,
                    for_update=True,
                )
                proposal_sequence = self._repository.next_proposal_sequence(
                    issue.issue_id
                )
                if active_attention is None:
                    attention = CompanionHumanAttention(
                        attention_id=uuid.uuid4(),
                        farm_id=scope.farm_id,
                        plant_id=scope.plant_id,
                        issue_id=issue.issue_id,
                        attention_sequence=self._repository.next_attention_sequence(
                            issue.issue_id
                        ),
                        status="active",
                        summary_text=command.attention_summary_text,
                        current_proposal_id=proposal_id,
                        record_version=1,
                        created_at=now,
                    )
                    self._session.add(attention)
                    self._add_attention_projection(
                        attention,
                        issue=issue,
                    )
                else:
                    attention = active_attention
                    current = self._repository.proposal(
                        attention.current_proposal_id,
                        for_update=True,
                    )
                    if current is None:
                        raise CompanionGovernanceError(
                            CompanionGovernanceErrorCode.READ_INCONSISTENT
                        )
                    validate_w1_current_pair(issue, attention, current)
                    projection = self._repository.ui_projection(
                        current.proposal_id,
                        for_update=True,
                    )
                    require_canonical_pending_proposal_projection(
                        projection,
                        current,
                    )
                if command.target_issue_id is not None:
                    self._focus_existing_issue(issue, focused=focused)
                if active_attention is not None:
                    superseded_ref = self._append(
                        scope,
                        event_type="companion_proposal_superseded",
                        source_id=current.proposal_id,
                        source_refs=[
                            f"companion_issue:{issue.issue_id}",
                            f"companion_attention:{attention.attention_id}",
                            f"companion_proposal:{current.proposal_id}",
                            f"companion_proposal:{proposal_id}",
                        ],
                        payload={
                            "proposal_sequence": current.proposal_sequence,
                            "replacement_proposal_id": str(proposal_id),
                            "record_version": 2,
                        },
                        actor=command.actor_context,
                    )
                    current.state = "superseded"
                    current.record_version = 2
                    current.terminal_at = now
                    current.superseded_event_ref = superseded_ref
                    apply_canonical_proposal_projection(projection, current)
                    attention.current_proposal_id = proposal_id
                    attention.record_version += 1

                created_ref = self._append(
                    scope,
                    event_type="companion_proposal_created",
                    source_id=proposal_id,
                    source_refs=list(command.proposal_source_refs),
                    payload={
                        "proposal_sequence": proposal_sequence,
                        "proposed_effect": command.proposed_effect.value,
                        "suggested_resolution": command.suggested_resolution.value,
                        "attention_sequence": attention.attention_sequence,
                        "source_ref_count": len(command.proposal_source_refs),
                    },
                    actor=command.actor_context,
                )
                proposal = CompanionProposal(
                    proposal_id=proposal_id,
                    farm_id=scope.farm_id,
                    plant_id=scope.plant_id,
                    issue_id=issue.issue_id,
                    attention_id=attention.attention_id,
                    proposal_sequence=proposal_sequence,
                    state="pending",
                    record_version=1,
                    proposal_summary=command.proposal_summary,
                    proposal_text=command.proposal_text,
                    rationale_text=command.rationale_text,
                    proposed_effect=command.proposed_effect.value,
                    task_display_text=command.task_display_text,
                    suggested_resolution=command.suggested_resolution.value,
                    source_run_id=command.run_id,
                    source_message_id=command.message_id,
                    source_classification_message_id=command.message_id,
                    source_refs=list(command.proposal_source_refs),
                    run_request_fingerprint=command.run_request_fingerprint,
                    created_at=now,
                    created_event_ref=created_ref,
                )
                self._session.add(proposal)
                self._add_proposal_projection(proposal)
                self._session.flush()
                return _result(proposal, result="created")
        except CompanionGovernanceError:
            raise
        except TimelineAppendError:
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.AUDIT_FAILED
            ) from None
        except IntegrityError:
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.VERSION_CONFLICT
            ) from None
        except (SQLAlchemyError, TypeError, ValueError):
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.PERSISTENCE_FAILED
            ) from None

    def list_issues(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        status: str | None,
        cursor: str | None,
        limit: int,
    ) -> IssueStackPageV1:
        if (
            not isinstance(actor, ActorContext)
            or not isinstance(plant_id, uuid.UUID)
            or status not in {None, "open", "resolved", "closed"}
            or not isinstance(limit, int)
            or isinstance(limit, bool)
            or not 1 <= limit <= 100
        ):
            raise CompanionGovernanceValidationError()
        parsed_cursor = _decode_cursor(cursor) if cursor is not None else None
        if parsed_cursor is not None and status is not None:
            expected_rank = {"open": 0, "resolved": 1, "closed": 2}[status]
            if parsed_cursor[0] != expected_rank:
                raise CompanionGovernanceValidationError()
        scope = self._repository.current_scope(
            actor,
            plant_id=plant_id,
            for_update=False,
        )
        if scope is None or not scope.can_read:
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.COMMAND_FORBIDDEN
            )
        rows = self._repository.list_issues(
            farm_id=scope.farm_id,
            plant_id=plant_id,
            status=status,
            cursor=parsed_cursor,
            limit=limit,
        )
        page_rows = rows[:limit]
        next_cursor = (
            _encode_cursor(page_rows[-1]) if len(rows) > limit and page_rows else None
        )
        focused = self._repository.focused_issue(plant_id, for_update=False)
        return IssueStackPageV1(
            plant_id=plant_id,
            focused_issue_ref=(
                f"companion_issue:{focused.issue_id}" if focused is not None else None
            ),
            items=tuple(_issue_value(row) for row in page_rows),
            next_cursor=next_cursor,
        )

    def get_issue_detail(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        issue_id: uuid.UUID,
    ) -> CompanionIssueDetailV1:
        if (
            not isinstance(actor, ActorContext)
            or not isinstance(plant_id, uuid.UUID)
            or not isinstance(issue_id, uuid.UUID)
        ):
            raise CompanionGovernanceValidationError()
        scope = self._repository.current_scope(
            actor,
            plant_id=plant_id,
            for_update=False,
        )
        if scope is None or not scope.can_read:
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.COMMAND_FORBIDDEN
            )
        issue = self._repository.issue(
            issue_id,
            plant_id=plant_id,
            farm_id=scope.farm_id,
            for_update=False,
        )
        if issue is None:
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.COMMAND_FORBIDDEN
            )
        attentions = self._repository.attentions(issue_id)
        proposals = self._repository.proposals(issue_id)
        decisions = self._repository.decisions_for_w1_graph(
            issue_id,
            attention_ids=[item.attention_id for item in attentions],
            proposal_ids=[item.proposal_id for item in proposals],
        )
        graph = validate_w1_issue_graph(
            issue,
            farm_id=scope.farm_id,
            plant_id=plant_id,
            attentions=attentions,
            proposals=proposals,
            decisions=decisions,
        )
        conclusion = _conclusion_value(
            issue,
            active_attention=graph.active_attention,
            current_proposal=graph.current_proposal,
            latest_decision=None,
        )
        return CompanionIssueDetailV1(
            issue=_issue_value(issue),
            attention=(
                _attention_value(graph.selected_attention)
                if graph.selected_attention is not None
                else None
            ),
            proposals=tuple(_proposal_value(item) for item in proposals),
            decision_records=(),
            conclusion=conclusion,
        )

    def _require_write_scope(
        self,
        command: PersistCompanionProposalCommandV1,
    ) -> CurrentGovernanceScope:
        scope = self._repository.current_scope(
            command.actor_context,
            plant_id=command.plant_id,
            for_update=True,
        )
        if scope is None:
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.COMMAND_FORBIDDEN
            )
        if scope.plant_status != "active":
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.PLANT_NOT_ACTIVE
            )
        if not scope.can_operate or scope.role_preset not in {"boss", "engineer"}:
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.COMMAND_FORBIDDEN
            )
        return scope

    def _prepare_issue(
        self,
        command: PersistCompanionProposalCommandV1,
        *,
        scope: CurrentGovernanceScope,
        focused: CompanionIssue | None,
        now: datetime,
        proposal_id: uuid.UUID,
    ) -> CompanionIssue:
        if command.target_issue_id is None:
            issue_id = uuid.uuid4()
            if focused is not None:
                focused.is_focused = False
                focused.record_version += 1
            opened_ref = self._append(
                scope,
                event_type="companion_issue_opened",
                source_id=issue_id,
                source_refs=list(command.proposal_source_refs),
                payload={
                    "issue_status": "open",
                    "is_focused": True,
                    "source_ref_count": len(command.proposal_source_refs),
                },
                actor=command.actor_context,
            )
            issue = CompanionIssue(
                issue_id=issue_id,
                farm_id=scope.farm_id,
                plant_id=scope.plant_id,
                status="open",
                is_focused=True,
                summary_text=command.issue_summary_text,
                record_version=1,
                created_by_run_id=command.run_id,
                created_at=now,
                opened_event_ref=opened_ref,
            )
            self._session.add(issue)
            self._session.flush()
            return issue

        issue = self._repository.issue(
            command.target_issue_id,
            plant_id=scope.plant_id,
            farm_id=scope.farm_id,
            for_update=True,
        )
        if issue is None:
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.COMMAND_FORBIDDEN
            )
        if issue.status != "open":
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.ISSUE_NOT_OPEN
            )
        if issue.record_version != command.expected_issue_version:
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.VERSION_CONFLICT
            )
        return issue

    @staticmethod
    def _focus_existing_issue(
        issue: CompanionIssue,
        *,
        focused: CompanionIssue | None,
    ) -> None:
        if focused is not None and focused.issue_id != issue.issue_id:
            focused.is_focused = False
            focused.record_version += 1
        if not issue.is_focused:
            issue.is_focused = True
            issue.record_version += 1

    def _append(
        self,
        scope: CurrentGovernanceScope,
        *,
        event_type: str,
        source_id: uuid.UUID,
        source_refs: list[str],
        payload: dict[str, object],
        actor: ActorContext,
    ) -> dict[str, object]:
        return self._timeline(
            TimelineEvent(
                farm_id=scope.farm_id,
                plant_id=scope.plant_id,
                actor_ref={
                    "account_id": str(actor.account_id),
                    "membership_id": str(actor.membership_id),
                    "role_preset": scope.role_preset,
                },
                event_type=event_type,
                source_type={
                    "companion_issue_opened": "companion_issue",
                    "companion_proposal_created": "companion_proposal",
                    "companion_proposal_superseded": "companion_proposal",
                }[event_type],
                source_id=source_id,
                source_refs={"record_refs": source_refs},
                payload_summary=payload,
            )
        )

    def _add_attention_projection(
        self,
        attention: CompanionHumanAttention,
        *,
        issue: CompanionIssue,
    ) -> None:
        self._session.add(new_ui_model(attention_ui_event(attention, issue=issue)))

    def _add_proposal_projection(
        self,
        proposal: CompanionProposal,
    ) -> None:
        self._session.add(new_ui_model(proposal_ui_event(proposal)))


def _classification_matches(command, row, scope) -> bool:
    if (
        row is None
        or row.message_id != command.message_id
        or row.farm_id != scope.farm_id
        or row.plant_id != scope.plant_id
        or row.origin_agent_id != "companion"
        or row.provider_status != "completed"
    ):
        return False
    if command.proposed_effect in {ProposalEffect.DISCUSSION_ONLY, ProposalEffect.NONE}:
        return row.classification == "safe_information" and row.safe_task_kind is None
    return (
        row.classification == "safe_task_request"
        and row.safe_task_kind == command.proposed_effect.value
    )


def _proposal_matches_command(row, command, scope, *, issue) -> bool:
    return (
        row.farm_id == scope.farm_id
        and row.plant_id == scope.plant_id
        and row.source_message_id == command.message_id
        and row.source_classification_message_id == command.message_id
        and row.run_request_fingerprint == command.run_request_fingerprint
        and row.proposal_summary == command.proposal_summary
        and row.proposal_text == command.proposal_text
        and row.rationale_text == command.rationale_text
        and row.proposed_effect == command.proposed_effect.value
        and row.task_display_text == command.task_display_text
        and row.suggested_resolution == command.suggested_resolution.value
        and row.source_refs == list(command.proposal_source_refs)
        and (
            (
                command.target_issue_id is None
                and issue.created_by_run_id == command.run_id
                and issue.summary_text == command.issue_summary_text
            )
            or (
                command.target_issue_id is not None
                and row.issue_id == command.target_issue_id
                and issue.created_by_run_id != command.run_id
            )
        )
    )


def _result(row: CompanionProposal, *, result: str) -> ProposalPersistenceResultV1:
    return ProposalPersistenceResultV1(
        result=result,
        issue_id=row.issue_id,
        attention_id=row.attention_id,
        proposal_id=row.proposal_id,
        classification_message_id=row.source_classification_message_id,
    )


def _issue_value(issue: CompanionIssue) -> Mapping[str, object]:
    return {
        "issue_id": str(issue.issue_id),
        "issue_ref": f"companion_issue:{issue.issue_id}",
        "status": issue.status,
        "is_focused": issue.is_focused,
        "summary_text": issue.summary_text,
        "record_version": issue.record_version,
        "created_at": timestamp_text(issue.created_at),
        "resolved_at": timestamp_text(issue.resolved_at) if issue.resolved_at else None,
        "closed_at": timestamp_text(issue.closed_at) if issue.closed_at else None,
    }


def _attention_value(attention: CompanionHumanAttention) -> Mapping[str, object]:
    return {
        "attention_id": str(attention.attention_id),
        "attention_ref": f"companion_attention:{attention.attention_id}",
        "issue_ref": f"companion_issue:{attention.issue_id}",
        "attention_sequence": attention.attention_sequence,
        "status": attention.status,
        "summary_text": attention.summary_text,
        "current_proposal_ref": (
            f"companion_proposal:{attention.current_proposal_id}"
        ),
        "record_version": attention.record_version,
        "created_at": timestamp_text(attention.created_at),
        "satisfied_at": (
            timestamp_text(attention.satisfied_at)
            if attention.satisfied_at is not None
            else None
        ),
        "satisfied_by_decision_record_ref": (
            f"decision_record:{attention.satisfied_by_decision_record_id}"
            if attention.satisfied_by_decision_record_id is not None
            else None
        ),
    }


def _proposal_value(proposal: CompanionProposal) -> Mapping[str, object]:
    return {
        "proposal_id": str(proposal.proposal_id),
        "proposal_ref": f"companion_proposal:{proposal.proposal_id}",
        "issue_ref": f"companion_issue:{proposal.issue_id}",
        "attention_ref": f"companion_attention:{proposal.attention_id}",
        "proposal_sequence": proposal.proposal_sequence,
        "state": proposal.state,
        "record_version": proposal.record_version,
        "proposal_summary": proposal.proposal_summary,
        "proposal_text": proposal.proposal_text,
        "rationale_text": proposal.rationale_text,
        "proposed_effect": proposal.proposed_effect,
        "task_display_text": proposal.task_display_text,
        "suggested_resolution": proposal.suggested_resolution,
        "source_refs": list(proposal.source_refs),
        "created_at": timestamp_text(proposal.created_at),
        "terminal_at": (
            timestamp_text(proposal.terminal_at)
            if proposal.terminal_at is not None
            else None
        ),
        "decision_record_ref": (
            f"decision_record:{proposal.decision_record_id}"
            if proposal.decision_record_id is not None
            else None
        ),
        "created_event_ref": proposal.created_event_ref["timeline_ref"],
        "superseded_event_ref": (
            proposal.superseded_event_ref["timeline_ref"]
            if proposal.superseded_event_ref is not None
            else None
        ),
    }


def _decision_value(decision) -> Mapping[str, object]:
    return {
        "decision_record_id": str(decision.decision_record_id),
        "decision_record_ref": f"decision_record:{decision.decision_record_id}",
        "issue_ref": f"companion_issue:{decision.issue_id}",
        "attention_ref": f"companion_attention:{decision.attention_id}",
        "proposal_ref": f"companion_proposal:{decision.proposal_id}",
        "decision": decision.decision,
        "decision_summary": decision.decision_summary,
        "allowed_workflow_effect": decision.allowed_workflow_effect,
        "issue_resolution": decision.issue_resolution,
        "workflow_effect_ref": decision.workflow_effect_ref,
        "decider_account_id": str(decision.decider_account_id),
        "decider_membership_id": str(decision.decider_membership_id),
        "decider_role_preset": decision.decider_role_preset,
        "decider_permission_source": decision.decider_permission_source,
        "decider_grant_id": (
            str(decision.decider_grant_id)
            if decision.decider_grant_id is not None
            else None
        ),
        "decided_at": timestamp_text(decision.decided_at),
        "source_refs": list(decision.source_refs),
        "decision_event_ref": decision.decision_event_ref["timeline_ref"],
        "safety_gate_authority": "not_granted",
    }


def _conclusion_value(
    issue,
    *,
    active_attention,
    current_proposal,
    latest_decision,
) -> Mapping[str, object]:
    latest_group = {
        "latest_decision_record_ref": (
            f"decision_record:{latest_decision.decision_record_id}"
            if latest_decision is not None
            else None
        ),
        "decision": latest_decision.decision if latest_decision is not None else None,
        "decision_summary": (
            latest_decision.decision_summary if latest_decision is not None else None
        ),
        "allowed_workflow_effect": (
            latest_decision.allowed_workflow_effect
            if latest_decision is not None
            else None
        ),
        "decided_at": (
            timestamp_text(latest_decision.decided_at)
            if latest_decision is not None
            else None
        ),
    }
    if active_attention is not None:
        if (
            issue.status != "open"
            or current_proposal is None
            or current_proposal.state != "pending"
            or current_proposal.attention_id != active_attention.attention_id
        ):
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.READ_INCONSISTENT
            )
        conclusion_status = "awaiting_human"
        current_attention_ref = (
            f"companion_attention:{active_attention.attention_id}"
        )
        current_proposal_ref = f"companion_proposal:{current_proposal.proposal_id}"
    else:
        current_attention_ref = None
        current_proposal_ref = None
        if issue.status == "closed":
            conclusion_status = "closed"
        elif issue.status in {"open", "resolved"} and latest_decision is not None:
            conclusion_status = "decided"
        else:
            raise CompanionGovernanceError(
                CompanionGovernanceErrorCode.READ_INCONSISTENT
            )
    if issue.status in {"resolved", "closed"} and issue.is_focused:
        raise CompanionGovernanceError(
            CompanionGovernanceErrorCode.READ_INCONSISTENT
        )
    if conclusion_status in {"decided", "closed"} and latest_decision is None:
        raise CompanionGovernanceError(
            CompanionGovernanceErrorCode.READ_INCONSISTENT
        )
    return {
        "schema_version": 1,
        "issue_id": str(issue.issue_id),
        "issue_status": issue.status,
        "is_focused": issue.is_focused,
        "conclusion_status": conclusion_status,
        "current_attention_ref": current_attention_ref,
        "current_proposal_ref": current_proposal_ref,
        **latest_group,
        "safety_gate_authority": "not_granted",
    }


def _encode_cursor(issue: CompanionIssue) -> str:
    value = {
        "v": 1,
        "status_rank": {"open": 0, "resolved": 1, "closed": 2}[issue.status],
        "created_at": timestamp_text(issue.created_at),
        "issue_id": str(issue.issue_id),
    }
    raw = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(value: str) -> tuple[int, datetime, uuid.UUID]:
    if not isinstance(value, str) or not value or "=" in value:
        raise CompanionGovernanceValidationError()
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        parsed = json.loads(raw.decode("utf-8"))
        if (
            not isinstance(parsed, dict)
            or set(parsed) != {"v", "status_rank", "created_at", "issue_id"}
            or parsed["v"] != 1
            or parsed["status_rank"] not in {0, 1, 2}
            or json.dumps(
                parsed, separators=(",", ":"), ensure_ascii=False
            ).encode()
            != raw
        ):
            raise ValueError
        created_text = parsed["created_at"]
        if not isinstance(created_text, str) or not created_text.endswith("Z"):
            raise ValueError
        created_at = datetime.fromisoformat(created_text[:-1] + "+00:00")
        issue_id = uuid.UUID(parsed["issue_id"])
        if str(issue_id) != parsed["issue_id"]:
            raise ValueError
        if _encode_cursor_parts(parsed["status_rank"], created_at, issue_id) != value:
            raise ValueError
        return parsed["status_rank"], created_at, issue_id
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        raise CompanionGovernanceValidationError() from None


def _encode_cursor_parts(rank: int, created_at: datetime, issue_id: uuid.UUID) -> str:
    raw = json.dumps(
        {
            "v": 1,
            "status_rank": rank,
            "created_at": timestamp_text(created_at),
            "issue_id": str(issue_id),
        },
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


__all__ = ["CompanionGovernanceService"]
