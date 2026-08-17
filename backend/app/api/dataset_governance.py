"""Protected read-only Dataset Candidate HTTP boundary for FT-016.

The handler stays transport-only: query parsing, error shaping, and no-store
headers. Business/query ownership (read scope resolution, canonical keyset
pagination, exact safe projection) lives in the Dataset Governance
service/repository. No Dataset mutation endpoint is registered here.
"""

from __future__ import annotations

from typing import Literal
import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from ..access_admin.actor_context import ActorContext
from ..access_admin.dependencies import require_actor_context
from ..access_admin.errors import AuthErrorCode, auth_error_response, request_id_for
from ..dataset_governance import DatasetGovernanceError, DatasetGovernanceErrorCode
from ..dataset_governance.service import DatasetGovernanceService


router = APIRouter(prefix="/api", tags=["dataset-governance"])


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class EvidenceRefV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "photo",
        "check_in",
        "measurement",
        "follow_up_outcome",
        "review",
        "observation",
    ]
    ref: str


class DatasetCandidateItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: uuid.UUID
    plant_id: uuid.UUID
    source_kind: Literal[
        "photo_catalog_item",
        "daily_check_in",
        "manual_measurement",
        "follow_up_outcome",
    ]
    source_ref: uuid.UUID
    candidate_status: Literal[
        "candidate",
        "needs_review",
        "confirmed",
        "rejected",
        "excluded",
    ]
    quality_tier: Literal["standard", "gold"]
    split: Literal["train", "eval", "holdout"] | None
    confirmation_source: Literal[
        "curator_auto",
        "human_review",
        "expert_review",
        "batch_review",
    ] | None
    evidence_refs: list[EvidenceRefV1]
    curator_decision: Literal["selected", "deferred", "rejected"] | None
    corrected: bool
    follow_up_seen: bool
    can_train_on: bool
    record_version: int
    created_at: str
    updated_at: str


class DatasetCandidateListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    items: list[DatasetCandidateItemResponse]
    next_cursor: str | None


_ERROR_RESPONSES = {
    401: {"model": ErrorEnvelope},
    403: {"model": ErrorEnvelope},
    404: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
    500: {"model": ErrorEnvelope},
}
_QUERY_PARAMETERS = [
    {
        "name": "cursor",
        "in": "query",
        "required": False,
        "schema": {"type": "string"},
        "description": "Opaque canonical continuation cursor from a previous "
        "Dataset Candidate page.",
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
        "description": "Page size for Dataset Candidates.",
    },
]


@router.get(
    "/plants/{plant_id}/dataset-candidates",
    response_model=DatasetCandidateListResponse,
    responses=_ERROR_RESPONSES,
    openapi_extra={"parameters": _QUERY_PARAMETERS},
)
def list_dataset_candidates(
    plant_id: uuid.UUID,
    request: Request,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
) -> DatasetCandidateListResponse | JSONResponse:
    try:
        cursor, limit = _parse_query(request)
        with request.app.state.database.session() as session:
            page = DatasetGovernanceService(session).list_dataset_candidates(
                actor,
                plant_id=plant_id,
                cursor=cursor,
                limit=limit,
            )
        body = DatasetCandidateListResponse(
            items=[_item_response(item) for item in page.items],
            next_cursor=page.next_cursor,
        )
    except DatasetGovernanceError as error:
        return _error_response(request, error.code)
    except Exception:
        return _error_response(
            request,
            DatasetGovernanceErrorCode.READ_FAILED,
        )
    response.headers["Cache-Control"] = "no-store"
    return body


def _parse_query(request: Request) -> tuple[str | None, int]:
    if any(key not in {"cursor", "limit"} for key in request.query_params):
        raise DatasetGovernanceError(DatasetGovernanceErrorCode.VALIDATION_FAILED)
    cursor_values = request.query_params.getlist("cursor")
    if len(cursor_values) > 1:
        raise DatasetGovernanceError(DatasetGovernanceErrorCode.VALIDATION_FAILED)
    cursor = cursor_values[0] if cursor_values else None
    if cursor == "":
        raise DatasetGovernanceError(DatasetGovernanceErrorCode.CURSOR_INVALID)
    limit = _limit_value(request)
    return cursor, limit


def _limit_value(request: Request) -> int:
    values = request.query_params.getlist("limit")
    if len(values) > 1:
        raise DatasetGovernanceError(DatasetGovernanceErrorCode.VALIDATION_FAILED)
    if not values:
        return 50
    if values[0] == "":
        raise DatasetGovernanceError(DatasetGovernanceErrorCode.LIMIT_INVALID)
    try:
        value = int(values[0])
    except ValueError:
        raise DatasetGovernanceError(
            DatasetGovernanceErrorCode.LIMIT_INVALID
        ) from None
    if not 1 <= value <= 100:
        raise DatasetGovernanceError(DatasetGovernanceErrorCode.LIMIT_INVALID)
    return value


def _item_response(item) -> DatasetCandidateItemResponse:
    return DatasetCandidateItemResponse(
        candidate_id=item.candidate_id,
        plant_id=item.plant_id,
        source_kind=item.source_kind,
        source_ref=item.source_ref,
        candidate_status=item.candidate_status,
        quality_tier=item.quality_tier,
        split=item.split,
        confirmation_source=item.confirmation_source,
        evidence_refs=[EvidenceRefV1(**ref) for ref in item.evidence_refs],
        curator_decision=item.curator_decision,
        corrected=item.corrected,
        follow_up_seen=item.follow_up_seen,
        can_train_on=item.can_train_on,
        record_version=item.record_version,
        created_at=_timestamp(item.created_at),
        updated_at=_timestamp(item.updated_at),
    )


def _timestamp(value) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _error_response(
    request: Request,
    code: DatasetGovernanceErrorCode | AuthErrorCode,
) -> JSONResponse:
    if code == DatasetGovernanceErrorCode.CONTEXT_FORBIDDEN:
        return auth_error_response(request, AuthErrorCode.PLANT_FORBIDDEN)
    status, message = _ERROR_MESSAGES.get(code, (500, "Dataset candidates could not be read."))
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code.value,
                "message": message,
                "request_id": request_id_for(request),
            }
        },
        headers={"Cache-Control": "no-store"},
    )


_ERROR_MESSAGES = {
    DatasetGovernanceErrorCode.CURSOR_INVALID: (422, "Dataset cursor is invalid."),
    DatasetGovernanceErrorCode.LIMIT_INVALID: (422, "Dataset limit is invalid."),
    DatasetGovernanceErrorCode.VALIDATION_FAILED: (
        422,
        "Request validation failed.",
    ),
    DatasetGovernanceErrorCode.READ_FAILED: (
        500,
        "Dataset candidates could not be read.",
    ),
    DatasetGovernanceErrorCode.INTERNAL_ERROR: (
        500,
        "Dataset candidates could not be read.",
    ),
    DatasetGovernanceErrorCode.PERSISTENCE_FAILED: (
        500,
        "Dataset candidates could not be read.",
    ),
}


__all__ = ["router"]