from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..access_admin.actor_context import ActorContext
from ..access_admin.dependencies import require_actor_context
from ..access_admin.errors import request_id_for
from ..plant_history import (
    ENTRY_SOURCE_TYPES,
    PlantHistoryCard,
    PlantHistoryEntry,
    PlantHistoryError,
    PlantHistoryErrorCode,
    PlantHistoryService,
)


router = APIRouter(prefix="/api", tags=["plant-history"])


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class PlantHistoryCardResponse(BaseModel):
    plant_id: uuid.UUID
    farm_id: uuid.UUID
    plant_key: str
    display_name: str
    status: Literal["active", "archived"]
    permissions: dict[str, object]
    latest_check_in_ref: dict[str, object] | None
    latest_ph_ref: dict[str, object] | None
    latest_ec_ref: dict[str, object] | None
    latest_ph: Decimal | None
    latest_ec_ms_cm: Decimal | None
    ph_fresh_for_analysis: bool
    ec_fresh_for_analysis: bool
    photo_count: int
    history_entry_count: int
    retained_history_mode: Literal["active_history", "archived_retained_history"]
    computed_at: datetime


class PlantHistoryEntryResponse(BaseModel):
    history_entry_id: str
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    source_type: Literal[
        "plant_admin_audit",
        "daily_checkin",
        "manual_measurement",
        "photo_catalog_item",
    ]
    source_id: uuid.UUID
    occurred_at: datetime
    recorded_at: datetime
    actor_ref: dict[str, object] | None
    summary: dict[str, object]
    source_refs: dict[str, object] | list[object]
    event_refs: dict[str, object]
    artifact_refs: dict[str, object]
    authority_source: Literal["postgresql_read_model"]


class PlantHistoryListResponse(BaseModel):
    items: list[PlantHistoryEntryResponse]
    next_cursor: str | None = None


@dataclass(frozen=True, slots=True)
class _HistoryErrorDefinition:
    status_code: int
    message: str


_ERROR_DEFINITIONS = {
    PlantHistoryErrorCode.AUTH_PLANT_FORBIDDEN: _HistoryErrorDefinition(
        404,
        "Plant is not available.",
    ),
    PlantHistoryErrorCode.HISTORY_CURSOR_INVALID: _HistoryErrorDefinition(
        422,
        "History cursor is invalid.",
    ),
    PlantHistoryErrorCode.HISTORY_LIMIT_INVALID: _HistoryErrorDefinition(
        422,
        "History limit is invalid.",
    ),
    PlantHistoryErrorCode.HISTORY_SOURCE_TYPE_INVALID: _HistoryErrorDefinition(
        422,
        "History source type is invalid.",
    ),
    PlantHistoryErrorCode.HISTORY_PERSISTENCE_FAILED: _HistoryErrorDefinition(
        500,
        "Plant history could not be read.",
    ),
    PlantHistoryErrorCode.VALIDATION_FAILED: _HistoryErrorDefinition(
        422,
        "Request validation failed.",
    ),
}

_ERROR_RESPONSES = {
    401: {"model": ErrorEnvelope},
    403: {"model": ErrorEnvelope},
    404: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
    500: {"model": ErrorEnvelope},
}
_HISTORY_QUERY_PARAMETERS = [
    {
        "name": "cursor",
        "in": "query",
        "required": False,
        "schema": {"type": "string"},
        "description": "Opaque cursor returned by a previous Plant history page.",
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
        "description": "Page size for Plant history entries.",
    },
    {
        "name": "source_type",
        "in": "query",
        "required": False,
        "schema": {"type": "string", "enum": sorted(ENTRY_SOURCE_TYPES)},
        "description": "Filter entries by implemented Plant history source type.",
    },
]


@router.get(
    "/plants/{plant_id}/history/card",
    response_model=PlantHistoryCardResponse,
    responses=_ERROR_RESPONSES,
)
def get_history_card(
    plant_id: uuid.UUID,
    response: Response,
    request: Request,
    actor: ActorContext = Depends(require_actor_context),
) -> PlantHistoryCardResponse | JSONResponse:
    try:
        _reject_unknown_query_params(request, allowed=frozenset())
        result = _run_history_read(
            request,
            lambda service: service.get_card(actor, plant_id=plant_id),
        )
    except PlantHistoryError as error:
        return _history_error_response(request, error.code)
    if isinstance(result, JSONResponse):
        return result
    _no_store(response)
    return _card_response(result)


@router.get(
    "/plants/{plant_id}/history",
    response_model=PlantHistoryListResponse,
    responses=_ERROR_RESPONSES,
    openapi_extra={"parameters": _HISTORY_QUERY_PARAMETERS},
)
def list_history(
    plant_id: uuid.UUID,
    response: Response,
    request: Request,
    actor: ActorContext = Depends(require_actor_context),
) -> PlantHistoryListResponse | JSONResponse:
    try:
        cursor, limit, source_type = _parse_history_query(request)
        result = _run_history_read(
            request,
            lambda service: service.list_history(
                actor,
                plant_id=plant_id,
                cursor=cursor,
                limit=limit,
                source_type=source_type,
            ),
        )
    except PlantHistoryError as error:
        return _history_error_response(request, error.code)
    if isinstance(result, JSONResponse):
        return result
    _no_store(response)
    return PlantHistoryListResponse(
        items=[_entry_response(item) for item in result.items],
        next_cursor=result.next_cursor,
    )


def _run_history_read(request: Request, command):
    try:
        with request.app.state.database.session() as session:
            return command(PlantHistoryService(session))
    except PlantHistoryError as error:
        return _history_error_response(request, error.code)
    except Exception:
        return _history_error_response(
            request,
            PlantHistoryErrorCode.HISTORY_PERSISTENCE_FAILED,
        )


def _history_error_response(
    request: Request,
    code: PlantHistoryErrorCode,
) -> JSONResponse:
    definition = _ERROR_DEFINITIONS[code]
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


def _parse_history_query(request: Request) -> tuple[str | None, int, str | None]:
    _reject_unknown_query_params(
        request,
        allowed=frozenset({"cursor", "limit", "source_type"}),
    )
    cursor = _optional_single_query_value(
        request,
        "cursor",
        empty_code=PlantHistoryErrorCode.HISTORY_CURSOR_INVALID,
    )
    source_type = _optional_single_query_value(
        request,
        "source_type",
        empty_code=PlantHistoryErrorCode.HISTORY_SOURCE_TYPE_INVALID,
    )
    return cursor, _limit_value(request), source_type


def _reject_unknown_query_params(
    request: Request,
    *,
    allowed: frozenset[str],
) -> None:
    for key in request.query_params.keys():
        if key not in allowed:
            raise PlantHistoryError(PlantHistoryErrorCode.VALIDATION_FAILED)


def _optional_single_query_value(
    request: Request,
    name: str,
    *,
    empty_code: PlantHistoryErrorCode,
) -> str | None:
    values = request.query_params.getlist(name)
    if len(values) > 1:
        raise PlantHistoryError(PlantHistoryErrorCode.VALIDATION_FAILED)
    if not values:
        return None
    value = values[0]
    if value == "":
        raise PlantHistoryError(empty_code)
    return value


def _limit_value(request: Request) -> int:
    values = request.query_params.getlist("limit")
    if len(values) > 1:
        raise PlantHistoryError(PlantHistoryErrorCode.VALIDATION_FAILED)
    if not values:
        return 50
    if values[0] == "":
        raise PlantHistoryError(PlantHistoryErrorCode.HISTORY_LIMIT_INVALID)
    try:
        return int(values[0])
    except ValueError:
        raise PlantHistoryError(PlantHistoryErrorCode.HISTORY_LIMIT_INVALID) from None


def _card_response(card: PlantHistoryCard) -> PlantHistoryCardResponse:
    return PlantHistoryCardResponse(
        plant_id=card.plant_id,
        farm_id=card.farm_id,
        plant_key=card.plant_key,
        display_name=card.display_name,
        status=card.status,
        permissions=dict(card.permissions),
        latest_check_in_ref=_optional_mapping(card.latest_check_in_ref),
        latest_ph_ref=_optional_mapping(card.latest_ph_ref),
        latest_ec_ref=_optional_mapping(card.latest_ec_ref),
        latest_ph=card.latest_ph,
        latest_ec_ms_cm=card.latest_ec_ms_cm,
        ph_fresh_for_analysis=card.ph_fresh_for_analysis,
        ec_fresh_for_analysis=card.ec_fresh_for_analysis,
        photo_count=card.photo_count,
        history_entry_count=card.history_entry_count,
        retained_history_mode=card.retained_history_mode,
        computed_at=_timestamp(card.computed_at),
    )


def _entry_response(entry: PlantHistoryEntry) -> PlantHistoryEntryResponse:
    return PlantHistoryEntryResponse(
        history_entry_id=entry.history_entry_id,
        farm_id=entry.farm_id,
        plant_id=entry.plant_id,
        source_type=entry.source_type,
        source_id=entry.source_id,
        occurred_at=_timestamp(entry.occurred_at),
        recorded_at=_timestamp(entry.recorded_at),
        actor_ref=_optional_mapping(entry.actor_ref),
        summary=dict(entry.summary),
        source_refs=entry.source_refs,
        event_refs=dict(entry.event_refs),
        artifact_refs=dict(entry.artifact_refs),
        authority_source=entry.authority_source,
    )


def _optional_mapping(value: dict[str, object] | None) -> dict[str, object] | None:
    return dict(value) if value is not None else None


def _timestamp(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


__all__ = ["router"]
