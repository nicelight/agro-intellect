"""Authoritative classified Plant trust persistence and human review service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import base64
import binascii
import json
from typing import Literal
import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.models import (
    Account,
    FarmMembership,
    LocalSession,
    Plant,
    PlantAccessGrant,
)
from ..agent_runtime.contracts import (
    AgentRuntimeValidationError,
    MessageEnvelopeV1,
    RuntimeDecision,
    SafetyClassificationResultV1,
)
from ..photo_intake.models import PhotoCatalogItem
from ..vision_observation.contracts import VisionStateCandidateV1
from .contracts import (
    PlantStateAssessmentCandidateV1,
    validate_structural_assessment,
)
from .models import PlantStateRecord


class PlantStateErrorCode(StrEnum):
    AUTH_PLANT_FORBIDDEN = "AUTH_PLANT_FORBIDDEN"
    PLANT_STATE_NOT_FOUND = "PLANT_STATE_NOT_FOUND"
    PLANT_STATE_CONTENT_CONFLICT = "PLANT_STATE_CONTENT_CONFLICT"
    PLANT_STATE_CLASSIFICATION_REQUIRED = "PLANT_STATE_CLASSIFICATION_REQUIRED"
    PLANT_STATE_CANDIDATE_INVALID = "PLANT_STATE_CANDIDATE_INVALID"
    PLANT_STATE_CONFLICT_UNRESOLVED = "PLANT_STATE_CONFLICT_UNRESOLVED"
    PLANT_STATE_VERSION_CONFLICT = "PLANT_STATE_VERSION_CONFLICT"
    PLANT_STATE_LIMIT_INVALID = "PLANT_STATE_LIMIT_INVALID"
    PLANT_STATE_PERSISTENCE_FAILED = "PLANT_STATE_PERSISTENCE_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class PlantStateError(RuntimeError):
    def __init__(self, code: PlantStateErrorCode) -> None:
        self.code = code
        super().__init__("Plant State operation failed.")


@dataclass(frozen=True, slots=True)
class PlantStateRecordViewV1:
    state_record_id: uuid.UUID
    plant_id: uuid.UUID
    record_kind: str
    agent_id: str
    observation_key: str
    polarity: str | None
    severity: str | None
    assessment_kind: str | None
    direction: str | None
    summary: str
    confidence: float
    trust_status: str
    source_refs: tuple[str, ...]
    observed_at: datetime
    recorded_at: datetime
    confirmation_source: str | None
    confirmed_at: datetime | None
    version: int

    @classmethod
    def from_record(cls, record: PlantStateRecord) -> "PlantStateRecordViewV1":
        return cls(
            state_record_id=record.state_record_id,
            plant_id=record.plant_id,
            record_kind=record.record_kind,
            agent_id=record.agent_id,
            observation_key=record.observation_key,
            polarity=record.polarity,
            severity=record.severity,
            assessment_kind=record.assessment_kind,
            direction=record.direction,
            summary=record.summary,
            confidence=float(record.confidence),
            trust_status=record.trust_status,
            source_refs=tuple(record.source_refs),
            observed_at=_as_utc(record.observed_at),
            recorded_at=_as_utc(record.recorded_at),
            confirmation_source=record.confirmation_source,
            confirmed_at=_as_utc(record.confirmed_at) if record.confirmed_at else None,
            version=record.version,
        )

    def as_value(self) -> dict[str, object]:
        return {
            "state_record_id": str(self.state_record_id),
            "plant_id": str(self.plant_id),
            "record_kind": self.record_kind,
            "agent_id": self.agent_id,
            "observation_key": self.observation_key,
            "polarity": self.polarity,
            "severity": self.severity,
            "assessment_kind": self.assessment_kind,
            "direction": self.direction,
            "summary": self.summary,
            "confidence": self.confidence,
            "trust_status": self.trust_status,
            "source_refs": list(self.source_refs),
            "observed_at": _timestamp(self.observed_at),
            "recorded_at": _timestamp(self.recorded_at),
            "confirmation_source": self.confirmation_source,
            "confirmed_at": _timestamp(self.confirmed_at)
            if self.confirmed_at is not None
            else None,
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class PlantStateRecordPageV1:
    items: tuple[PlantStateRecordViewV1, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class _CurrentAccess:
    role_preset: str
    plant_status: str
    can_read: bool
    can_operate: bool
    permission_source: str
    grant_id: uuid.UUID | None


Candidate = VisionStateCandidateV1 | PlantStateAssessmentCandidateV1


class PlantStateTrustService:
    def __init__(self, session: Session, *, clock=None) -> None:
        self._session = session
        self._clock = clock or _utc_now

    def persist_classified(
        self,
        actor: ActorContext,
        *,
        envelope: MessageEnvelopeV1,
        candidate: Candidate,
        classification: SafetyClassificationResultV1 | object,
    ) -> PlantStateRecordViewV1:
        classification_value = _classification(classification)
        if (
            classification_value is None
            or classification_value.classification != "safe_information"
            or classification_value.message_id != getattr(envelope, "message_id", None)
        ):
            raise PlantStateError(PlantStateErrorCode.PLANT_STATE_CLASSIFICATION_REQUIRED)
        shape = _candidate_shape(envelope, candidate)
        if shape is None:
            raise PlantStateError(PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID)

        with self._session.begin():
            if (
                envelope.farm_id != actor.farm_id
                or envelope.authorization_scope.farm_id != actor.farm_id
                or envelope.authorization_scope.plant_id != envelope.plant_id
            ):
                raise PlantStateError(PlantStateErrorCode.AUTH_PLANT_FORBIDDEN)
            access = _require_current_access(
                self._session,
                actor,
                plant_id=envelope.plant_id,
                mode="active_read",
                clock=self._clock,
                lock=True,
            )
            if (
                envelope.authorization_scope.role_preset != access.role_preset
                or envelope.authorization_scope.permission_source
                != access.permission_source
                or envelope.authorization_scope.grant_id != access.grant_id
            ):
                raise PlantStateError(PlantStateErrorCode.AUTH_PLANT_FORBIDDEN)

            if isinstance(candidate, VisionStateCandidateV1):
                photo_id = _vision_photo_id(candidate.source_refs)
                photo = self._session.scalar(
                    select(PhotoCatalogItem)
                    .where(PhotoCatalogItem.photo_id == photo_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                if (
                    photo is None
                    or photo.farm_id != envelope.farm_id
                    or photo.plant_id != envelope.plant_id
                ):
                    raise PlantStateError(
                        PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID
                    )
            existing = self._session.scalar(
                select(PlantStateRecord)
                .where(PlantStateRecord.message_id == envelope.message_id)
                .with_for_update()
            )
            if existing is not None:
                if _same_immutable_content(existing, envelope, shape):
                    return PlantStateRecordViewV1.from_record(existing)
                raise PlantStateError(PlantStateErrorCode.PLANT_STATE_CONTENT_CONFLICT)

            referenced: list[PlantStateRecord] = []
            if isinstance(candidate, PlantStateAssessmentCandidateV1):
                referenced = self._load_assessment_sources(
                    envelope.plant_id,
                    candidate,
                )
                if not validate_structural_assessment(
                    referenced,
                    assessment_kind=candidate.assessment_kind,
                    observation_key=candidate.observation_key,
                    direction=candidate.direction,
                ):
                    raise PlantStateError(
                        PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID
                    )

            now = _as_utc(self._clock())
            record = PlantStateRecord(
                state_record_id=uuid.uuid4(),
                farm_id=envelope.farm_id,
                plant_id=envelope.plant_id,
                record_kind=shape["record_kind"],
                agent_id=envelope.agent_id,
                run_id=envelope.run_id,
                message_id=envelope.message_id,
                observation_key=shape["observation_key"],
                polarity=shape["polarity"],
                severity=shape["severity"],
                assessment_kind=shape["assessment_kind"],
                direction=shape["direction"],
                summary=shape["summary"],
                confidence=Decimal(str(shape["confidence"])),
                trust_status=shape["trust_status"],
                source_refs=list(shape["source_refs"]),
                observed_at=shape["observed_at"],
                recorded_at=now,
                confirmation_source=None,
                confirmed_by_account_id=None,
                confirmed_by_membership_id=None,
                confirmed_at=None,
                version=1,
                created_at=now,
                updated_at=now,
            )
            if shape["assessment_kind"] == "conflict":
                for source in referenced:
                    if (
                        source.observation_key == record.observation_key
                        and source.trust_status not in {"rejected", "confirmed"}
                    ):
                        source.trust_status = "conflicting"
                        source.version += 1
                        source.updated_at = now
            self._session.add(record)
            self._session.flush()
            return PlantStateRecordViewV1.from_record(record)

    def list_records(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> PlantStateRecordPageV1:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise PlantStateError(PlantStateErrorCode.PLANT_STATE_LIMIT_INVALID)
        _require_current_access(
            self._session,
            actor,
            plant_id=plant_id,
            mode="history_read",
            clock=self._clock,
            lock=False,
        )
        cursor_value = _decode_cursor(cursor, plant_id) if cursor is not None else None
        statement = select(PlantStateRecord).where(
            PlantStateRecord.farm_id == actor.farm_id,
            PlantStateRecord.plant_id == plant_id,
        )
        if cursor_value is not None:
            recorded_at, state_record_id = cursor_value
            statement = statement.where(
                or_(
                    PlantStateRecord.recorded_at < recorded_at,
                    and_(
                        PlantStateRecord.recorded_at == recorded_at,
                        PlantStateRecord.state_record_id < state_record_id,
                    ),
                )
            )
        rows = list(
            self._session.scalars(
                statement.order_by(
                    PlantStateRecord.recorded_at.desc(),
                    PlantStateRecord.state_record_id.desc(),
                ).limit(limit + 1)
            )
        )
        has_more = len(rows) > limit
        visible = rows[:limit]
        next_cursor = None
        if has_more and visible:
            last = visible[-1]
            next_cursor = _encode_cursor(
                plant_id,
                _as_utc(last.recorded_at),
                last.state_record_id,
            )
        return PlantStateRecordPageV1(
            items=tuple(PlantStateRecordViewV1.from_record(item) for item in visible),
            next_cursor=next_cursor,
        )

    def review_record(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        state_record_id: uuid.UUID,
        expected_version: int,
        decision: Literal["confirm", "reject"] | str,
    ) -> PlantStateRecordViewV1:
        if (
            isinstance(expected_version, bool)
            or not isinstance(expected_version, int)
            or expected_version < 1
            or decision not in {"confirm", "reject"}
        ):
            raise PlantStateError(PlantStateErrorCode.VALIDATION_FAILED)
        with self._session.begin():
            access = _require_current_access(
                self._session,
                actor,
                plant_id=plant_id,
                mode="operate",
                clock=self._clock,
                lock=True,
            )
            if access.role_preset not in {"boss", "engineer"}:
                raise PlantStateError(PlantStateErrorCode.AUTH_PLANT_FORBIDDEN)
            record = self._session.scalar(
                select(PlantStateRecord)
                .where(
                    PlantStateRecord.farm_id == actor.farm_id,
                    PlantStateRecord.plant_id == plant_id,
                    PlantStateRecord.state_record_id == state_record_id,
                )
                .with_for_update()
            )
            if record is None:
                raise PlantStateError(PlantStateErrorCode.PLANT_STATE_NOT_FOUND)
            if record.version != expected_version:
                raise PlantStateError(
                    PlantStateErrorCode.PLANT_STATE_VERSION_CONFLICT
                )
            if (
                decision == "confirm"
                and record.trust_status == "confirmed"
                and record.confirmation_source == "human_review"
            ) or (decision == "reject" and record.trust_status == "rejected"):
                return PlantStateRecordViewV1.from_record(record)

            now = _as_utc(self._clock())
            if decision == "confirm":
                polarities = set(
                    self._session.scalars(
                        select(PlantStateRecord.polarity)
                        .where(
                            PlantStateRecord.farm_id == actor.farm_id,
                            PlantStateRecord.plant_id == plant_id,
                            PlantStateRecord.observation_key == record.observation_key,
                            PlantStateRecord.trust_status != "rejected",
                            PlantStateRecord.polarity.in_(["present", "absent"]),
                        )
                        .with_for_update()
                    )
                )
                if {"present", "absent"}.issubset(polarities):
                    raise PlantStateError(
                        PlantStateErrorCode.PLANT_STATE_CONFLICT_UNRESOLVED
                    )
                record.trust_status = "confirmed"
                record.confirmation_source = "human_review"
                record.confirmed_by_account_id = actor.account_id
                record.confirmed_by_membership_id = actor.membership_id
                record.confirmed_at = now
            else:
                record.trust_status = "rejected"
                record.confirmation_source = None
                record.confirmed_by_account_id = None
                record.confirmed_by_membership_id = None
                record.confirmed_at = None
            record.version += 1
            record.updated_at = now
            self._session.flush()
            return PlantStateRecordViewV1.from_record(record)

    def _load_assessment_sources(
        self,
        plant_id: uuid.UUID,
        candidate: PlantStateAssessmentCandidateV1,
    ) -> list[PlantStateRecord]:
        ids = [_record_id_from_ref(item) for item in candidate.source_refs]
        if any(item is None for item in ids):
            raise PlantStateError(PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID)
        rows = list(
            self._session.scalars(
                select(PlantStateRecord)
                .where(
                    PlantStateRecord.farm_id == candidate.farm_id,
                    PlantStateRecord.plant_id == plant_id,
                    PlantStateRecord.state_record_id.in_(ids),
                    PlantStateRecord.trust_status != "rejected",
                )
                .with_for_update()
            )
        )
        by_id = {item.state_record_id: item for item in rows}
        ordered = [by_id.get(item) for item in ids]
        if any(item is None for item in ordered):
            raise PlantStateError(PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID)
        return [item for item in ordered if item is not None]


def _classification(value: object) -> SafetyClassificationResultV1 | None:
    if isinstance(value, SafetyClassificationResultV1):
        return value
    try:
        return SafetyClassificationResultV1.from_untrusted(value)
    except AgentRuntimeValidationError:
        return None


def _candidate_shape(
    envelope: MessageEnvelopeV1,
    candidate: Candidate,
) -> dict[str, object] | None:
    if (
        not isinstance(envelope, MessageEnvelopeV1)
        or envelope.runtime_decision is not RuntimeDecision.SPEAK
        or envelope.publication_state != "pending_classification"
        or envelope.consumable_by_agents is not False
        or getattr(candidate, "run_id", None) != envelope.run_id
        or getattr(candidate, "message_id", None) != envelope.message_id
        or getattr(candidate, "summary", None) != envelope.candidate_output
        or getattr(candidate, "confidence", None) != envelope.confidence
        or getattr(candidate, "source_refs", None) != envelope.source_refs
    ):
        return None
    if isinstance(candidate, VisionStateCandidateV1):
        if (
            envelope.agent_id != "vision_observation"
            or envelope.candidate_claim_type not in {"observation", "hypothesis"}
        ):
            return None
        trust = (
            "observed"
            if candidate.polarity in {"present", "absent"}
            and candidate.confidence >= 0.50
            else "unknown"
        )
        return {
            "record_kind": "vision_observation",
            "observation_key": candidate.observation_key,
            "polarity": candidate.polarity,
            "severity": candidate.severity,
            "assessment_kind": None,
            "direction": None,
            "summary": candidate.summary,
            "confidence": candidate.confidence,
            "trust_status": trust,
            "source_refs": candidate.source_refs,
            "observed_at": _as_utc(candidate.observed_at),
        }
    if isinstance(candidate, PlantStateAssessmentCandidateV1):
        if (
            envelope.agent_id != "plant_state"
            or envelope.farm_id != candidate.farm_id
            or envelope.plant_id != candidate.plant_id
            or envelope.candidate_claim_type != "hypothesis"
        ):
            return None
        trust = {
            "trend": "hypothesis",
            "conflict": "conflicting",
            "unknown": "unknown",
        }[candidate.assessment_kind]
        return {
            "record_kind": "plant_state_assessment",
            "observation_key": candidate.observation_key,
            "polarity": None,
            "severity": None,
            "assessment_kind": candidate.assessment_kind,
            "direction": candidate.direction,
            "summary": candidate.summary,
            "confidence": candidate.confidence,
            "trust_status": trust,
            "source_refs": candidate.source_refs,
            "observed_at": _as_utc(candidate.observed_at),
        }
    return None


def _same_immutable_content(
    record: PlantStateRecord,
    envelope: MessageEnvelopeV1,
    shape: dict[str, object],
) -> bool:
    return (
        record.farm_id == envelope.farm_id
        and record.plant_id == envelope.plant_id
        and record.agent_id == envelope.agent_id
        and record.run_id == envelope.run_id
        and record.message_id == envelope.message_id
        and record.record_kind == shape["record_kind"]
        and record.observation_key == shape["observation_key"]
        and record.polarity == shape["polarity"]
        and record.severity == shape["severity"]
        and record.assessment_kind == shape["assessment_kind"]
        and record.direction == shape["direction"]
        and record.summary == shape["summary"]
        and float(record.confidence) == shape["confidence"]
        and tuple(record.source_refs) == shape["source_refs"]
        and _as_utc(record.observed_at) == shape["observed_at"]
    )


def _require_current_access(
    session: Session,
    actor: ActorContext,
    *,
    plant_id: uuid.UUID,
    mode: Literal["active_read", "history_read", "operate"],
    clock,
    lock: bool,
) -> _CurrentAccess:
    if not isinstance(actor, ActorContext) or not isinstance(plant_id, uuid.UUID):
        raise PlantStateError(PlantStateErrorCode.AUTH_PLANT_FORBIDDEN)
    suffix = (lambda statement: statement.with_for_update()) if lock else (lambda statement: statement)
    local_session = session.scalar(
        suffix(select(LocalSession).where(LocalSession.session_id == actor.session_id))
        .execution_options(populate_existing=True)
    )
    account = session.scalar(
        suffix(select(Account).where(Account.account_id == actor.account_id))
        .execution_options(populate_existing=True)
    )
    membership = session.scalar(
        suffix(
            select(FarmMembership).where(
                FarmMembership.membership_id == actor.membership_id,
                FarmMembership.farm_id == actor.farm_id,
            )
        ).execution_options(populate_existing=True)
    )
    plant = session.scalar(
        suffix(
            select(Plant).where(
                Plant.plant_id == plant_id,
                Plant.farm_id == actor.farm_id,
            )
        ).execution_options(populate_existing=True)
    )
    if (
        local_session is None
        or account is None
        or membership is None
        or plant is None
        or local_session.account_id != actor.account_id
        or local_session.revoked_at is not None
        or _as_utc(local_session.expires_at) <= _as_utc(clock())
        or account.account_status != "active"
        or membership.account_id != actor.account_id
        or membership.membership_status != "active"
        or membership.role_preset not in {"boss", "engineer", "consultant"}
    ):
        raise PlantStateError(PlantStateErrorCode.AUTH_PLANT_FORBIDDEN)
    grant = None
    if membership.role_preset != "boss":
        grant = session.scalar(
            suffix(
                select(PlantAccessGrant).where(
                    PlantAccessGrant.membership_id == actor.membership_id,
                    PlantAccessGrant.plant_id == plant_id,
                )
            ).execution_options(populate_existing=True)
        )
        if grant is None or grant.status != "active":
            raise PlantStateError(PlantStateErrorCode.AUTH_PLANT_FORBIDDEN)
    active = plant.status == "active"
    can_read = active or mode == "history_read"
    can_operate = active and membership.role_preset in {"boss", "engineer"}
    if mode == "active_read" and not (active and can_read):
        raise PlantStateError(PlantStateErrorCode.AUTH_PLANT_FORBIDDEN)
    if mode == "history_read" and not can_read:
        raise PlantStateError(PlantStateErrorCode.AUTH_PLANT_FORBIDDEN)
    if mode == "operate" and not can_operate:
        raise PlantStateError(PlantStateErrorCode.AUTH_PLANT_FORBIDDEN)
    return _CurrentAccess(
        role_preset=membership.role_preset,
        plant_status=plant.status,
        can_read=can_read,
        can_operate=can_operate,
        permission_source=(
            "boss_role" if membership.role_preset == "boss" else "plant_access_grant"
        ),
        grant_id=None if grant is None else grant.grant_id,
    )


def _vision_photo_id(source_refs: tuple[str, ...]) -> uuid.UUID:
    if len(source_refs) != 1:
        raise PlantStateError(PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID)
    photo_ref = source_refs[0]
    if not isinstance(photo_ref, str) or not photo_ref.startswith("photo:"):
        raise PlantStateError(PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID)
    try:
        photo_id = uuid.UUID(photo_ref.split(":", 1)[1])
    except (TypeError, ValueError, AttributeError):
        raise PlantStateError(
            PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID
        ) from None
    if photo_ref != f"photo:{photo_id}":
        raise PlantStateError(PlantStateErrorCode.PLANT_STATE_CANDIDATE_INVALID)
    return photo_id


def _record_id_from_ref(value: str) -> uuid.UUID | None:
    if not isinstance(value, str) or not value.startswith("plant_state_record:"):
        return None
    try:
        parsed = uuid.UUID(value.split(":", 1)[1])
    except (TypeError, ValueError, AttributeError):
        return None
    return parsed if value == f"plant_state_record:{parsed}" else None


def _encode_cursor(
    plant_id: uuid.UUID,
    recorded_at: datetime,
    state_record_id: uuid.UUID,
) -> str:
    payload = json.dumps(
        {
            "plant_id": str(plant_id),
            "recorded_at": _timestamp(recorded_at),
            "state_record_id": str(state_record_id),
            "v": 1,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(value: str, plant_id: uuid.UUID) -> tuple[datetime, uuid.UUID]:
    try:
        if not isinstance(value, str) or not value or "=" in value:
            raise ValueError
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        payload = json.loads(raw.decode("ascii"))
        if (
            not isinstance(payload, dict)
            or set(payload) != {"plant_id", "recorded_at", "state_record_id", "v"}
            or payload["v"] != 1
            or payload["plant_id"] != str(plant_id)
        ):
            raise ValueError
        timestamp = datetime.fromisoformat(payload["recorded_at"].replace("Z", "+00:00"))
        record_id = uuid.UUID(payload["state_record_id"])
        if (
            _encode_cursor(plant_id, timestamp, record_id) != value
            or str(record_id) != payload["state_record_id"]
            or _timestamp(timestamp) != payload["recorded_at"]
        ):
            raise ValueError
        return _as_utc(timestamp), record_id
    except (
        AttributeError,
        binascii.Error,
        OverflowError,
        TypeError,
        UnicodeError,
        ValueError,
    ):
        raise PlantStateError(PlantStateErrorCode.VALIDATION_FAILED) from None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "PlantStateError",
    "PlantStateErrorCode",
    "PlantStateRecordPageV1",
    "PlantStateRecordViewV1",
    "PlantStateTrustService",
]
