from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from ..access_admin.actor_context import ActorContext
from ..access_admin.dependencies import require_actor_context
from ..access_admin.errors import request_id_for
from ..plant_state import PlantStateError, PlantStateErrorCode, PlantStateTrustService


router = APIRouter(prefix="/api", tags=["plant-state"])


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class PlantStateRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_record_id: uuid.UUID
    plant_id: uuid.UUID
    record_kind: Literal["vision_observation", "plant_state_assessment"]
    agent_id: Literal["vision_observation", "plant_state"]
    observation_key: Literal[
        "image_quality",
        "leaf_color_change",
        "leaf_spots",
        "wilting",
        "growth_change",
        "root_color_change",
        "root_damage",
        "other_visible_change",
    ]
    polarity: Literal["present", "absent", "uncertain", "not_assessable"] | None
    severity: Literal["none", "mild", "moderate", "strong", "unknown"] | None
    assessment_kind: Literal["trend", "conflict", "unknown"] | None
    direction: Literal[
        "increasing", "decreasing", "stable", "mixed", "not_applicable"
    ] | None
    summary: str
    confidence: float
    trust_status: Literal[
        "unknown", "observed", "hypothesis", "conflicting", "confirmed", "rejected"
    ]
    source_refs: list[str]
    observed_at: datetime
    recorded_at: datetime
    confirmation_source: Literal[
        "human_review", "manual_measurement", "follow_up"
    ] | None
    confirmed_at: datetime | None
    version: int


class PlantStateRecordListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PlantStateRecordResponse]
    next_cursor: str | None


class PlantStateReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["confirm", "reject"]
    expected_version: int = Field(ge=1)


@dataclass(frozen=True, slots=True)
class _ErrorDefinition:
    status_code: int
    message: str


_ERRORS = {
    PlantStateErrorCode.AUTH_PLANT_FORBIDDEN: _ErrorDefinition(
        404, "Plant is not available."
    ),
    PlantStateErrorCode.PLANT_STATE_NOT_FOUND: _ErrorDefinition(
        404, "Plant state record is not available."
    ),
    PlantStateErrorCode.PLANT_STATE_CONFLICT_UNRESOLVED: _ErrorDefinition(
        409, "Plant state conflict must be resolved explicitly."
    ),
    PlantStateErrorCode.PLANT_STATE_VERSION_CONFLICT: _ErrorDefinition(
        409, "Plant state record changed. Retry with its current version."
    ),
    PlantStateErrorCode.PLANT_STATE_LIMIT_INVALID: _ErrorDefinition(
        422, "Plant state limit is invalid."
    ),
    PlantStateErrorCode.VALIDATION_FAILED: _ErrorDefinition(
        422, "Request validation failed."
    ),
    PlantStateErrorCode.PLANT_STATE_PERSISTENCE_FAILED: _ErrorDefinition(
        500, "Plant state request could not be completed."
    ),
    PlantStateErrorCode.PLANT_STATE_CONTENT_CONFLICT: _ErrorDefinition(
        409, "Plant state content conflicts with an existing message."
    ),
    PlantStateErrorCode.PLANT_STATE_CLASSIFICATION_REQUIRED: _ErrorDefinition(
        409, "A matching safe-information classification is required."
    ),
    PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID: _ErrorDefinition(
        422, "Plant state candidate is invalid."
    ),
}
_ERROR_RESPONSES = {
    401: {"model": ErrorEnvelope},
    403: {"model": ErrorEnvelope},
    404: {"model": ErrorEnvelope},
    409: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
    500: {"model": ErrorEnvelope},
}
_LIST_PARAMETERS = [
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
        "schema": {"type": "integer", "default": 50, "minimum": 1, "maximum": 100},
    },
]


@router.get(
    "/plants/{plant_id}/state-records",
    response_model=PlantStateRecordListResponse,
    responses=_ERROR_RESPONSES,
    openapi_extra={"parameters": _LIST_PARAMETERS},
)
def list_plant_state_records(
    plant_id: uuid.UUID,
    request: Request,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
) -> PlantStateRecordListResponse | JSONResponse:
    try:
        cursor, limit = _list_query(request)
        with request.app.state.database.session() as session:
            page = PlantStateTrustService(session).list_records(
                actor,
                plant_id=plant_id,
                cursor=cursor,
                limit=limit,
            )
    except PlantStateError as error:
        return _error_response(request, error.code)
    except Exception:
        return _error_response(
            request,
            PlantStateErrorCode.PLANT_STATE_PERSISTENCE_FAILED,
        )
    response.headers["Cache-Control"] = "no-store"
    return PlantStateRecordListResponse(
        items=[PlantStateRecordResponse(**item.as_value()) for item in page.items],
        next_cursor=page.next_cursor,
    )


@router.post(
    "/plants/{plant_id}/state-records/{state_record_id}/review",
    response_model=PlantStateRecordResponse,
    responses=_ERROR_RESPONSES,
)
def review_plant_state_record(
    plant_id: uuid.UUID,
    state_record_id: uuid.UUID,
    payload: PlantStateReviewRequest,
    request: Request,
    response: Response,
    actor: ActorContext = Depends(require_actor_context),
) -> PlantStateRecordResponse | JSONResponse:
    try:
        if request.query_params:
            raise PlantStateError(PlantStateErrorCode.VALIDATION_FAILED)
        with request.app.state.database.session() as session:
            item = PlantStateTrustService(session).review_record(
                actor,
                plant_id=plant_id,
                state_record_id=state_record_id,
                expected_version=payload.expected_version,
                decision=payload.decision,
            )
    except PlantStateError as error:
        return _error_response(request, error.code)
    except Exception:
        return _error_response(
            request,
            PlantStateErrorCode.PLANT_STATE_PERSISTENCE_FAILED,
        )
    response.headers["Cache-Control"] = "no-store"
    return PlantStateRecordResponse(**item.as_value())


def _list_query(request: Request) -> tuple[str | None, int]:
    if any(key not in {"cursor", "limit"} for key in request.query_params.keys()):
        raise PlantStateError(PlantStateErrorCode.VALIDATION_FAILED)
    if any(len(request.query_params.getlist(key)) > 1 for key in ("cursor", "limit")):
        raise PlantStateError(PlantStateErrorCode.VALIDATION_FAILED)
    cursor = request.query_params.get("cursor")
    raw_limit = request.query_params.get("limit")
    if raw_limit is None:
        return cursor, 50
    if (
        not raw_limit
        or raw_limit.strip() != raw_limit
        or not raw_limit.isascii()
        or not raw_limit.isdecimal()
    ):
        raise PlantStateError(PlantStateErrorCode.PLANT_STATE_LIMIT_INVALID)
    limit = int(raw_limit)
    if raw_limit != str(limit) or not 1 <= limit <= 100:
        raise PlantStateError(PlantStateErrorCode.PLANT_STATE_LIMIT_INVALID)
    return cursor, limit


def _error_response(request: Request, code: PlantStateErrorCode) -> JSONResponse:
    definition = _ERRORS[code]
    return JSONResponse(
        status_code=definition.status_code,
        content={
            "error": {
                "code": code.value,
                "message": definition.message,
                "request_id": request_id_for(request),
            }
        },
        headers={"Cache-Control": "no-store"},
    )


__all__ = ["router"]
