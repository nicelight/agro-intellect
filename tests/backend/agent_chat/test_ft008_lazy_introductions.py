from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import threading
import uuid

import pytest
from sqlalchemy import event, func, select

from backend.app.access_admin.models import Plant, PlantAccessGrant
from backend.app.access_admin.farm_service import FarmService
from backend.app.agent_chat import (
    AgentBusEvent,
    PlantFeedError,
    PlantFeedErrorCode,
    PlantFeedService,
    UIFeedEvent,
)
from backend.app.agent_runtime import build_introductions
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    grant_access,
    revoke_access,
)


def _introduction_rows(database, plant_id):
    with database.session() as session:
        return list(
            session.scalars(
                select(UIFeedEvent)
                .where(
                    UIFeedEvent.plant_id == plant_id,
                    UIFeedEvent.display_kind == "agent_introduction",
                )
                .order_by(UIFeedEvent.agent_id)
            )
        )


def _bus_count(database, plant_id) -> int:
    with database.session() as session:
        return session.scalar(
            select(func.count(AgentBusEvent.event_id)).where(
                AgentBusEvent.plant_id == plant_id
            )
        )


def _open(database, actor, plant_id):
    with database.session() as session:
        return PlantFeedService(session).list_feed(
            actor,
            plant_id=plant_id,
            cursor=None,
            limit=50,
        )


def test_active_feed_materializes_exact_missing_rows_and_repeat_preserves_them(
    ft008_database,
    ft008_seed,
):
    farm, boss, plant = ft008_seed
    assert _introduction_rows(ft008_database, plant.plant_id) == []

    first_page = _open(ft008_database, boss, plant.plant_id)
    first = _introduction_rows(ft008_database, plant.plant_id)
    before = {
        row.ui_event_id: (
            row.created_at,
            row.source_id,
            row.source_refs,
            row.display_payload,
            row.visible_to_roles,
            row.visible_to_agents,
            row.consumable_by_agents,
        )
        for row in first
    }

    second_page = _open(ft008_database, boss, plant.plant_id)
    second = _introduction_rows(ft008_database, plant.plant_id)
    assert len(first_page.items) == len(second_page.items) == 8
    assert len(first) == len(second) == 8
    assert {
        row.ui_event_id: (
            row.created_at,
            row.source_id,
            row.source_refs,
            row.display_payload,
            row.visible_to_roles,
            row.visible_to_agents,
            row.consumable_by_agents,
        )
        for row in second
    } == before
    assert {row.farm_id for row in second} == {farm.farm_id}
    assert all(
        row.visible_to_agents is False
        and row.consumable_by_agents is False
        for row in second
    )
    assert _bus_count(ft008_database, plant.plant_id) == 0


@pytest.mark.parametrize("role", ["engineer", "consultant"])
def test_granted_non_boss_feed_materializes_under_current_locked_authority(
    ft008_database,
    ft008_seed,
    role,
):
    farm, boss, plant = ft008_seed
    actor, membership = create_actor(ft008_database, farm, role)
    grant_access(
        ft008_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    statements: list[tuple[int, bool, str]] = []

    def capture(connection, _cursor, statement, _parameters, _context, _many):
        statements.append(
            (id(connection), connection.in_transaction(), statement.lower())
        )

    event.listen(ft008_database.engine(), "before_cursor_execute", capture)
    try:
        page = _open(ft008_database, actor, plant.plant_id)
    finally:
        event.remove(ft008_database.engine(), "before_cursor_execute", capture)

    assert len(page.items) == 8
    assert len(_introduction_rows(ft008_database, plant.plant_id)) == 8
    assert len({connection_id for connection_id, _active, _sql in statements}) == 1
    assert all(active for _connection_id, active, _sql in statements)
    assert any(
        "from accounts join farm_memberships" in sql and "for update" in sql
        for _connection_id, _active, sql in statements
    )
    assert any(
        "from plants" in sql and "for update" in sql
        for _connection_id, _active, sql in statements
    )
    assert any(
        "from plant_access_grants" in sql and "for update" in sql
        for _connection_id, _active, sql in statements
    )
    assert any(
        "insert into ui_feed_events" in sql
        for _connection_id, _active, sql in statements
    )


def test_missing_and_revoked_grants_write_no_introductions(
    ft008_database,
    ft008_seed,
):
    farm, boss, plant = ft008_seed
    engineer, membership = create_actor(ft008_database, farm, "engineer")

    with pytest.raises(PlantFeedError) as missing:
        _open(ft008_database, engineer, plant.plant_id)
    assert missing.value.code is PlantFeedErrorCode.AUTH_PLANT_FORBIDDEN
    assert _introduction_rows(ft008_database, plant.plant_id) == []

    grant_access(
        ft008_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    revoke_access(
        ft008_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    with pytest.raises(PlantFeedError) as revoked:
        _open(ft008_database, engineer, plant.plant_id)
    assert revoked.value.code is PlantFeedErrorCode.AUTH_PLANT_FORBIDDEN
    assert _introduction_rows(ft008_database, plant.plant_id) == []


def test_partial_existing_row_is_never_updated_or_replaced(
    ft008_database,
    ft008_seed,
):
    farm, boss, plant = ft008_seed
    item = build_introductions(
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )[0]
    preserved_at = datetime(2025, 1, 2, 3, 4, tzinfo=timezone.utc)
    preserved_payload = {
        "payload_kind": "agent_introduction",
        "agent_id": item.agent_id,
        "display_name": item.display_name,
        "competence_summary": item.competence_summary,
        "introduction_text": "retained existing presentation",
        "roster_version": 1,
    }
    with ft008_database.session() as session, session.begin():
        session.add(
            UIFeedEvent(
                ui_event_id=item.introduction_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                created_at=preserved_at,
                source_type="system",
                source_id=str(item.introduction_id),
                source_refs=[
                    "agent_roster:1",
                    f"agent_introduction:{item.introduction_id}",
                ],
                display_kind="agent_introduction",
                display_payload=preserved_payload,
                visible_to_roles=["boss", "engineer", "consultant"],
                visible_to_agents=False,
                consumable_by_agents=False,
                agent_id=item.agent_id,
                roster_version=1,
            )
        )

    _open(ft008_database, boss, plant.plant_id)
    rows = _introduction_rows(ft008_database, plant.plant_id)
    retained = next(row for row in rows if row.ui_event_id == item.introduction_id)
    assert len(rows) == 8
    assert retained.created_at == preserved_at
    assert retained.display_payload == preserved_payload


def test_concurrent_feed_opens_converge_to_eight_rows(
    ft008_database,
    ft008_seed,
):
    _farm, boss, plant = ft008_seed
    with ThreadPoolExecutor(max_workers=4) as pool:
        pages = tuple(
            pool.map(
                lambda _index: _open(ft008_database, boss, plant.plant_id),
                range(4),
            )
        )

    assert all(len(page.items) == 8 for page in pages)
    assert len(_introduction_rows(ft008_database, plant.plant_id)) == 8


def test_archive_winning_the_lock_race_keeps_feed_read_only(
    ft008_database,
    ft008_seed,
):
    _farm, boss, plant = ft008_seed
    feed_thread: dict[str, int] = {}
    lock_attempted = threading.Event()

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        if (
            threading.get_ident() == feed_thread.get("ident")
            and "from plants" in statement.lower()
            and "for update" in statement.lower()
        ):
            lock_attempted.set()

    event.listen(ft008_database.engine(), "before_cursor_execute", capture)
    try:
        with ft008_database.session() as archive_session:
            transaction = archive_session.begin()
            locked = archive_session.scalar(
                select(Plant)
                .where(Plant.plant_id == plant.plant_id)
                .with_for_update()
            )
            locked.status = "archived"
            archive_session.flush()

            def open_feed():
                feed_thread["ident"] = threading.get_ident()
                return _open(ft008_database, boss, plant.plant_id)

            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(open_feed)
                assert lock_attempted.wait(timeout=5)
                assert not future.done()
                transaction.commit()
                page = future.result(timeout=5)
    finally:
        event.remove(ft008_database.engine(), "before_cursor_execute", capture)

    assert page.items == ()
    assert _introduction_rows(ft008_database, plant.plant_id) == []


def test_grant_revocation_winning_the_lock_race_denies_and_writes_nothing(
    ft008_database,
    ft008_seed,
):
    farm, boss, plant = ft008_seed
    engineer, membership = create_actor(ft008_database, farm, "engineer")
    grant = grant_access(
        ft008_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    feed_thread: dict[str, int] = {}
    lock_attempted = threading.Event()

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        if (
            threading.get_ident() == feed_thread.get("ident")
            and "from plant_access_grants" in statement.lower()
            and "for update" in statement.lower()
        ):
            lock_attempted.set()

    event.listen(ft008_database.engine(), "before_cursor_execute", capture)
    try:
        with ft008_database.session() as revoke_session:
            transaction = revoke_session.begin()
            locked = revoke_session.scalar(
                select(PlantAccessGrant)
                .where(PlantAccessGrant.grant_id == grant.grant_id)
                .with_for_update()
            )
            locked.status = "revoked"
            revoke_session.flush()

            def open_feed():
                feed_thread["ident"] = threading.get_ident()
                return _open(ft008_database, engineer, plant.plant_id)

            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(open_feed)
                assert lock_attempted.wait(timeout=5)
                assert not future.done()
                transaction.commit()
                with pytest.raises(PlantFeedError) as denied:
                    future.result(timeout=5)
    finally:
        event.remove(ft008_database.engine(), "before_cursor_execute", capture)

    assert denied.value.code is PlantFeedErrorCode.AUTH_PLANT_FORBIDDEN
    assert _introduction_rows(ft008_database, plant.plant_id) == []


def test_archived_read_and_restore_are_write_free_until_active_feed(
    ft008_database,
    ft008_seed,
):
    _farm, boss, plant = ft008_seed
    archive_plant(ft008_database, boss, plant_id=plant.plant_id)

    retained = _open(ft008_database, boss, plant.plant_id)
    assert retained.items == ()
    assert _introduction_rows(ft008_database, plant.plant_id) == []

    with ft008_database.session() as session:
        FarmService(session).restore_plant(boss, plant_id=plant.plant_id)
    assert _introduction_rows(ft008_database, plant.plant_id) == []

    active = _open(ft008_database, boss, plant.plant_id)
    assert len(active.items) == 8
    assert len(_introduction_rows(ft008_database, plant.plant_id)) == 8


@pytest.mark.parametrize("stage", ["insert", "flush", "read", "commit"])
def test_each_persistence_failure_rolls_back_and_later_retry_converges(
    ft008_database,
    ft008_seed,
    monkeypatch,
    stage,
):
    _farm, boss, plant = ft008_seed
    from backend.app.agent_chat import feed as module

    with ft008_database.session() as session:
        service = PlantFeedService(session)
        listener = None
        if stage == "insert":
            monkeypatch.setattr(
                module,
                "_event_from",
                lambda _item: (_ for _ in ()).throw(
                    RuntimeError("synthetic insert failure")
                ),
            )
        elif stage == "flush":
            monkeypatch.setattr(
                session,
                "flush",
                lambda: (_ for _ in ()).throw(
                    RuntimeError("synthetic flush failure")
                ),
            )
        elif stage == "read":
            monkeypatch.setattr(
                service,
                "_read_page_rows",
                lambda **_kwargs: (_ for _ in ()).throw(
                    RuntimeError("synthetic read failure")
                ),
            )
        else:
            def fail_commit(_connection):
                raise RuntimeError("synthetic commit failure")

            listener = fail_commit
            event.listen(ft008_database.engine(), "commit", listener)

        try:
            with pytest.raises(PlantFeedError) as raised:
                service.list_feed(
                    boss,
                    plant_id=plant.plant_id,
                    cursor=None,
                    limit=50,
                )
        finally:
            if listener is not None:
                event.remove(ft008_database.engine(), "commit", listener)

    assert raised.value.code is PlantFeedErrorCode.FEED_PERSISTENCE_FAILED
    assert _introduction_rows(ft008_database, plant.plant_id) == []
    monkeypatch.undo()

    retry = _open(ft008_database, boss, plant.plant_id)
    assert len(retry.items) == 8
    assert len(_introduction_rows(ft008_database, plant.plant_id)) == 8


def test_batch_sink_reconciliation_and_startup_machinery_are_absent():
    roots = (
        Path("backend/app/agent_runtime"),
        Path("backend/app/agent_chat"),
        Path("backend/app/api"),
        Path("backend/app/main.py"),
    )
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for root in roots
        for path in ([root] if root.is_file() else sorted(root.glob("*.py")))
    )
    forbidden = (
        "PlantAgentBootstrap",
        "AgentIntroductionBatch",
        "AgentIntroductionSink",
        "PostgreSQLAgentIntroductionSink",
        "reconcile_active_plants",
        "content_digest",
        "AGENT_BOOTSTRAP_HANDOFF_FAILED",
        "AGENT_INTRODUCTION_RECONCILIATION_FAILED",
    )
    assert all(name not in source for name in forbidden)
    assert not Path("backend/app/agent_chat/introduction_sink.py").exists()
    assert not Path("backend/app/agent_chat/reconciliation.py").exists()
