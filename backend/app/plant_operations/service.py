from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import StrEnum
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.permissions import (
    MembershipStatus,
    OperationKind,
    PermissionSource,
    PlantPermissionContext,
    PlantStatus,
    RolePreset,
    _BoundedPlantPermissionResolver,
)
from ..dataset_governance import (
    DatasetGovernanceError,
    DatasetGovernanceErrorCode,
    DatasetGovernanceService,
    SourceKind,
    record_dataset_evidence,
)
from ..timeline import TimelineEvent, TimelineJsonlAppender
from .models import DailyCheckIn, ManualMeasurement
from .repository import PlantOperationsRepository


class PlantOperationErrorCode(StrEnum):
    AUTH_PLANT_FORBIDDEN = "AUTH_PLANT_FORBIDDEN"
    CHECK_IN_EMPTY = "CHECK_IN_EMPTY"
    OBSERVATION_TEXT_REQUIRED = "OBSERVATION_TEXT_REQUIRED"
    OBSERVATION_TEXT_FORBIDDEN = "OBSERVATION_TEXT_FORBIDDEN"
    OBSERVATION_TEXT_TOO_LONG = "OBSERVATION_TEXT_TOO_LONG"
    MEASUREMENT_VALUE_REQUIRED = "MEASUREMENT_VALUE_REQUIRED"
    PH_INVALID = "PH_INVALID"
    EC_INVALID = "EC_INVALID"
    TIMELINE_APPEND_FAILED = "TIMELINE_APPEND_FAILED"
    OPERATION_DATASET_AUDIT_FAILED = "OPERATION_DATASET_AUDIT_FAILED"
    OPERATION_PERSISTENCE_FAILED = "OPERATION_PERSISTENCE_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class PlantOperationError(RuntimeError):
    def __init__(self, code: PlantOperationErrorCode) -> None:
        self.code = code
        super().__init__(f"Plant operation failed: {code.value}.")


@dataclass(frozen=True, slots=True)
class ManualMeasurementInput:
    ph: object = None
    ec_ms_cm: object = None
    measured_at: datetime | None = None
    provenance_note: str | None = None


@dataclass(frozen=True, slots=True)
class FreshnessProjection:
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


@dataclass(frozen=True, slots=True)
class CheckInResult:
    check_in: DailyCheckIn
    measurements: tuple[ManualMeasurement, ...]
    freshness: FreshnessProjection


@dataclass(frozen=True, slots=True)
class MeasurementResult:
    measurement: ManualMeasurement
    freshness: FreshnessProjection


RepositoryFactory = Callable[[Session], PlantOperationsRepository]
TimelineAppender = Callable[[TimelineEvent], dict[str, object]]


class PlantOperationsService:
    def __init__(
        self,
        session: Session,
        *,
        repository_factory: RepositoryFactory = PlantOperationsRepository,
        timeline_append: TimelineAppender | None = None,
        dataset_governance: DatasetGovernanceService | None = None,
    ) -> None:
        self._session = session
        self._repository_factory = repository_factory
        self._timeline_append = timeline_append or TimelineJsonlAppender()
        self._dataset_governance = dataset_governance

    def create_check_in(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        observation_state: str | None,
        observation_text: str | None = None,
        observed_at: datetime | None = None,
        measurement: ManualMeasurementInput | None = None,
    ) -> CheckInResult:
        measurement_values = (
            _validated_measurement(measurement) if measurement is not None else None
        )
        normalized_observation_state, normalized_observation_text = (
            _validated_observation(
                observation_state,
                observation_text,
                has_measurement=measurement_values is not None,
            )
        )
        observed = _aware_timestamp(observed_at, default=_now())

        def command(repository: PlantOperationsRepository) -> CheckInResult:
            permission = _require_permission(
                repository,
                actor,
                plant_id=plant_id,
                operation=OperationKind.OPERATE,
            )
            recorded_at = _now()
            source_refs = _source_refs(actor, permission)
            check_in = DailyCheckIn(
                check_in_id=uuid.uuid4(),
                farm_id=actor.farm_id,
                plant_id=plant_id,
                actor_account_id=actor.account_id,
                actor_membership_id=actor.membership_id,
                check_in_state="completed",
                observed_at=observed,
                recorded_at=recorded_at,
                observation_state=normalized_observation_state,
                observation_text=normalized_observation_text,
                source_refs=source_refs,
                event_refs={},
            )
            repository.add_check_in(check_in)

            measurements: list[ManualMeasurement] = []
            if measurement_values is not None:
                measurements.append(
                    _build_measurement(
                        actor=actor,
                        permission=permission,
                        plant_id=plant_id,
                        check_in_id=check_in.check_in_id,
                        values=measurement_values,
                        recorded_at=recorded_at,
                    )
                )
                repository.add_measurement(measurements[0])
            repository.flush()

            check_in.event_refs = {
                "daily_checkin_recorded": _append_event(
                    self._timeline_append,
                    _check_in_event(check_in, measurements, source_refs),
                )
            }
            for item in measurements:
                item.event_refs = {
                    "manual_measurement_recorded": _append_event(
                        self._timeline_append,
                        _measurement_event(item, source_refs),
                    )
                }
            repository.flush()
            for item in measurements:
                record_dataset_evidence(
                    self._dataset_governance,
                    session=self._session,
                    timeline_appender=self._timeline_append,
                    actor=actor,
                    plant_id=plant_id,
                    source_kind=SourceKind.MANUAL_MEASUREMENT,
                    source_ref=item.measurement_id,
                )
            record_dataset_evidence(
                self._dataset_governance,
                session=self._session,
                timeline_appender=self._timeline_append,
                actor=actor,
                plant_id=plant_id,
                source_kind=SourceKind.DAILY_CHECK_IN,
                source_ref=check_in.check_in_id,
            )
            freshness = _freshness_projection(
                repository,
                farm_id=actor.farm_id,
                plant_id=plant_id,
                purpose="analysis",
            )
            return CheckInResult(
                check_in=check_in,
                measurements=tuple(measurements),
                freshness=freshness,
            )

        return self._run(command)

    def create_manual_measurement(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        measurement: ManualMeasurementInput,
    ) -> MeasurementResult:
        values = _validated_measurement(measurement)

        def command(repository: PlantOperationsRepository) -> MeasurementResult:
            permission = _require_permission(
                repository,
                actor,
                plant_id=plant_id,
                operation=OperationKind.OPERATE,
            )
            recorded_at = _now()
            source_refs = _source_refs(actor, permission)
            row = _build_measurement(
                actor=actor,
                permission=permission,
                plant_id=plant_id,
                check_in_id=None,
                values=values,
                recorded_at=recorded_at,
            )
            repository.add_measurement(row)
            repository.flush()
            row.event_refs = {
                "manual_measurement_recorded": _append_event(
                    self._timeline_append,
                    _measurement_event(row, source_refs),
                )
            }
            repository.flush()
            record_dataset_evidence(
                self._dataset_governance,
                session=self._session,
                timeline_appender=self._timeline_append,
                actor=actor,
                plant_id=plant_id,
                source_kind=SourceKind.MANUAL_MEASUREMENT,
                source_ref=row.measurement_id,
            )
            return MeasurementResult(
                measurement=row,
                freshness=_freshness_projection(
                    repository,
                    farm_id=actor.farm_id,
                    plant_id=plant_id,
                    purpose="analysis",
                ),
            )

        return self._run(command)

    def latest_measurements(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        purpose: str = "analysis",
    ) -> FreshnessProjection:
        normalized_purpose = _freshness_purpose(purpose)

        def command(repository: PlantOperationsRepository) -> FreshnessProjection:
            _require_permission(
                repository,
                actor,
                plant_id=plant_id,
                operation=OperationKind.NORMAL_READ,
            )
            return _freshness_projection(
                repository,
                farm_id=actor.farm_id,
                plant_id=plant_id,
                purpose=normalized_purpose,
            )

        return self._run(command)

    def _run(self, command):
        try:
            with self._session.begin():
                return command(self._repository_factory(self._session))
        except PlantOperationError:
            raise
        except IntegrityError:
            raise PlantOperationError(
                PlantOperationErrorCode.OPERATION_PERSISTENCE_FAILED
            ) from None
        except DatasetGovernanceError as error:
            if error.code is DatasetGovernanceErrorCode.AUDIT_FAILED:
                raise PlantOperationError(
                    PlantOperationErrorCode.OPERATION_DATASET_AUDIT_FAILED
                ) from None
            raise PlantOperationError(
                PlantOperationErrorCode.OPERATION_PERSISTENCE_FAILED
            ) from None
        except Exception:
            raise PlantOperationError(
                PlantOperationErrorCode.OPERATION_PERSISTENCE_FAILED
            ) from None


@dataclass(frozen=True, slots=True)
class _MeasurementValues:
    ph: Decimal | None
    ec_ms_cm: Decimal | None
    measured_at: datetime
    provenance_note: str | None


def _require_permission(
    repository: PlantOperationsRepository,
    actor: ActorContext,
    *,
    plant_id: uuid.UUID,
    operation: OperationKind,
) -> PlantPermissionContext:
    if not isinstance(plant_id, uuid.UUID):
        raise PlantOperationError(PlantOperationErrorCode.VALIDATION_FAILED)
    identity = repository.lock_actor_identity(
        account_id=actor.account_id,
        membership_id=actor.membership_id,
        farm_id=actor.farm_id,
    )
    if identity is None:
        raise PlantOperationError(PlantOperationErrorCode.AUTH_PLANT_FORBIDDEN)
    account, membership = identity
    if (
        account.account_status != "active"
        or membership.membership_status != MembershipStatus.ACTIVE.value
        or membership.account_id != actor.account_id
        or membership.role_preset != actor.role_preset.value
    ):
        raise PlantOperationError(PlantOperationErrorCode.AUTH_PLANT_FORBIDDEN)

    resolver = _BoundedPlantPermissionResolver(
        farm_id=actor.farm_id,
        membership_id=actor.membership_id,
        membership_status=actor.membership_status,
        role_preset=actor.role_preset,
        snapshot_provider=repository.lock_plant_access_snapshot,
    )
    permission = resolver.resolve(plant_id, operation)
    allowed = (
        permission.plant_status is PlantStatus.ACTIVE
        and (
            permission.can_operate
            if operation is OperationKind.OPERATE
            else permission.can_read
        )
    )
    if not allowed:
        raise PlantOperationError(PlantOperationErrorCode.AUTH_PLANT_FORBIDDEN)
    return permission


def _validated_observation(
    observation_state: str | None,
    observation_text: str | None,
    *,
    has_measurement: bool,
) -> tuple[str, str | None]:
    if observation_state is None:
        if observation_text is not None:
            raise PlantOperationError(PlantOperationErrorCode.VALIDATION_FAILED)
        if not has_measurement:
            raise PlantOperationError(PlantOperationErrorCode.CHECK_IN_EMPTY)
        return "no_observation_provided", None
    try:
        state = str(observation_state)
    except Exception:
        raise PlantOperationError(PlantOperationErrorCode.VALIDATION_FAILED) from None
    if state not in {"observed", "no_observation_provided"}:
        raise PlantOperationError(PlantOperationErrorCode.VALIDATION_FAILED)
    text = observation_text.strip() if isinstance(observation_text, str) else None
    if state == "observed":
        if not text:
            raise PlantOperationError(
                PlantOperationErrorCode.OBSERVATION_TEXT_REQUIRED
            )
        if len(text) > 2000:
            raise PlantOperationError(
                PlantOperationErrorCode.OBSERVATION_TEXT_TOO_LONG
            )
        return state, text
    if text:
        raise PlantOperationError(PlantOperationErrorCode.OBSERVATION_TEXT_FORBIDDEN)
    return state, None


def _validated_measurement(
    measurement: ManualMeasurementInput,
) -> _MeasurementValues:
    if not isinstance(measurement, ManualMeasurementInput):
        raise PlantOperationError(PlantOperationErrorCode.VALIDATION_FAILED)
    ph = _decimal_value(
        measurement.ph,
        code=PlantOperationErrorCode.PH_INVALID,
        minimum=Decimal("0"),
        maximum=Decimal("14"),
        quantum=Decimal("0.01"),
    )
    ec = _decimal_value(
        measurement.ec_ms_cm,
        code=PlantOperationErrorCode.EC_INVALID,
        minimum=Decimal("0"),
        maximum=None,
        quantum=Decimal("0.001"),
    )
    if ph is None and ec is None:
        raise PlantOperationError(PlantOperationErrorCode.MEASUREMENT_VALUE_REQUIRED)
    note = measurement.provenance_note.strip() if measurement.provenance_note else None
    return _MeasurementValues(
        ph=ph,
        ec_ms_cm=ec,
        measured_at=_aware_timestamp(measurement.measured_at, default=_now()),
        provenance_note=note or None,
    )


def _decimal_value(
    value: object,
    *,
    code: PlantOperationErrorCode,
    minimum: Decimal,
    maximum: Decimal | None,
    quantum: Decimal,
) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise PlantOperationError(code)
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise PlantOperationError(code) from None
    if not decimal.is_finite() or decimal < minimum:
        raise PlantOperationError(code)
    if maximum is not None and decimal > maximum:
        raise PlantOperationError(code)
    try:
        return decimal.quantize(quantum, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise PlantOperationError(code) from None


def _aware_timestamp(value: datetime | None, *, default: datetime) -> datetime:
    timestamp = default if value is None else value
    if (
        not isinstance(timestamp, datetime)
        or timestamp.tzinfo is None
        or timestamp.utcoffset() is None
    ):
        raise PlantOperationError(PlantOperationErrorCode.VALIDATION_FAILED)
    return timestamp


def _build_measurement(
    *,
    actor: ActorContext,
    permission: PlantPermissionContext,
    plant_id: uuid.UUID,
    check_in_id: uuid.UUID | None,
    values: _MeasurementValues,
    recorded_at: datetime,
) -> ManualMeasurement:
    return ManualMeasurement(
        measurement_id=uuid.uuid4(),
        farm_id=actor.farm_id,
        plant_id=plant_id,
        check_in_id=check_in_id,
        actor_account_id=actor.account_id,
        actor_membership_id=actor.membership_id,
        measured_at=values.measured_at,
        recorded_at=recorded_at,
        ph=values.ph,
        ec_ms_cm=values.ec_ms_cm,
        provenance_note=values.provenance_note,
        source_type="manual_user",
        source_refs=_source_refs(actor, permission),
        trust_status="confirmed",
        event_refs={},
    )


def _append_event(
    timeline_append: TimelineAppender,
    event: TimelineEvent,
) -> dict[str, object]:
    try:
        ref = timeline_append(event)
    except Exception:
        raise PlantOperationError(
            PlantOperationErrorCode.TIMELINE_APPEND_FAILED
        ) from None
    if not _event_ref_shape_is_valid(ref, event.event_type):
        raise PlantOperationError(PlantOperationErrorCode.TIMELINE_APPEND_FAILED)
    return ref


def _event_ref_shape_is_valid(ref: object, event_type: str) -> bool:
    if not isinstance(ref, dict) or ref.get("event_type") != event_type:
        return False
    try:
        uuid.UUID(str(ref["timeline_event_id"]))
    except (KeyError, TypeError, ValueError):
        return False
    return (
        isinstance(ref.get("timeline_ref"), str)
        and str(ref["timeline_ref"]).startswith("timeline.jsonl#")
        and isinstance(ref.get("created_at"), str)
    )


def _check_in_event(
    check_in: DailyCheckIn,
    measurements: list[ManualMeasurement],
    source_refs: dict[str, object],
) -> TimelineEvent:
    return TimelineEvent(
        farm_id=check_in.farm_id,
        plant_id=check_in.plant_id,
        actor_ref=_actor_ref(source_refs),
        event_type="daily_checkin_recorded",
        source_type="daily_checkin",
        source_id=check_in.check_in_id,
        source_refs=source_refs,
        payload_summary={
            "observation_state": check_in.observation_state,
            "observed_at": check_in.observed_at,
            "recorded_at": check_in.recorded_at,
            "measurement_refs": [
                str(item.measurement_id) for item in measurements
            ],
            "source_refs": source_refs,
        },
    )


def _measurement_event(
    measurement: ManualMeasurement,
    source_refs: dict[str, object],
) -> TimelineEvent:
    payload: dict[str, object] = {
        "check_in_id": str(measurement.check_in_id)
        if measurement.check_in_id is not None
        else None,
        "measured_at": measurement.measured_at,
        "recorded_at": measurement.recorded_at,
        "has_ph": measurement.ph is not None,
        "has_ec": measurement.ec_ms_cm is not None,
        "trust_status": measurement.trust_status,
        "source_refs": source_refs,
    }
    if measurement.ph is not None:
        payload["ph"] = measurement.ph
    if measurement.ec_ms_cm is not None:
        payload["ec_ms_cm"] = measurement.ec_ms_cm
    if measurement.provenance_note:
        payload["provenance_note"] = measurement.provenance_note
    return TimelineEvent(
        farm_id=measurement.farm_id,
        plant_id=measurement.plant_id,
        actor_ref=_actor_ref(source_refs),
        event_type="manual_measurement_recorded",
        source_type="manual_measurement",
        source_id=measurement.measurement_id,
        source_refs=source_refs,
        payload_summary=payload,
    )


def _freshness_projection(
    repository: PlantOperationsRepository,
    *,
    farm_id: uuid.UUID,
    plant_id: uuid.UUID,
    purpose: str,
) -> FreshnessProjection:
    computed_at = _now()
    latest_ph = repository.latest_ph_measurement(farm_id=farm_id, plant_id=plant_id)
    latest_ec = repository.latest_ec_measurement(farm_id=farm_id, plant_id=plant_id)
    ph_analysis = _is_fresh(latest_ph, computed_at, hours=24)
    ec_analysis = _is_fresh(latest_ec, computed_at, hours=24)
    ph_approval = _is_fresh(latest_ph, computed_at, hours=2)
    ec_approval = _is_fresh(latest_ec, computed_at, hours=2)
    if purpose == "analysis":
        missing_or_stale = [
            name
            for name, fresh in (("ph", ph_analysis), ("ec", ec_analysis))
            if not fresh
        ]
    else:
        missing_or_stale = [
            name
            for name, fresh in (("ph", ph_approval), ("ec", ec_approval))
            if not fresh
        ]
    return FreshnessProjection(
        latest_ph_ref=latest_ph.measurement_id if latest_ph is not None else None,
        latest_ec_ref=latest_ec.measurement_id if latest_ec is not None else None,
        latest_ph=latest_ph.ph if latest_ph is not None else None,
        latest_ec_ms_cm=latest_ec.ec_ms_cm if latest_ec is not None else None,
        ph_fresh_for_analysis=ph_analysis,
        ec_fresh_for_analysis=ec_analysis,
        ph_fresh_for_approval_input=ph_approval,
        ec_fresh_for_approval_input=ec_approval,
        missing_or_stale=missing_or_stale,
        computed_at=computed_at,
    )


def _is_fresh(
    measurement: ManualMeasurement | None,
    computed_at: datetime,
    *,
    hours: int,
) -> bool:
    if measurement is None:
        return False
    measured_at = _stored_timestamp(measurement.measured_at)
    return computed_at - timedelta(hours=hours) <= measured_at <= computed_at


def _stored_timestamp(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _freshness_purpose(value: str) -> str:
    if value not in {"analysis", "approval_input"}:
        raise PlantOperationError(PlantOperationErrorCode.VALIDATION_FAILED)
    return value


def _source_refs(
    actor: ActorContext,
    permission: PlantPermissionContext,
) -> dict[str, object]:
    refs: dict[str, object] = {
        "request_id": actor.request_id,
        "account_id": str(actor.account_id),
        "membership_id": str(actor.membership_id),
        "farm_id": str(actor.farm_id),
        "plant_id": str(permission.plant_id),
        "role_preset": _enum_value(actor.role_preset),
        "membership_status": _enum_value(actor.membership_status),
        "permission_source": _enum_value(permission.source),
        "session_id": str(actor.session_id),
    }
    if permission.source is PermissionSource.PLANT_ACCESS_GRANT:
        refs["grant_id"] = str(permission.grant_id)
    return refs


def _actor_ref(source_refs: dict[str, object]) -> dict[str, object]:
    return {
        "account_id": source_refs["account_id"],
        "membership_id": source_refs["membership_id"],
        "role_preset": source_refs["role_preset"],
    }


def _enum_value(value: object) -> str:
    if isinstance(value, StrEnum | RolePreset | MembershipStatus | PermissionSource):
        return value.value
    return str(value)


def _now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "CheckInResult",
    "FreshnessProjection",
    "ManualMeasurementInput",
    "MeasurementResult",
    "PlantOperationError",
    "PlantOperationErrorCode",
    "PlantOperationsService",
]
