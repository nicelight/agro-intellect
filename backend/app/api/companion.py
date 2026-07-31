"""Isolated strict read-only HTTP boundary for FT-013 W1."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Annotated, Literal
import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    UUID4,
    WithJsonSchema,
)

from ..access_admin.actor_context import ActorContext
from ..access_admin.dependencies import require_actor_context
from ..access_admin.errors import AuthErrorCode, auth_error_response, request_id_for
from ..companion_governance import (
    CloseCompanionIssueCommandV1,
    DecideCompanionProposalCommandV1,
    CompanionGovernanceError,
    CompanionGovernanceErrorCode,
    CompanionGovernanceService,
    CompanionGovernanceValidationError,
)


router = APIRouter(prefix="/api", tags=["companion-governance"])


_CANONICAL_UUID_PATTERN = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_CANONICAL_UUID_BYTES = re.compile(_CANONICAL_UUID_PATTERN.encode("ascii"))
_UUID_FRAGMENT = _CANONICAL_UUID_PATTERN.removeprefix("^").removesuffix("$")
_COMPANION_RAW_ROUTE_PATTERNS = (
    re.compile(rb"^/api/plants/([^/]+)/companion/issues$"),
    re.compile(rb"^/api/plants/([^/]+)/companion/issues/([^/]+)$"),
    re.compile(
        rb"^/api/plants/([^/]+)/companion/proposals/([^/]+)/decision$"
    ),
    re.compile(rb"^/api/plants/([^/]+)/companion/issues/([^/]+)/close$"),
)
_COMPANION_DECODED_ROUTE_PATTERNS = tuple(
    re.compile(pattern.pattern.decode("ascii"))
    for pattern in _COMPANION_RAW_ROUTE_PATTERNS
)


class FT013RawPathCanonicalityMiddleware:
    """Reject alternate UUID path spellings before dependencies or routing."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") == "http" and _raw_companion_path_is_invalid(scope):
            request = Request(scope, receive=receive)
            response = auth_error_response(request, AuthErrorCode.VALIDATION_FAILED)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def _raw_companion_path_is_invalid(scope: dict[str, object]) -> bool:
    raw_path = scope.get("raw_path")
    if isinstance(raw_path, bytes):
        for pattern in _COMPANION_RAW_ROUTE_PATTERNS:
            match = pattern.fullmatch(raw_path)
            if match is not None:
                return any(
                    _CANONICAL_UUID_BYTES.fullmatch(segment) is None
                    for segment in match.groups()
                )
    decoded_path = scope.get("path")
    return isinstance(decoded_path, str) and any(
        pattern.fullmatch(decoded_path) is not None
        for pattern in _COMPANION_DECODED_ROUTE_PATTERNS
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
CompanionIssueRef = Annotated[
    str,
    Field(pattern=rf"^companion_issue:{_UUID_FRAGMENT}$"),
]
CompanionAttentionRef = Annotated[
    str,
    Field(pattern=rf"^companion_attention:{_UUID_FRAGMENT}$"),
]
CompanionProposalRef = Annotated[
    str,
    Field(pattern=rf"^companion_proposal:{_UUID_FRAGMENT}$"),
]
DecisionRecordRef = Annotated[
    str,
    Field(pattern=rf"^decision_record:{_UUID_FRAGMENT}$"),
]
TaskRef = Annotated[str, Field(pattern=rf"^task:{_UUID_FRAGMENT}$")]
TimelineRef = Annotated[
    str,
    Field(pattern=rf"^timeline\.jsonl#{_UUID_FRAGMENT}$"),
]
SafeSourceRef = Annotated[
    str,
    Field(
        pattern=(
            rf"^(plant|daily_checkin|manual_measurement|message_envelope|"
            rf"safety_classification|companion_issue|companion_attention|"
            rf"companion_proposal|decision_record|task):{_UUID_FRAGMENT}$"
        )
    ),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IssueSummaryV1(StrictModel):
    issue_id: uuid.UUID
    issue_ref: CompanionIssueRef
    status: Literal["open", "resolved", "closed"]
    is_focused: bool
    summary_text: str = Field(min_length=1, max_length=500)
    record_version: int = Field(ge=1)
    created_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None


class CompanionAttentionViewV1(StrictModel):
    attention_id: uuid.UUID
    attention_ref: CompanionAttentionRef
    issue_ref: CompanionIssueRef
    attention_sequence: int = Field(ge=1)
    status: Literal["active", "satisfied"]
    summary_text: str = Field(min_length=1, max_length=500)
    current_proposal_ref: CompanionProposalRef
    record_version: int = Field(ge=1)
    created_at: datetime
    satisfied_at: datetime | None
    satisfied_by_decision_record_ref: DecisionRecordRef | None


class CompanionProposalViewV1(StrictModel):
    proposal_id: uuid.UUID
    proposal_ref: CompanionProposalRef
    issue_ref: CompanionIssueRef
    attention_ref: CompanionAttentionRef
    proposal_sequence: int = Field(ge=1)
    state: Literal["pending", "approved", "rejected", "superseded"]
    record_version: Literal[1, 2]
    proposal_summary: str = Field(min_length=1, max_length=500)
    proposal_text: str = Field(min_length=1, max_length=2000)
    rationale_text: str | None = Field(default=None, min_length=1, max_length=2000)
    proposed_effect: Literal[
        "discussion_only",
        "check",
        "measurement",
        "follow_up",
        "none",
    ]
    task_display_text: str | None = Field(
        default=None,
        min_length=1,
        max_length=2000,
    )
    suggested_resolution: Literal["keep_open", "resolved"]
    source_refs: list[SafeSourceRef] = Field(min_length=3, max_length=6)
    created_at: datetime
    terminal_at: datetime | None
    decision_record_ref: DecisionRecordRef | None
    created_event_ref: TimelineRef
    superseded_event_ref: TimelineRef | None


class DecisionRecordViewV1(StrictModel):
    decision_record_id: uuid.UUID
    decision_record_ref: DecisionRecordRef
    issue_ref: CompanionIssueRef
    attention_ref: CompanionAttentionRef
    proposal_ref: CompanionProposalRef
    decision: Literal["approved", "rejected"]
    decision_summary: str = Field(min_length=1, max_length=500)
    allowed_workflow_effect: Literal[
        "discussion_only",
        "check",
        "measurement",
        "follow_up",
        "none",
    ]
    issue_resolution: Literal["keep_open", "resolved"]
    workflow_effect_ref: TaskRef | None
    decider_account_id: uuid.UUID
    decider_membership_id: uuid.UUID
    decider_role_preset: Literal["boss", "engineer"]
    decider_permission_source: Literal["boss_role", "plant_access_grant"]
    decider_grant_id: uuid.UUID | None
    decided_at: datetime
    source_refs: list[SafeSourceRef] = Field(min_length=5, max_length=7)
    decision_event_ref: TimelineRef
    safety_gate_authority: Literal["not_granted"]


class CompanionConclusionV1(StrictModel):
    schema_version: Literal[1]
    issue_id: uuid.UUID
    issue_status: Literal["open", "resolved", "closed"]
    is_focused: bool
    conclusion_status: Literal["awaiting_human", "decided", "closed"]
    current_attention_ref: CompanionAttentionRef | None
    current_proposal_ref: CompanionProposalRef | None
    latest_decision_record_ref: DecisionRecordRef | None
    decision: Literal["approved", "rejected"] | None
    decision_summary: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )
    allowed_workflow_effect: Literal[
        "discussion_only",
        "check",
        "measurement",
        "follow_up",
        "none",
    ] | None
    decided_at: datetime | None
    safety_gate_authority: Literal["not_granted"]


class IssueStackPageResponseV1(StrictModel):
    schema_version: Literal[1]
    plant_id: uuid.UUID
    focused_issue_ref: CompanionIssueRef | None
    items: list[IssueSummaryV1] = Field(max_length=100)
    next_cursor: str | None


class CompanionIssueDetailResponseV1(StrictModel):
    schema_version: Literal[1]
    issue: IssueSummaryV1
    attention: CompanionAttentionViewV1 | None
    proposals: list[CompanionProposalViewV1]
    decision_records: list[DecisionRecordViewV1]
    conclusion: CompanionConclusionV1


class CompanionDecisionRequestV1(StrictModel):
    schema_version: Literal[1]
    request_id: UUID4
    expected_version: Literal[1]
    decision: Literal["approved", "rejected"]
    decision_summary: str = Field(min_length=1, max_length=500)
    issue_resolution: Literal["keep_open", "resolved"]


class CompanionDecisionResultResponseV1(StrictModel):
    schema_version: Literal[1]
    result: Literal["created", "duplicate"]
    decision_record: DecisionRecordViewV1
    workflow_task_ref: TaskRef | None
    issue: IssueSummaryV1
    conclusion: CompanionConclusionV1


class CompanionIssueCloseRequestV1(StrictModel):
    schema_version: Literal[1]
    request_id: UUID4
    expected_version: int = Field(ge=1)


class CompanionIssueCloseResultResponseV1(StrictModel):
    schema_version: Literal[1]
    result: Literal["closed", "duplicate"]
    issue: IssueSummaryV1


class ErrorDetail(StrictModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(StrictModel):
    error: ErrorDetail


_ERRORS = {
    CompanionGovernanceErrorCode.COMMAND_FORBIDDEN: (
        404,
        "COMPANION_SCOPE_NOT_FOUND",
        "Companion scope is not available.",
    ),
    CompanionGovernanceErrorCode.PLANT_NOT_ACTIVE: (
        409,
        "COMPANION_PLANT_NOT_ACTIVE",
        "Plant is not active.",
    ),
    CompanionGovernanceErrorCode.ISSUE_NOT_OPEN: (
        409,
        "COMPANION_ISSUE_NOT_OPEN",
        "Companion issue is not open.",
    ),
    CompanionGovernanceErrorCode.PROPOSAL_NOT_CURRENT: (
        409,
        "COMPANION_PROPOSAL_NOT_CURRENT",
        "Companion proposal is not current.",
    ),
    CompanionGovernanceErrorCode.VERSION_CONFLICT: (
        409,
        "COMPANION_VERSION_CONFLICT",
        "Companion governance record changed or request conflicts.",
    ),
    CompanionGovernanceErrorCode.EFFECT_INVALID: (
        422,
        "COMPANION_EFFECT_INVALID",
        "Companion proposal effect is invalid.",
    ),
    CompanionGovernanceErrorCode.READ_INCONSISTENT: (
        500,
        "COMPANION_READ_INCONSISTENT",
        "Companion governance records are inconsistent.",
    ),
    CompanionGovernanceErrorCode.AUDIT_FAILED: (
        500,
        "COMPANION_AUDIT_FAILED",
        "Companion governance audit could not be recorded.",
    ),
    CompanionGovernanceErrorCode.PERSISTENCE_FAILED: (
        500,
        "COMPANION_PERSISTENCE_FAILED",
        "Companion governance request could not be completed.",
    ),
    CompanionGovernanceErrorCode.INTERNAL_ERROR: (
        500,
        "COMPANION_INTERNAL_ERROR",
        "Companion governance request failed.",
    ),
}
_ERROR_RESPONSES = {
    code: {"model": ErrorEnvelope}
    for code in (401, 403, 404, 409, 422, 500)
}
_LIST_PARAMETERS = [
    {
        "name": "status",
        "in": "query",
        "required": False,
        "schema": {
            "type": "string",
            "enum": ["open", "resolved", "closed"],
        },
    },
    {
        "name": "cursor",
        "in": "query",
        "required": False,
        "schema": {"type": "string"},
    },
    {
        "name": "limit",
        "in": "query",
        "required": False,
        "schema": {
            "type": "integer",
            "default": 50,
            "minimum": 1,
            "maximum": 100,
        },
    },
]


@router.get(
    "/plants/{plant_id}/companion/issues",
    response_model=IssueStackPageResponseV1,
    responses=_ERROR_RESPONSES,
    openapi_extra={"parameters": _LIST_PARAMETERS},
)
def list_companion_issues(
    plant_id: CanonicalPathUUID,
    request: Request,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
) -> IssueStackPageResponseV1 | JSONResponse:
    try:
        status, cursor, limit = _list_query(request)
        with request.app.state.database.session() as session:
            page = CompanionGovernanceService(session).list_issues(
                actor,
                plant_id=plant_id,
                status=status,
                cursor=cursor,
                limit=limit,
            )
        result = IssueStackPageResponseV1.model_validate(page.as_value())
    except CompanionGovernanceValidationError:
        return _validation_error_response(request)
    except CompanionGovernanceError as error:
        return _governance_error_response(request, error.code)
    except ValidationError:
        return _governance_error_response(
            request,
            CompanionGovernanceErrorCode.READ_INCONSISTENT,
        )
    except Exception:
        return _governance_error_response(
            request,
            CompanionGovernanceErrorCode.PERSISTENCE_FAILED,
        )
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get(
    "/plants/{plant_id}/companion/issues/{issue_id}",
    response_model=CompanionIssueDetailResponseV1,
    responses=_ERROR_RESPONSES,
)
def get_companion_issue(
    plant_id: CanonicalPathUUID,
    issue_id: CanonicalPathUUID,
    request: Request,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
) -> CompanionIssueDetailResponseV1 | JSONResponse:
    try:
        if request.query_params:
            raise CompanionGovernanceValidationError()
        with request.app.state.database.session() as session:
            detail = CompanionGovernanceService(session).get_issue_detail(
                actor,
                plant_id=plant_id,
                issue_id=issue_id,
            )
        result = CompanionIssueDetailResponseV1.model_validate(detail.as_value())
    except CompanionGovernanceValidationError:
        return _validation_error_response(request)
    except CompanionGovernanceError as error:
        return _governance_error_response(request, error.code)
    except ValidationError:
        return _governance_error_response(
            request,
            CompanionGovernanceErrorCode.READ_INCONSISTENT,
        )
    except Exception:
        return _governance_error_response(
            request,
            CompanionGovernanceErrorCode.PERSISTENCE_FAILED,
        )
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post(
    "/plants/{plant_id}/companion/proposals/{proposal_id}/decision",
    response_model=CompanionDecisionResultResponseV1,
    responses=_ERROR_RESPONSES,
)
def decide_companion_proposal(
    plant_id: CanonicalPathUUID,
    proposal_id: CanonicalPathUUID,
    body: CompanionDecisionRequestV1,
    request: Request,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
) -> CompanionDecisionResultResponseV1 | JSONResponse:
    try:
        if request.query_params:
            raise CompanionGovernanceValidationError()
        with request.app.state.database.session() as session:
            result_value = CompanionGovernanceService(
                session
            ).decide_companion_proposal(
                DecideCompanionProposalCommandV1(
                    actor_context=actor,
                    plant_id=plant_id,
                    proposal_id=proposal_id,
                    request_id=body.request_id,
                    expected_version=body.expected_version,
                    decision=body.decision,
                    decision_summary=body.decision_summary,
                    issue_resolution=body.issue_resolution,
                )
            )
        result = CompanionDecisionResultResponseV1.model_validate(
            result_value.as_value()
        )
    except CompanionGovernanceValidationError:
        return _validation_error_response(request)
    except CompanionGovernanceError as error:
        return _governance_error_response(request, error.code)
    except ValidationError:
        return _governance_error_response(
            request,
            CompanionGovernanceErrorCode.READ_INCONSISTENT,
        )
    except Exception:
        return _governance_error_response(
            request,
            CompanionGovernanceErrorCode.INTERNAL_ERROR,
        )
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post(
    "/plants/{plant_id}/companion/issues/{issue_id}/close",
    response_model=CompanionIssueCloseResultResponseV1,
    responses=_ERROR_RESPONSES,
)
def close_companion_issue(
    plant_id: CanonicalPathUUID,
    issue_id: CanonicalPathUUID,
    body: CompanionIssueCloseRequestV1,
    request: Request,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
) -> CompanionIssueCloseResultResponseV1 | JSONResponse:
    try:
        if request.query_params:
            raise CompanionGovernanceValidationError()
        with request.app.state.database.session() as session:
            result_value = CompanionGovernanceService(
                session
            ).close_companion_issue(
                CloseCompanionIssueCommandV1(
                    actor_context=actor,
                    plant_id=plant_id,
                    issue_id=issue_id,
                    request_id=body.request_id,
                    expected_version=body.expected_version,
                )
            )
        result = CompanionIssueCloseResultResponseV1.model_validate(
            result_value.as_value()
        )
    except CompanionGovernanceValidationError:
        return _validation_error_response(request)
    except CompanionGovernanceError as error:
        return _governance_error_response(request, error.code)
    except ValidationError:
        return _governance_error_response(
            request,
            CompanionGovernanceErrorCode.READ_INCONSISTENT,
        )
    except Exception:
        return _governance_error_response(
            request,
            CompanionGovernanceErrorCode.INTERNAL_ERROR,
        )
    response.headers["Cache-Control"] = "no-store"
    return result


def _list_query(request: Request) -> tuple[str | None, str | None, int]:
    allowed = {"status", "cursor", "limit"}
    if any(key not in allowed for key in request.query_params):
        raise CompanionGovernanceValidationError()
    if any(len(request.query_params.getlist(key)) > 1 for key in allowed):
        raise CompanionGovernanceValidationError()
    status = request.query_params.get("status")
    if status not in {None, "open", "resolved", "closed"}:
        raise CompanionGovernanceValidationError()
    cursor = request.query_params.get("cursor")
    if cursor == "":
        raise CompanionGovernanceValidationError()
    raw_limit = request.query_params.get("limit", "50")
    try:
        if (
            not raw_limit
            or not raw_limit.isascii()
            or not raw_limit.isdecimal()
        ):
            raise ValueError
        limit = int(raw_limit)
        if str(limit) != raw_limit or not 1 <= limit <= 100:
            raise ValueError
    except ValueError:
        raise CompanionGovernanceValidationError() from None
    return status, cursor, limit


def _validation_error_response(request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_FAILED",
                "message": "Request validation failed.",
                "request_id": request_id_for(request),
            }
        },
        headers={"Cache-Control": "no-store"},
    )


def _governance_error_response(
    request: Request,
    code: CompanionGovernanceErrorCode,
) -> JSONResponse:
    status, public_code, message = _ERRORS[code]
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": public_code,
                "message": message,
                "request_id": request_id_for(request),
            }
        },
        headers={"Cache-Control": "no-store"},
    )


__all__ = ["FT013RawPathCanonicalityMiddleware", "router"]
