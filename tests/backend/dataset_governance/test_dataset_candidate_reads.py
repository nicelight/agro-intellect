"""Read-only Dataset Candidate service/repository tests (FT-016-AC-009 / REQ-021).

Pure-read coverage on the canonical PostgreSQL authority: exact safe projection
with authority values, Plant scope, complete stable keyset pagination, cursor
canonicality, active vs archived retained-history authority, no-enumeration
denials, safe fail-closed failures, and a post-read DB snapshot proving zero
writes on every read path (success, denied, failed, rerun).
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json
import uuid

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.access_admin.actor_context import (
    ActorContext,
    AuthTransport,
)
from backend.app.access_admin.models import Account, FarmMembership, LocalSession
from backend.app.access_admin.permissions import MembershipStatus, RolePreset
from backend.app.access_admin.session_service import ValidatedSession
from backend.app.dataset_governance import (
    DatasetCandidate,
    DatasetGovernanceError,
    DatasetGovernanceErrorCode,
)
from backend.app.dataset_governance.repository import DatasetGovernanceRepository
from backend.app.dataset_governance.service import DatasetGovernanceService
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_active_plant,
    create_actor,
    grant_access,
    revoke_access,
    seed_farm,
)

NOW = datetime(2026, 8, 17, 9, 0, tzinfo=timezone.utc)

EXPECTED_VIEW_FIELDS = {
    "candidate_id",
    "plant_id",
    "source_kind",
    "source_ref",
    "candidate_status",
    "quality_tier",
    "split",
    "confirmation_source",
    "evidence_refs",
    "curator_decision",
    "corrected",
    "follow_up_seen",
    "can_train_on",
    "record_version",
    "created_at",
    "updated_at",
}

FORBIDDEN_VIEW_FIELDS = {
    "farm_id",
    "candidate_origin",
    "curator_notes_ref",
    "curator_run_id",
    "curator_command_sha256",
    "curator_recorded_at",
    "event_refs",
}


def _disabled_actor(database, farm) -> tuple[object, object, uuid.UUID]:
    """Create a disabled-membership actor with a live session row.

    ``create_actor`` refuses disabled memberships by design (the resolver
    rejects them), so this helper builds the rows and an ActorContext directly.
    The Dataset read authority must still deny this actor.
    """
    now = datetime.now(timezone.utc)
    with database.session() as session:
        account = Account(
            login_name=f"disabled-{uuid.uuid4().hex}",
            display_name="Disabled User",
            account_status="active",
            password_hash="test-only-hash",
        )
        session.add(account)
        session.flush()
        membership = FarmMembership(
            account_id=account.account_id,
            farm_id=farm.farm_id,
            role_preset="engineer",
            membership_status="disabled",
        )
        session.add(membership)
        session.flush()
        local_session = LocalSession(
            account_id=account.account_id,
            token_hash=uuid.uuid4().hex * 2,
            created_at=now,
            expires_at=now + timedelta(days=1),
            auth_method="local_password",
        )
        session.add(local_session)
        session.flush()
        validated = ValidatedSession(
            session=local_session,
            account=account,
            membership=membership,
        )
    actor = ActorContext._from_validated(
        request_id=f"req-disabled-{uuid.uuid4().hex}",
        validated_session=validated,
        role_preset=RolePreset("engineer"),
        membership_status=MembershipStatus.DISABLED,
        transport=AuthTransport.COOKIE,
        plant_permission_resolver=lambda plant_id, operation_kind: None,
    )
    return actor, membership, membership.membership_id


def _seed_candidate(
    session,
    *,
    farm_id: uuid.UUID,
    plant_id: uuid.UUID,
    updated_at: datetime,
    index: int,
    status: str = "candidate",
    source_kind: str = "photo_catalog_item",
) -> DatasetCandidate:
    confirmed = status == "confirmed"
    candidate = DatasetCandidate(
        candidate_id=uuid.uuid4(),
        farm_id=farm_id,
        plant_id=plant_id,
        candidate_status=status,
        candidate_origin="raw",
        quality_tier=("standard" if confirmed else "standard"),
        split=None,
        confirmation_source=("human_review" if confirmed else None),
        evidence_refs=[
            {"kind": "photo", "ref": str(uuid.uuid4())},
            {"kind": "observation", "ref": str(uuid.uuid4())},
        ],
        source_kind=source_kind,
        source_ref=uuid.uuid4(),
        curator_decision=("selected" if index == 2 else None),
        curator_notes_ref=("internal://notes" if index == 2 else None),
        curator_run_id=(uuid.uuid4() if index == 2 else None),
        curator_command_sha256=("a" * 64 if index == 2 else None),
        curator_recorded_at=(updated_at if index == 2 else None),
        corrected=(index == 3),
        follow_up_seen=(index in {2, 4}),
        can_train_on=(confirmed and index == 0),
        record_version=index + 1,
        event_refs=[{"kind": "timeline", "ref": str(uuid.uuid4())}],
        created_at=updated_at - timedelta(minutes=5),
        updated_at=updated_at,
    )
    session.add(candidate)
    return candidate


def _full_db_dump(database) -> dict[str, object]:
    """Deterministic row-level snapshot of every table for zero-write proof."""
    inspector = inspect(database.engine())
    table_names = sorted(inspector.get_table_names())
    snapshot: dict[str, object] = {}
    with database.session() as session:
        for table_name in table_names:
            count = session.execute(
                select(func.count()).select_from(text(f'"{table_name}"'))
            ).scalar()
            rows = session.execute(
                text(f'SELECT * FROM "{table_name}" ORDER BY 1')
            ).mappings().all()
            snapshot[table_name] = {
                "count": count,
                "rows": [tuple(sorted(item.items())) for item in rows],
            }
    return snapshot


def _dump_candidates(database, *, plant_id: uuid.UUID) -> list[dict[str, object]]:
    with database.session() as session:
        rows = session.scalars(
            select(DatasetCandidate)
            .where(DatasetCandidate.plant_id == plant_id)
            .order_by(DatasetCandidate.updated_at, DatasetCandidate.candidate_id)
        ).all()
        return [{c.name: getattr(row, c.name) for c in DatasetCandidate.__table__.columns} for row in rows]


@pytest.fixture
def read_seed(ft014_database):
    farm = seed_farm(ft014_database)
    boss, boss_membership = create_actor(ft014_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft014_database, farm, "engineer")
    consultant, consultant_membership = create_actor(ft014_database, farm, "consultant")
    disabled, disabled_membership, _ = _disabled_actor(ft014_database, farm)

    plant = create_active_plant(
        ft014_database,
        boss,
        plant_key=f"read_{uuid.uuid4().hex[:8]}",
    )
    archived = create_active_plant(
        ft014_database,
        boss,
        plant_key=f"archived_{uuid.uuid4().hex[:8]}",
    )
    no_grant_plant = create_active_plant(
        ft014_database,
        boss,
        plant_key=f"nogrant_{uuid.uuid4().hex[:8]}",
    )

    grant_access(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    grant_access(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )
    grant_access(
        ft014_database,
        boss,
        plant_id=archived.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    grant_access(
        ft014_database,
        boss,
        plant_id=archived.plant_id,
        membership_id=consultant_membership.membership_id,
    )
    grant_access(
        ft014_database,
        boss,
        plant_id=no_grant_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    revoke_access(
        ft014_database,
        boss,
        plant_id=no_grant_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archive_plant(ft014_database, boss, plant_id=archived.plant_id)

    candidates: list[DatasetCandidate] = []
    with ft014_database.session() as session:
        for index in range(7):
            candidates.append(
                _seed_candidate(
                    session,
                    farm_id=farm.farm_id,
                    plant_id=plant.plant_id,
                    updated_at=NOW + timedelta(minutes=index),
                    index=index,
                    status=("confirmed" if index in {0, 2} else "candidate"),
                    source_kind=(
                        "photo_catalog_item" if index % 2 == 0 else "daily_check_in"
                    ),
                )
            )
        archived_candidate = _seed_candidate(
            session,
            farm_id=farm.farm_id,
            plant_id=archived.plant_id,
            updated_at=NOW + timedelta(minutes=1),
            index=0,
            status="confirmed",
            source_kind="manual_measurement",
        )
        session.commit()
        session.refresh(archived_candidate)

    return {
        "farm": farm,
        "boss": boss,
        "engineer": engineer,
        "consultant": consultant,
        "disabled": disabled,
        "boss_membership": boss_membership,
        "engineer_membership": engineer_membership,
        "plant": plant,
        "archived_plant": archived,
        "no_grant_plant": no_grant_plant,
        "candidates": candidates,
        "archived_candidate": archived_candidate,
    }


def test_read_projection_exact_authority_values(ft014_database, read_seed):
    farm = read_seed["farm"]
    plant = read_seed["plant"]
    with ft014_database.session() as session:
        page = DatasetGovernanceService(session).list_dataset_candidates(
            read_seed["boss"],
            plant_id=plant.plant_id,
            limit=100,
        )
    assert page.schema_version == 1
    assert len(page.items) == 7

    by_candidate_id = {item.candidate_id: item for item in page.items}
    ordered = [item.candidate_id for item in page.items]
    expected_order = [
        str(c.candidate_id)
        for c in sorted(
            read_seed["candidates"],
            key=lambda c: (c.updated_at, c.candidate_id),
            reverse=True,
        )
    ]
    assert [str(item) for item in ordered] == expected_order

    for candidate in read_seed["candidates"]:
        view = by_candidate_id[candidate.candidate_id]
        value = view.as_value()
        assert set(value) == EXPECTED_VIEW_FIELDS
        assert FORBIDDEN_VIEW_FIELDS.isdisjoint(value)
        assert value["candidate_id"] == str(candidate.candidate_id)
        assert value["plant_id"] == str(candidate.plant_id)
        assert value["source_kind"] == candidate.source_kind
        assert value["source_ref"] == str(candidate.source_ref)
        assert value["candidate_status"] == candidate.candidate_status
        assert value["quality_tier"] == candidate.quality_tier
        assert value["split"] == candidate.split
        assert value["confirmation_source"] == candidate.confirmation_source
        assert value["curator_decision"] == candidate.curator_decision
        assert value["corrected"] == candidate.corrected
        assert value["follow_up_seen"] == candidate.follow_up_seen
        # can_train_on is copied from authority verbatim, never recomputed.
        assert value["can_train_on"] == candidate.can_train_on
        assert value["record_version"] == candidate.record_version
        assert value["created_at"].endswith(("+00:00", "Z"))
        assert value["updated_at"].endswith(("+00:00", "Z"))
        assert value["evidence_refs"] == [
            dict(item) for item in candidate.evidence_refs
        ]

    # The seeded confirmed candidates carry mixed stored can_train_on values;
    # the projection must preserve both without recomputing either.
    confirmed_values = {
        by_candidate_id[c.candidate_id].as_value()["can_train_on"]
        for c in read_seed["candidates"]
        if c.candidate_status == "confirmed"
    }
    assert confirmed_values == {False, True}


def test_read_is_farm_filtered_and_plant_scoped_complete_stable_pagination(
    ft014_database, read_seed
):
    plant = read_seed["plant"]
    seen: list[str] = []
    cursor = None
    with ft014_database.session() as session:
        while True:
            page = DatasetGovernanceService(session).list_dataset_candidates(
                read_seed["engineer"],
                plant_id=plant.plant_id,
                limit=3,
                cursor=cursor,
            )
            ids = [str(item.candidate_id) for item in page.items]
            assert len(ids) <= 3
            seen.extend(ids)
            if page.next_cursor is None:
                break
            cursor = page.next_cursor
            assert len(ids) == 3
    assert len(seen) == 7
    assert len(set(seen)) == 7
    expected_desc = [
        str(c.candidate_id)
        for c in sorted(
            read_seed["candidates"],
            key=lambda c: (c.updated_at, c.candidate_id),
            reverse=True,
        )
    ]
    assert seen == expected_desc


def test_cursor_decode_reencode_identity_and_rejections(ft014_database, read_seed):
    plant = read_seed["plant"]
    with ft014_database.session() as session:
        page = DatasetGovernanceService(session).list_dataset_candidates(
            read_seed["boss"],
            plant_id=plant.plant_id,
            limit=2,
        )
    assert page.next_cursor is not None
    cursor = page.next_cursor

    with ft014_database.session() as session:
        continued = DatasetGovernanceService(session).list_dataset_candidates(
            read_seed["boss"],
            plant_id=plant.plant_id,
            limit=2,
            cursor=cursor,
        )
    assert {item.candidate_id for item in page.items}.isdisjoint(
        {item.candidate_id for item in continued.items}
    )

    payload = json.loads(
        base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode("utf-8")
    )
    malformed = [
        f"!{cursor}",
        f"{cursor[:4]} {cursor[4:]}",
        f"{cursor}=",
        _encoded({**payload, "v": 2}),
        _encoded({**payload, "extra": True}),
        _encoded({k: v for k, v in payload.items() if k != "candidate_id"}),
        _encoded({**payload, "updated_at": "not-a-timestamp"}),
        _encoded({**payload, "candidate_id": "not-a-uuid"}),
        _encoded({**payload, "plant_id": str(uuid.uuid4())}),
        _encoded(payload, canonical_json=False),
    ]
    for index, bad_cursor in enumerate(malformed):
        with ft014_database.session() as session:
            with pytest.raises(DatasetGovernanceError) as exc_info:
                DatasetGovernanceService(session).list_dataset_candidates(
                    read_seed["boss"],
                    plant_id=plant.plant_id,
                    limit=2,
                    cursor=bad_cursor,
                )
        assert exc_info.value.code == DatasetGovernanceErrorCode.CURSOR_INVALID


def test_active_and_archived_retained_history_read_authority(ft014_database, read_seed):
    plant = read_seed["plant"]
    archived = read_seed["archived_plant"]
    for actor in (read_seed["boss"], read_seed["engineer"], read_seed["consultant"]):
        with ft014_database.session() as session:
            active = DatasetGovernanceService(session).list_dataset_candidates(
                actor, plant_id=plant.plant_id, limit=100
            )
            retained = DatasetGovernanceService(session).list_dataset_candidates(
                actor, plant_id=archived.plant_id, limit=100
            )
        assert len(active.items) == 7
        assert len(retained.items) == 1
        assert retained.items[0].candidate_id == read_seed["archived_candidate"].candidate_id
        assert retained.items[0].can_train_on is read_seed["archived_candidate"].can_train_on


def test_denied_reads_no_enumeration(ft014_database, read_seed):
    plant = read_seed["plant"]
    no_grant_plant = read_seed["no_grant_plant"]
    disabled = read_seed["disabled"]
    wrong_farm_plant_id = uuid.uuid4()
    missing_plant_id = uuid.uuid4()

    cases = [
        (read_seed["engineer"], no_grant_plant.plant_id),
        (read_seed["engineer"], wrong_farm_plant_id),
        (read_seed["engineer"], missing_plant_id),
    ]
    for actor, target in cases:
        with ft014_database.session() as session:
            with pytest.raises(DatasetGovernanceError) as exc_info:
                DatasetGovernanceService(session).list_dataset_candidates(
                    actor, plant_id=target, limit=50
                )
        assert exc_info.value.code == DatasetGovernanceErrorCode.CONTEXT_FORBIDDEN

    with ft014_database.session() as session:
        with pytest.raises(DatasetGovernanceError) as exc_info:
            DatasetGovernanceService(session).list_dataset_candidates(
                disabled, plant_id=plant.plant_id, limit=50
            )
    assert exc_info.value.code == DatasetGovernanceErrorCode.CONTEXT_FORBIDDEN


def test_limit_validation(ft014_database, read_seed):
    for bad_limit in (0, -1, 101, 1.5, "10"):
        with ft014_database.session() as session:
            with pytest.raises(DatasetGovernanceError) as exc_info:
                DatasetGovernanceService(session).list_dataset_candidates(
                    read_seed["boss"],
                    plant_id=read_seed["plant"].plant_id,
                    limit=bad_limit,
                )
        assert exc_info.value.code == DatasetGovernanceErrorCode.LIMIT_INVALID
    with ft014_database.session() as session:
        page = DatasetGovernanceService(session).list_dataset_candidates(
            read_seed["boss"],
            plant_id=read_seed["plant"].plant_id,
            limit=1,
        )
    assert len(page.items) == 1


def test_safe_fail_closed_read_failure(ft014_database, read_seed):
    class ExplodingRepository(DatasetGovernanceRepository):
        def list_candidates(self, **kwargs):
            raise SQLAlchemyError("postgresql://admin:secret@localhost/raw leak")

    def build(session):
        return DatasetGovernanceService(session, repository=ExplodingRepository(session))

    with ft014_database.session() as session:
        with pytest.raises(DatasetGovernanceError) as exc_info:
            build(session).list_dataset_candidates(
                read_seed["boss"],
                plant_id=read_seed["plant"].plant_id,
                limit=50,
            )
    assert exc_info.value.code == DatasetGovernanceErrorCode.READ_FAILED
    assert "postgresql:" not in str(exc_info.value)
    assert "secret" not in str(exc_info.value)


def test_read_produces_zero_writes_snapshot(ft014_database, read_seed):
    plant = read_seed["plant"]
    no_grant_plant = read_seed["no_grant_plant"]
    snapshot_before = _full_db_dump(ft014_database)
    candidate_dump_before = _dump_candidates(ft014_database, plant_id=plant.plant_id)

    def run_read(actor, target):
        with ft014_database.session() as session:
            DatasetGovernanceService(session).list_dataset_candidates(
                actor, plant_id=target, limit=3
            )

    run_read(read_seed["boss"], plant.plant_id)
    run_read(read_seed["engineer"], plant.plant_id)
    run_read(read_seed["consultant"], plant.plant_id)
    with pytest.raises(DatasetGovernanceError):
        run_read(read_seed["engineer"], no_grant_plant.plant_id)

    class ExplodingRepository(DatasetGovernanceRepository):
        def list_candidates(self, **kwargs):
            raise SQLAlchemyError("boom")

    def failed_read():
        with ft014_database.session() as session:
            DatasetGovernanceService(
                session, repository=ExplodingRepository(session)
            ).list_dataset_candidates(
                read_seed["boss"], plant_id=plant.plant_id, limit=3
            )

    with pytest.raises(DatasetGovernanceError):
        failed_read()

    run_read(read_seed["boss"], plant.plant_id)

    snapshot_after = _full_db_dump(ft014_database)
    candidate_dump_after = _dump_candidates(ft014_database, plant_id=plant.plant_id)
    assert snapshot_after == snapshot_before
    assert candidate_dump_after == candidate_dump_before


def _encoded(payload: dict[str, object], *, canonical_json: bool = True) -> str:
    separators = (",", ":") if canonical_json else (", ", ": ")
    raw = json.dumps(payload, separators=separators, sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")