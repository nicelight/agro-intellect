from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from ..access_admin.actor_context import ActorContext
from ..access_admin.dependencies import (
    AuthorizedPlantRequest,
    require_plant_permission,
)
from ..access_admin.errors import request_id_for
from ..access_admin.permissions import OperationKind
from ..plant_operations import (
    CheckInResult,
    FreshnessProjection,
    ManualMeasurement,
    ManualMeasurementInput,
    PlantOperationError,
    PlantOperationErrorCode,
    PlantOperationsService,
)
from ..timeline import TimelineJsonlAppender


router = APIRouter(prefix="/api", tags=["plant-operations"])


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class ManualMeasurementPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    measured_at: datetime | None = None
    ph: object | None = None
    ec_ms_cm: object | None = None
    provenance_note: str | None = None


class CheckInCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_at: datetime | None = None
    observation_state: Literal["observed", "no_observation_provided"] | None = None
    observation_text: str | None = None
    measurement: ManualMeasurementPayload | None = None


class ManualMeasurementCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    measured_at: datetime | None = None
    ph: object | None = None
    ec_ms_cm: object | None = None
    provenance_note: str | None = None


class CheckInPromptResponse(BaseModel):
    plant_id: uuid.UUID
    prompt: str
    photo_upload_available: bool


class FreshnessProjectionResponse(BaseModel):
    latest_ph_ref: uuid.UUID | None
    latest_ec_ref: uuid.UUID | None
    latest_ph: Decimal | None
    latest_ec_ms_cm: Decimal | None
    ph_fresh_for_analysis: bool
    ec_fresh_for_analysis: bool
    ph_fresh_for_approval_input: bool
    ec_fresh_for_approval_input: bool
    missing_or_stale: list[str]
    computed_at: datetime


class CheckInSummary(BaseModel):
    check_in_id: uuid.UUID
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    observation_state: Literal["observed", "no_observation_provided"]
    observation_text: str | None
    observed_at: datetime
    recorded_at: datetime
    measurement_refs: list[uuid.UUID]
    event_refs: dict[str, dict[str, object]]
    freshness: FreshnessProjectionResponse
    photo_upload_available: bool


class MeasurementSummary(BaseModel):
    measurement_id: uuid.UUID
    check_in_id: uuid.UUID | None
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    ph: Decimal | None
    ec_ms_cm: Decimal | None
    measured_at: datetime
    recorded_at: datetime
    provenance_note: str | None
    trust_status: Literal["confirmed"]
    event_refs: dict[str, dict[str, object]]


@dataclass(frozen=True, slots=True)
class _OperationErrorDefinition:
    status_code: int
    message: str


_ERROR_DEFINITIONS = {
    PlantOperationErrorCode.AUTH_PLANT_FORBIDDEN: _OperationErrorDefinition(
        404,
        "Plant is not available.",
    ),
    PlantOperationErrorCode.CHECK_IN_EMPTY: _OperationErrorDefinition(
        422,
        "Check-in must include an observation or measurement.",
    ),
    PlantOperationErrorCode.OBSERVATION_TEXT_REQUIRED: _OperationErrorDefinition(
        422,
        "Observation text is required.",
    ),
    PlantOperationErrorCode.OBSERVATION_TEXT_FORBIDDEN: _OperationErrorDefinition(
        422,
        "Observation text is not allowed for this observation state.",
    ),
    PlantOperationErrorCode.MEASUREMENT_VALUE_REQUIRED: _OperationErrorDefinition(
        422,
        "Measurement must include pH or EC.",
    ),
    PlantOperationErrorCode.PH_INVALID: _OperationErrorDefinition(
        422,
        "pH value is invalid.",
    ),
    PlantOperationErrorCode.EC_INVALID: _OperationErrorDefinition(
        422,
        "EC value is invalid.",
    ),
    PlantOperationErrorCode.TIMELINE_APPEND_FAILED: _OperationErrorDefinition(
        500,
        "Plant operation audit trail could not be recorded.",
    ),
    PlantOperationErrorCode.OPERATION_PERSISTENCE_FAILED: _OperationErrorDefinition(
        500,
        "Plant operation could not be completed.",
    ),
    PlantOperationErrorCode.VALIDATION_FAILED: _OperationErrorDefinition(
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
_normal_read = require_plant_permission(OperationKind.NORMAL_READ)
_operate = require_plant_permission(OperationKind.OPERATE)


@router.get(
    "/plants/{plant_id}/operations/check-in-prompt",
    response_model=CheckInPromptResponse,
    responses=_ERROR_RESPONSES,
)
def get_check_in_prompt(
    plant_id: uuid.UUID,
    response: Response,
    _authorized: AuthorizedPlantRequest = Depends(_normal_read),
) -> CheckInPromptResponse:
    _no_store(response)
    return CheckInPromptResponse(
        plant_id=plant_id,
        prompt="Record today's observation and optional pH/EC measurement.",
        photo_upload_available=False,
    )


@router.post(
    "/plants/{plant_id}/operations/check-ins",
    response_model=CheckInSummary,
    status_code=201,
    responses=_ERROR_RESPONSES,
)
def create_check_in(
    plant_id: uuid.UUID,
    payload: CheckInCreateRequest,
    response: Response,
    request: Request,
    authorized: AuthorizedPlantRequest = Depends(_operate),
) -> CheckInSummary | JSONResponse:
    result = _run_operation(
        request,
        authorized.actor,
        lambda service, actor: service.create_check_in(
            actor,
            plant_id=plant_id,
            observation_state=payload.observation_state,
            observation_text=payload.observation_text,
            observed_at=payload.observed_at,
            measurement=_measurement_input(payload.measurement)
            if payload.measurement is not None
            else None,
        ),
    )
    if isinstance(result, JSONResponse):
        return result
    _no_store(response)
    return _check_in_summary(result)


@router.post(
    "/plants/{plant_id}/operations/measurements",
    response_model=MeasurementSummary,
    status_code=201,
    responses=_ERROR_RESPONSES,
)
def create_measurement(
    plant_id: uuid.UUID,
    payload: ManualMeasurementCreateRequest,
    response: Response,
    request: Request,
    authorized: AuthorizedPlantRequest = Depends(_operate),
) -> MeasurementSummary | JSONResponse:
    result = _run_operation(
        request,
        authorized.actor,
        lambda service, actor: service.create_manual_measurement(
            actor,
            plant_id=plant_id,
            measurement=_measurement_input(payload),
        ),
    )
    if isinstance(result, JSONResponse):
        return result
    _no_store(response)
    return _measurement_summary(result.measurement)


@router.get(
    "/plants/{plant_id}/operations/measurements/latest",
    response_model=FreshnessProjectionResponse,
    responses=_ERROR_RESPONSES,
)
def latest_measurements(
    plant_id: uuid.UUID,
    response: Response,
    request: Request,
    purpose: Literal["analysis", "approval_input"] = "analysis",
    authorized: AuthorizedPlantRequest = Depends(_normal_read),
) -> FreshnessProjectionResponse | JSONResponse:
    result = _run_operation(
        request,
        authorized.actor,
        lambda service, actor: service.latest_measurements(
            actor,
            plant_id=plant_id,
            purpose=purpose,
        ),
    )
    if isinstance(result, JSONResponse):
        return result
    _no_store(response)
    return _freshness_response(result)


def _run_operation(request: Request, actor: ActorContext, command):
    try:
        with request.app.state.database.session() as session:
            service = PlantOperationsService(
                session,
                timeline_append=TimelineJsonlAppender(request.app.state.settings),
            )
            return command(service, actor)
    except PlantOperationError as error:
        return _operation_error_response(request, error.code)
    except Exception:
        return _operation_error_response(
            request,
            PlantOperationErrorCode.OPERATION_PERSISTENCE_FAILED,
        )


def _operation_error_response(
    request: Request,
    code: PlantOperationErrorCode,
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


def _measurement_input(
    payload: ManualMeasurementPayload | ManualMeasurementCreateRequest,
) -> ManualMeasurementInput:
    return ManualMeasurementInput(
        ph=payload.ph,
        ec_ms_cm=payload.ec_ms_cm,
        measured_at=payload.measured_at,
        provenance_note=payload.provenance_note,
    )


def _check_in_summary(result: CheckInResult) -> CheckInSummary:
    return CheckInSummary(
        check_in_id=result.check_in.check_in_id,
        farm_id=result.check_in.farm_id,
        plant_id=result.check_in.plant_id,
        observation_state=result.check_in.observation_state,
        observation_text=result.check_in.observation_text,
        observed_at=_timestamp(result.check_in.observed_at),
        recorded_at=_timestamp(result.check_in.recorded_at),
        measurement_refs=[item.measurement_id for item in result.measurements],
        event_refs=_event_refs(result.check_in.event_refs),
        freshness=_freshness_response(result.freshness),
        photo_upload_available=False,
    )


def _measurement_summary(measurement: ManualMeasurement) -> MeasurementSummary:
    return MeasurementSummary(
        measurement_id=measurement.measurement_id,
        check_in_id=measurement.check_in_id,
        farm_id=measurement.farm_id,
        plant_id=measurement.plant_id,
        ph=measurement.ph,
        ec_ms_cm=measurement.ec_ms_cm,
        measured_at=_timestamp(measurement.measured_at),
        recorded_at=_timestamp(measurement.recorded_at),
        provenance_note=measurement.provenance_note,
        trust_status=measurement.trust_status,
        event_refs=_event_refs(measurement.event_refs),
    )


def _freshness_response(
    projection: FreshnessProjection,
) -> FreshnessProjectionResponse:
    return FreshnessProjectionResponse(
        latest_ph_ref=projection.latest_ph_ref,
        latest_ec_ref=projection.latest_ec_ref,
        latest_ph=projection.latest_ph,
        latest_ec_ms_cm=projection.latest_ec_ms_cm,
        ph_fresh_for_analysis=projection.ph_fresh_for_analysis,
        ec_fresh_for_analysis=projection.ec_fresh_for_analysis,
        ph_fresh_for_approval_input=projection.ph_fresh_for_approval_input,
        ec_fresh_for_approval_input=projection.ec_fresh_for_approval_input,
        missing_or_stale=projection.missing_or_stale,
        computed_at=_timestamp(projection.computed_at),
    )


def _event_refs(value: object) -> dict[str, dict[str, object]]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, dict[str, object]] = {}
    for key, item in value.items():
        if isinstance(item, dict):
            result[str(key)] = item
    return result


def _timestamp(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


__all__ = ["router"]
