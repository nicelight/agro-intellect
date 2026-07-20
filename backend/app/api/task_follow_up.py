"""Protected strict HTTP boundary for FT-012 Approval, Task, and Outcome."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
import re
import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, WithJsonSchema

from ..access_admin.actor_context import ActorContext
from ..access_admin.dependencies import require_actor_context
from ..access_admin.errors import AuthErrorCode, auth_error_response, request_id_for
from ..task_follow_up import (
    ApprovalDecisionCommandV1,
    ApprovalStatus,
    CompleteTaskCommandV1,
    OutcomeValue,
    RecordOutcomeCommandV1,
    TaskFollowUpError,
    TaskFollowUpErrorCode,
    TaskFollowUpService,
)
from ..timeline import TimelineJsonlAppender


router = APIRouter(prefix="/api", tags=["task-follow-up"])


_CANONICAL_UUID_PATTERN = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_CANONICAL_UUID_BYTES = re.compile(_CANONICAL_UUID_PATTERN.encode("ascii"))
_FT012_RAW_ROUTE_PATTERNS = (
    re.compile(rb"^/api/plants/([^/]+)/tasks$"),
    re.compile(rb"^/api/plants/([^/]+)/approvals$"),
    re.compile(rb"^/api/plants/([^/]+)/safety-decisions/([^/]+)/approval$"),
    re.compile(rb"^/api/plants/([^/]+)/tasks/([^/]+)/complete$"),
    re.compile(rb"^/api/plants/([^/]+)/tasks/([^/]+)/outcome$"),
)
_FT012_DECODED_ROUTE_PATTERNS = tuple(
    re.compile(pattern.pattern.decode("ascii"))
    for pattern in _FT012_RAW_ROUTE_PATTERNS
)


class FT012RawPathCanonicalityMiddleware:
    """Reject alternate raw spellings before routing or dependencies run."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") == "http" and _raw_ft012_path_is_invalid(scope):
            request = Request(scope, receive=receive)
            response = auth_error_response(request, AuthErrorCode.VALIDATION_FAILED)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def _raw_ft012_path_is_invalid(scope: dict[str, object]) -> bool:
    raw_path = scope.get("raw_path")
    if isinstance(raw_path, bytes):
        for pattern in _FT012_RAW_ROUTE_PATTERNS:
            match = pattern.fullmatch(raw_path)
            if match is not None:
                return any(
                    _CANONICAL_UUID_BYTES.fullmatch(segment) is None
                    for segment in match.groups()
                )
    decoded_path = scope.get("path")
    return isinstance(decoded_path, str) and any(
        pattern.fullmatch(decoded_path) is not None
        for pattern in _FT012_DECODED_ROUTE_PATTERNS
    )


def _parse_canonical_path_uuid(value: object) -> uuid.UUID:
    if not isinstance(value, str):
        raise ValueError("Path id must be a lowercase canonical UUID string.")
    try:
        parsed = uuid.UUID(value)
    except (AttributeError, TypeError, ValueError):
        raise ValueError(
            "Path id must be a lowercase canonical UUID string."
        ) from None
    if str(parsed) != value:
        raise ValueError("Path id must be a lowercase canonical UUID string.")
    return parsed


CanonicalPathUUID = Annotated[
    uuid.UUID,
    BeforeValidator(_parse_canonical_path_uuid),
    WithJsonSchema(
        {
            "type": "string",
            "format": "uuid",
            "pattern": _CANONICAL_UUID_PATTERN,
        }
    ),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SafeActorViewV1(StrictModel):
    account_id: uuid.UUID
    membership_id: uuid.UUID
    role_preset: Literal["boss", "engineer"]
    agent_id: str | None


class SafeOutcomeActorViewV1(StrictModel):
    account_id: uuid.UUID
    membership_id: uuid.UUID
    role_preset: Literal["boss", "engineer"]


class OutcomeViewV1(StrictModel):
    outcome_id: uuid.UUID
    follow_up_task_id: uuid.UUID
    value: Literal["improved", "worsened", "unchanged", "no_data"]
    evidence_refs: list[str]
    recorded_at: datetime
    recorded_by: SafeOutcomeActorViewV1


class TaskViewV1(StrictModel):
    task_id: uuid.UUID
    kind: Literal["check", "measurement", "action", "follow_up"]
    status: Literal["open", "completed"]
    display_text: str
    source_type: Literal["safe_task_request", "approved_action", "automatic_follow_up"]
    source_refs: list[str]
    due_at: datetime | None
    created_at: datetime
    completed_at: datetime | None
    created_by: SafeActorViewV1
    completed_by: SafeActorViewV1 | None
    parent_action_task_id: uuid.UUID | None
    outcome: OutcomeViewV1 | None


class BossApprovalActorViewV1(StrictModel):
    account_id: uuid.UUID
    membership_id: uuid.UUID
    role_preset: Literal["boss"]
    permission_source: Literal["boss_role"]


class PlantAccessGrantApprovalActorViewV1(StrictModel):
    account_id: uuid.UUID
    membership_id: uuid.UUID
    role_preset: Literal["engineer"]
    permission_source: Literal["plant_access_grant"]
    grant_id: uuid.UUID


ApprovalActorViewV1 = Annotated[
    BossApprovalActorViewV1 | PlantAccessGrantApprovalActorViewV1,
    Field(discriminator="permission_source"),
]


class ApprovalViewV1(StrictModel):
    approval_id: uuid.UUID
    safety_decision_id: uuid.UUID
    action_kind: Literal["ph_adjustment", "ec_adjustment", "solution_change"]
    status: Literal["pending", "approved", "rejected"]
    record_version: int
    valid_until: datetime
    is_expired: bool
    source_refs: list[str]
    created_at: datetime
    decided_at: datetime | None
    decided_by: ApprovalActorViewV1 | None


class TaskListV1(StrictModel):
    schema_version: Literal[1] = 1
    items: list[TaskViewV1]


class ApprovalListV1(StrictModel):
    schema_version: Literal[1] = 1
    items: list[ApprovalViewV1]


class ApprovalDecisionRequestV1(StrictModel):
    schema_version: Literal[1]
    request_id: uuid.UUID
    expected_version: int = Field(ge=1)
    decision: Literal["approved", "rejected"]


class CompleteTaskRequestV1(StrictModel):
    schema_version: Literal[1]
    request_id: uuid.UUID


class RecordOutcomeRequestV1(StrictModel):
    schema_version: Literal[1]
    request_id: uuid.UUID
    value: Literal["improved", "worsened", "unchanged", "no_data"]
    evidence_refs: list[str] = Field(min_length=0, max_length=4)


class ApprovalDecisionResultV1(StrictModel):
    schema_version: Literal[1] = 1
    approval: ApprovalViewV1
    action_task: TaskViewV1 | None
    result: Literal["created", "duplicate"]


class CompleteTaskResultV1(StrictModel):
    schema_version: Literal[1] = 1
    task: TaskViewV1
    follow_up_task: TaskViewV1 | None
    result: Literal["created", "duplicate"]


class RecordOutcomeResultV1(StrictModel):
    schema_version: Literal[1] = 1
    task: TaskViewV1
    outcome: OutcomeViewV1
    result: Literal["created", "duplicate"]


class ErrorDetail(StrictModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(StrictModel):
    error: ErrorDetail


_ERRORS = {
    TaskFollowUpErrorCode.TASK_REQUEST_INVALID: (400, "Task request is invalid."),
    TaskFollowUpErrorCode.TASK_SCOPE_NOT_FOUND: (404, "Task scope is not available."),
    TaskFollowUpErrorCode.TASK_COMMAND_FORBIDDEN: (404, "Task scope is not available."),
    TaskFollowUpErrorCode.TASK_PLANT_NOT_ACTIVE: (409, "Plant is not active."),
    TaskFollowUpErrorCode.TASK_SOURCE_INVALID: (409, "Task source is not current."),
    TaskFollowUpErrorCode.APPROVAL_NOT_CURRENT: (409, "Approval is not current."),
    TaskFollowUpErrorCode.TASK_VERSION_CONFLICT: (409, "Task record changed or request conflicts."),
    TaskFollowUpErrorCode.TASK_INVALID_TRANSITION: (409, "Task transition is not allowed."),
    TaskFollowUpErrorCode.TASK_EVIDENCE_REQUIRED: (422, "Outcome evidence is invalid or required."),
    TaskFollowUpErrorCode.TASK_AUDIT_FAILED: (500, "Task audit trail could not be recorded."),
    TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED: (500, "Task request could not be completed."),
}
_ERROR_RESPONSES = {code: {"model": ErrorEnvelope} for code in (400, 401, 404, 409, 422, 500)}
_TASK_LIST_PARAMETERS = [
    {"name": "status", "in": "query", "required": False, "schema": {"type": "string", "enum": ["open", "completed"]}},
    {"name": "kind", "in": "query", "required": False, "schema": {"type": "string", "enum": ["check", "measurement", "action", "follow_up"]}},
    {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "default": 50, "minimum": 1, "maximum": 100}},
]
_APPROVAL_LIST_PARAMETERS = [
    {"name": "status", "in": "query", "required": False, "schema": {"type": "string", "enum": ["pending", "approved", "rejected"]}},
    {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "default": 50, "minimum": 1, "maximum": 100}},
]


@router.get(
    "/plants/{plant_id}/tasks",
    response_model=TaskListV1,
    responses=_ERROR_RESPONSES,
    openapi_extra={"parameters": _TASK_LIST_PARAMETERS},
)
def list_tasks(
    plant_id: CanonicalPathUUID,
    request: Request,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
) -> TaskListV1 | JSONResponse:
    try:
        status, kind, limit = _task_query(request)
        with request.app.state.database.session() as session:
            rows = TaskFollowUpService(session).list_tasks(
                actor, plant_id=plant_id, status=status, kind=kind, limit=limit
            )
        result = TaskListV1(items=[_task_view(task, outcome) for task, outcome in rows])
    except TaskFollowUpError as error:
        return _error_response(request, error.code)
    except Exception:
        return _error_response(request, TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get(
    "/plants/{plant_id}/approvals",
    response_model=ApprovalListV1,
    responses=_ERROR_RESPONSES,
    openapi_extra={"parameters": _APPROVAL_LIST_PARAMETERS},
)
def list_approvals(
    plant_id: CanonicalPathUUID,
    request: Request,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
) -> ApprovalListV1 | JSONResponse:
    try:
        status, limit = _approval_query(request)
        now = datetime.now(timezone.utc)
        with request.app.state.database.session() as session:
            rows = TaskFollowUpService(session).list_approvals(
                actor, plant_id=plant_id, status=status, limit=limit
            )
        result = ApprovalListV1(items=[_approval_view(row, now=now) for row in rows])
    except TaskFollowUpError as error:
        return _error_response(request, error.code)
    except Exception:
        return _error_response(request, TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post(
    "/plants/{plant_id}/safety-decisions/{safety_decision_id}/approval",
    response_model=ApprovalDecisionResultV1,
    responses=_ERROR_RESPONSES,
)
def decide_approval(
    plant_id: CanonicalPathUUID,
    safety_decision_id: CanonicalPathUUID,
    payload: ApprovalDecisionRequestV1,
    request: Request,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
) -> ApprovalDecisionResultV1 | JSONResponse:
    try:
        _no_query(request)
        command = ApprovalDecisionCommandV1(
            actor_context=actor, plant_id=plant_id,
            safety_decision_id=safety_decision_id,
            request_id=payload.request_id,
            expected_version=payload.expected_version,
            decision=ApprovalStatus(payload.decision),
        )
        with request.app.state.database.session() as session:
            result = TaskFollowUpService(
                session,
                timeline_appender=TimelineJsonlAppender(request.app.state.settings),
            ).decide_approval(command)
        body = ApprovalDecisionResultV1(
            approval=_approval_view(result.approval),
            action_task=_task_view(result.action_task) if result.action_task else None,
            result=result.result,
        )
    except TaskFollowUpError as error:
        return _error_response(request, error.code)
    except Exception:
        return _error_response(request, TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED)
    response.headers["Cache-Control"] = "no-store"
    return body


@router.post(
    "/plants/{plant_id}/tasks/{task_id}/complete",
    response_model=CompleteTaskResultV1,
    responses=_ERROR_RESPONSES,
)
def complete_task(
    plant_id: CanonicalPathUUID,
    task_id: CanonicalPathUUID,
    payload: CompleteTaskRequestV1,
    request: Request,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
) -> CompleteTaskResultV1 | JSONResponse:
    try:
        _no_query(request)
        with request.app.state.database.session() as session:
            result = TaskFollowUpService(
                session,
                timeline_appender=TimelineJsonlAppender(request.app.state.settings),
            ).complete_task(CompleteTaskCommandV1(
                actor_context=actor, plant_id=plant_id,
                task_id=task_id, request_id=payload.request_id,
            ))
        body = CompleteTaskResultV1(
            task=_task_view(result.task),
            follow_up_task=_task_view(result.follow_up_task) if result.follow_up_task else None,
            result=result.result,
        )
    except TaskFollowUpError as error:
        return _error_response(request, error.code)
    except Exception:
        return _error_response(request, TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED)
    response.headers["Cache-Control"] = "no-store"
    return body


@router.post(
    "/plants/{plant_id}/tasks/{task_id}/outcome",
    response_model=RecordOutcomeResultV1,
    responses=_ERROR_RESPONSES,
)
def record_outcome(
    plant_id: CanonicalPathUUID,
    task_id: CanonicalPathUUID,
    payload: RecordOutcomeRequestV1,
    request: Request,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
) -> RecordOutcomeResultV1 | JSONResponse:
    try:
        _no_query(request)
        with request.app.state.database.session() as session:
            result = TaskFollowUpService(
                session,
                timeline_appender=TimelineJsonlAppender(request.app.state.settings),
            ).record_outcome(RecordOutcomeCommandV1(
                actor_context=actor, plant_id=plant_id,
                follow_up_task_id=task_id, request_id=payload.request_id,
                value=OutcomeValue(payload.value),
                evidence_refs=tuple(payload.evidence_refs),
            ))
        body = RecordOutcomeResultV1(
            task=_task_view(result.task, result.outcome),
            outcome=_outcome_view(result.outcome), result=result.result,
        )
    except TaskFollowUpError as error:
        return _error_response(request, error.code)
    except Exception:
        return _error_response(request, TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED)
    response.headers["Cache-Control"] = "no-store"
    return body


def _task_view(task, outcome=None) -> TaskViewV1:
    completed_by = None
    if task.completed_by_account_id is not None:
        completed_by = SafeActorViewV1(
            account_id=task.completed_by_account_id,
            membership_id=task.completed_by_membership_id,
            role_preset=task.completed_by_role_preset,
            agent_id=None,
        )
    return TaskViewV1(
        task_id=task.task_id, kind=task.kind, status=task.status,
        display_text=task.display_text, source_type=task.source_type,
        source_refs=list(task.source_refs), due_at=task.due_at,
        created_at=task.created_at, completed_at=task.completed_at,
        created_by=SafeActorViewV1(
            account_id=task.created_by_account_id,
            membership_id=task.created_by_membership_id,
            role_preset=task.created_by_role_preset,
            agent_id=task.created_by_agent_id,
        ),
        completed_by=completed_by,
        parent_action_task_id=task.parent_action_task_id,
        outcome=_outcome_view(outcome) if outcome is not None else None,
    )


def _outcome_view(outcome) -> OutcomeViewV1:
    return OutcomeViewV1(
        outcome_id=outcome.outcome_id,
        follow_up_task_id=outcome.follow_up_task_id,
        value=outcome.value, evidence_refs=list(outcome.evidence_refs),
        recorded_at=outcome.recorded_at,
        recorded_by=SafeOutcomeActorViewV1(
            account_id=outcome.recorded_by_account_id,
            membership_id=outcome.recorded_by_membership_id,
            role_preset=outcome.recorded_by_role_preset,
        ),
    )


def _approval_view(approval, *, now=None) -> ApprovalViewV1:
    instant = now or datetime.now(timezone.utc)
    decided_by = None
    if approval.decision_actor_account_id is not None:
        actor_fields = {
            "account_id": approval.decision_actor_account_id,
            "membership_id": approval.decision_actor_membership_id,
            "role_preset": approval.decision_actor_role_preset,
            "permission_source": approval.decision_permission_source,
        }
        if approval.decision_permission_source == "boss_role":
            decided_by = BossApprovalActorViewV1(**actor_fields)
        else:
            decided_by = PlantAccessGrantApprovalActorViewV1(
                **actor_fields,
                grant_id=approval.decision_grant_id,
            )
    valid_until = approval.valid_until
    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=timezone.utc)
    return ApprovalViewV1(
        approval_id=approval.approval_id,
        safety_decision_id=approval.safety_decision_id,
        action_kind=approval.action_kind, status=approval.status,
        record_version=approval.record_version, valid_until=valid_until,
        is_expired=instant > valid_until,
        source_refs=list(approval.source_refs), created_at=approval.created_at,
        decided_at=approval.decided_at, decided_by=decided_by,
    )


def _task_query(request: Request) -> tuple[str | None, str | None, int]:
    allowed = {"status", "kind", "limit"}
    if any(key not in allowed for key in request.query_params):
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
    if any(len(request.query_params.getlist(key)) > 1 for key in allowed):
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
    status = request.query_params.get("status")
    kind = request.query_params.get("kind")
    if status not in {None, "open", "completed"}:
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
    if kind not in {None, "check", "measurement", "action", "follow_up"}:
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
    return status, kind, _limit(request)


def _approval_query(request: Request) -> tuple[str | None, int]:
    allowed = {"status", "limit"}
    if any(key not in allowed for key in request.query_params):
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
    if any(len(request.query_params.getlist(key)) > 1 for key in allowed):
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
    status = request.query_params.get("status")
    if status not in {None, "pending", "approved", "rejected"}:
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
    return status, _limit(request)


def _limit(request: Request) -> int:
    raw = request.query_params.get("limit", "50")
    try:
        value = int(raw)
    except ValueError:
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID) from None
    if not 1 <= value <= 100 or str(value) != raw:
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
    return value


def _no_query(request: Request) -> None:
    if request.query_params:
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)


def _error_response(request: Request, code: TaskFollowUpErrorCode) -> JSONResponse:
    status, message = _ERRORS[code]
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code.value, "message": message, "request_id": request_id_for(request)}},
        headers={"Cache-Control": "no-store"},
    )


__all__ = ["FT012RawPathCanonicalityMiddleware", "router"]
