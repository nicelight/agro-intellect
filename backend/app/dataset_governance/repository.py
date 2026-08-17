"""Repository and current-authority locks for Dataset Governance."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from sqlalchemy import and_, column, or_, select, table, text
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.models import (
    Account,
    FarmMembership,
    LocalSession,
    Plant,
    PlantAccessGrant,
)
from .contracts import (
    DatasetGovernanceError,
    DatasetGovernanceErrorCode,
    SourceKind,
)
from .models import DatasetCandidate

#: Evidence kinds from the canonical FT-014 closed set.
ALLOWED_EVIDENCE_KINDS = frozenset(
    {"photo", "check_in", "measurement", "follow_up_outcome", "review", "observation"}
)

#: Kind -> runtime table existence target for same-Farm/same-Plant validation.
_EVIDENCE_KIND_TABLE = {
    "photo": ("photo_catalog_items", "photo_id"),
    "check_in": ("daily_checkins", "check_in_id"),
    "observation": ("daily_checkins", "check_in_id"),
    "measurement": ("manual_measurements", "measurement_id"),
    "follow_up_outcome": ("outcomes", "outcome_id"),
}

#: Outcome source ref kind -> Dataset source identity mapping. Only these kinds
#: can produce an eligible Dataset candidate; ``plant`` and
#: ``plant_state_record`` refs have no FT-014 source candidate and are ignored.
_OUTCOME_REF_SOURCE_KIND = {
    "photo_catalog_item": SourceKind.PHOTO_CATALOG_ITEM,
    "daily_checkin": SourceKind.DAILY_CHECK_IN,
    "manual_measurement": SourceKind.MANUAL_MEASUREMENT,
}

#: Dataset source kind -> raw runtime source table for same-Farm/same-Plant
#: lock/recheck without cross-module ORM imports.
_SOURCE_KIND_TABLE = {
    SourceKind.PHOTO_CATALOG_ITEM: ("photo_catalog_items", "photo_id"),
    SourceKind.DAILY_CHECK_IN: ("daily_checkins", "check_in_id"),
    SourceKind.MANUAL_MEASUREMENT: ("manual_measurements", "measurement_id"),
}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class CurrentDatasetScope:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    plant_status: str
    role_preset: str
    permission_source: str
    grant_id: uuid.UUID | None
    can_operate: bool


class DatasetGovernanceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def current_scope(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        for_update: bool,
    ) -> CurrentDatasetScope | None:
        resolved = self._resolve_identity(actor, plant_id=plant_id, for_update=for_update)
        if resolved is None:
            return None
        _account, membership, plant = resolved

        grant_id: uuid.UUID | None = None
        permission_source = "boss_role"
        if membership.role_preset != "boss":
            grant_query = select(PlantAccessGrant).where(
                PlantAccessGrant.membership_id == membership.membership_id,
                PlantAccessGrant.plant_id == plant_id,
                PlantAccessGrant.status == "active",
            )
            if for_update:
                grant_query = grant_query.with_for_update()
            grant = self.session.scalar(
                grant_query.execution_options(populate_existing=True)
            )
            if grant is None:
                return None
            grant_id = grant.grant_id
            permission_source = "plant_access_grant"

        return CurrentDatasetScope(
            farm_id=actor.farm_id,
            plant_id=plant_id,
            plant_status=plant.status,
            role_preset=membership.role_preset,
            permission_source=permission_source,
            grant_id=grant_id,
            can_operate=(
                plant.status == "active"
                and membership.role_preset in {"boss", "engineer"}
            ),
        )

    def current_read_scope(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
    ) -> CurrentDatasetScope | None:
        """Read-only authority for the protected Dataset Candidate projection.

        Active Plants use normal-read authority; archived Plants use the
        retained-history read path. The read performs no mutation and never
        reveals whether an unauthorized Plant exists (no-enumeration denial).
        """
        resolved = self._resolve_identity(actor, plant_id=plant_id, for_update=False)
        if resolved is None:
            return None
        _account, membership, plant = resolved
        if plant.status not in {"active", "archived"}:
            return None

        grant_id: uuid.UUID | None = None
        permission_source = "boss_role"
        if membership.role_preset != "boss":
            grant = self.session.scalar(
                select(PlantAccessGrant)
                .where(
                    PlantAccessGrant.membership_id == membership.membership_id,
                    PlantAccessGrant.plant_id == plant_id,
                    PlantAccessGrant.status == "active",
                )
                .execution_options(populate_existing=True)
            )
            if grant is None:
                return None
            grant_id = grant.grant_id
            permission_source = "plant_access_grant"

        return CurrentDatasetScope(
            farm_id=actor.farm_id,
            plant_id=plant_id,
            plant_status=plant.status,
            role_preset=membership.role_preset,
            permission_source=permission_source,
            grant_id=grant_id,
            can_operate=(
                plant.status == "active"
                and membership.role_preset in {"boss", "engineer"}
            ),
        )

    def _resolve_identity(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        for_update: bool,
    ) -> tuple[object, object, object] | None:
        now = datetime.now(timezone.utc)
        session_query = select(LocalSession).where(
            LocalSession.session_id == actor.session_id
        )
        account_query = select(Account).where(Account.account_id == actor.account_id)
        membership_query = select(FarmMembership).where(
            FarmMembership.membership_id == actor.membership_id
        )
        plant_query = select(Plant).where(
            Plant.plant_id == plant_id,
            Plant.farm_id == actor.farm_id,
        )
        if for_update:
            session_query = session_query.with_for_update()
            account_query = account_query.with_for_update()
            membership_query = membership_query.with_for_update()
            plant_query = plant_query.with_for_update()
        local_session = self.session.scalar(
            session_query.execution_options(populate_existing=True)
        )
        account = self.session.scalar(
            account_query.execution_options(populate_existing=True)
        )
        membership = self.session.scalar(
            membership_query.execution_options(populate_existing=True)
        )
        plant = self.session.scalar(
            plant_query.execution_options(populate_existing=True)
        )
        if (
            local_session is None
            or account is None
            or membership is None
            or plant is None
            or local_session.account_id != account.account_id
            or local_session.revoked_at is not None
            or _as_utc(local_session.expires_at) <= now
            or account.account_status != "active"
            or membership.account_id != account.account_id
            or membership.farm_id != actor.farm_id
            or membership.membership_status != "active"
            or membership.role_preset != actor.role_preset.value
            or membership.role_preset not in {"boss", "engineer", "consultant"}
        ):
            return None
        return account, membership, plant

    def candidate_by_source_identity(
        self,
        *,
        plant_id: uuid.UUID,
        source_kind: str,
        source_ref: uuid.UUID,
        for_update: bool,
    ) -> DatasetCandidate | None:
        query = select(DatasetCandidate).where(
            DatasetCandidate.plant_id == plant_id,
            DatasetCandidate.source_kind == source_kind,
            DatasetCandidate.source_ref == source_ref,
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def candidate(
        self,
        candidate_id: uuid.UUID,
        *,
        for_update: bool,
    ) -> DatasetCandidate | None:
        query = select(DatasetCandidate).where(
            DatasetCandidate.candidate_id == candidate_id
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def list_candidates(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
        limit: int,
        after: tuple[datetime, uuid.UUID] | None,
    ) -> list[DatasetCandidate]:
        """Plant-scoped canonical keyset page in ``(updated_at DESC,
        candidate_id DESC)`` order.

        Fetches at most ``limit`` rows plus one lookahead row so the caller can
        decide whether another page exists. Pure read: no locking and no
        mutation. ``farm_id`` is a defensive same-Farm filter on top of the
        authorized Plant scope.
        """
        query = select(DatasetCandidate).where(
            DatasetCandidate.farm_id == farm_id,
            DatasetCandidate.plant_id == plant_id,
        )
        if after is not None:
            updated_at, candidate_id = after
            query = query.where(
                or_(
                    DatasetCandidate.updated_at < updated_at,
                    and_(
                        DatasetCandidate.updated_at == updated_at,
                        DatasetCandidate.candidate_id < candidate_id,
                    ),
                )
            )
        query = query.order_by(
            DatasetCandidate.updated_at.desc(),
            DatasetCandidate.candidate_id.desc(),
        ).limit(limit + 1)
        return list(
            self.session.scalars(
                query.execution_options(populate_existing=True)
            )
        )

    def evidence_refs_resolve(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
        evidence_refs: list[Mapping[str, object]],
    ) -> bool:
        """Return True only when every evidence ref resolves to an existing
        same-Farm/same-Plant runtime record with an allowed canonical kind.

        Raw-table existence checks keep Dataset Governance off other modules'
        ORM models while preserving the boundary direction.
        """
        if not evidence_refs:
            return False
        for item in evidence_refs:
            if not isinstance(item, Mapping):
                return False
            kind = item.get("kind")
            if kind not in ALLOWED_EVIDENCE_KINDS:
                return False
            target = _EVIDENCE_KIND_TABLE.get(kind)
            if target is None:
                return False
            table_name, id_column = target
            raw_ref = item.get("ref")
            try:
                ref_id = uuid.UUID(str(raw_ref))
            except (TypeError, ValueError):
                return False
            identity = table(
                table_name,
                column(id_column),
                column("farm_id"),
                column("plant_id"),
            )
            exists = self.session.scalar(
                select(text("1"))
                .select_from(identity)
                .where(
                    identity.c[id_column] == ref_id,
                    identity.c.farm_id == farm_id,
                    identity.c.plant_id == plant_id,
                )
                .execution_options(populate_existing=True)
            )
            if exists is None:
                return False
        return True

    def lock_outcome_row(
        self,
        outcome_id: uuid.UUID,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> list[object] | None:
        """Lock and recheck the caller's Outcome row identity.

        The caller already locked the row inside its unit of work; re-locking
        inside this command's transaction revalidates that it still exists and
        matches one Farm/Plant before any candidate write. Returns the row's
        canonical ordered ``evidence_refs`` so the service can reject any
        caller-supplied refs that are not the Outcome's own authorized refs.
        """
        outcomes = table(
            "outcomes",
            column("outcome_id"),
            column("farm_id"),
            column("plant_id"),
            column("evidence_refs"),
        )
        row = self.session.execute(
            select(
                outcomes.c.outcome_id,
                outcomes.c.evidence_refs,
            )
            .select_from(outcomes)
            .where(
                outcomes.c.outcome_id == outcome_id,
                outcomes.c.farm_id == farm_id,
                outcomes.c.plant_id == plant_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        ).mappings().first()
        if row is None:
            return None
        return list(row["evidence_refs"])

    def lock_source_row(
        self,
        source_kind: SourceKind,
        source_ref: uuid.UUID,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> bool:
        """Lock and recheck a derived source row (photo/check-in/measurement).

        Keeps Dataset Governance off other modules' ORM models while preserving
        the same-Farm/same-Plant identity contract for the derived link.
        """
        target = _SOURCE_KIND_TABLE.get(source_kind)
        if target is None:
            return False
        table_name, id_column = target
        identity = table(
            table_name,
            column(id_column),
            column("farm_id"),
            column("plant_id"),
        )
        exists = self.session.scalar(
            select(text("1"))
            .select_from(identity)
            .where(
                identity.c[id_column] == source_ref,
                identity.c.farm_id == farm_id,
                identity.c.plant_id == plant_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return exists is not None

    def derive_source_identity(self, ref: str) -> tuple[SourceKind | None, uuid.UUID | None]:
        """Map one Outcome source ref to its Dataset source identity.

        ``photo_catalog_item``, ``daily_checkin``, and ``manual_measurement``
        map to their exact Dataset source kinds; ``plant`` and
        ``plant_state_record`` refs return ``(None, None)`` (ignored — they have
        no FT-014 source candidate). Any other kind is an unsupported derived
        link and fails closed so arbitrary evidence cannot be silently dropped.
        """
        kind, identifier = ref.split(":", maxsplit=1)
        source_kind = _OUTCOME_REF_SOURCE_KIND.get(kind)
        if source_kind is None:
            if kind in {"plant", "plant_state_record"}:
                return None, None
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.EVIDENCE_ASSOCIATION_CONFLICT
            )
        try:
            source_ref = uuid.UUID(identifier)
        except (TypeError, ValueError):
            return None, None
        return source_kind, source_ref


__all__ = [
    "ALLOWED_EVIDENCE_KINDS",
    "CurrentDatasetScope",
    "DatasetGovernanceRepository",
]
