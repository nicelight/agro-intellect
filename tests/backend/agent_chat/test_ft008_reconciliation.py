from __future__ import annotations

from sqlalchemy import func, select

from backend.app.access_admin.models import Plant
from backend.app.agent_chat import (
    AgentBusEvent,
    AgentIntroductionBatch,
    PostgreSQLAgentIntroductionSink,
    UIFeedEvent,
    reconcile_active_plants,
)


def _counts(database):
    with database.session() as session:
        return (
            session.scalar(select(func.count(AgentIntroductionBatch.batch_id))),
            session.scalar(select(func.count(UIFeedEvent.ui_event_id))),
            session.scalar(select(func.count(AgentBusEvent.event_id))),
        )


def test_restart_and_repeated_reconciliation_converge_without_bus_copy(
    ft008_database, ft008_seed
):
    _farm, _boss, _plant = ft008_seed
    first = reconcile_active_plants(
        ft008_database, PostgreSQLAgentIntroductionSink(ft008_database)
    )
    second = reconcile_active_plants(
        ft008_database, PostgreSQLAgentIntroductionSink(ft008_database)
    )
    assert (first.scanned, first.durable, first.failed) == (1, 1, 0)
    assert (second.scanned, second.durable, second.failed) == (1, 1, 0)
    assert _counts(ft008_database) == (1, 8, 0)


def test_archive_blocks_projection_and_restore_requires_fresh_scan(
    ft008_database, ft008_seed
):
    _farm, _boss, plant = ft008_seed
    with ft008_database.session() as session, session.begin():
        session.get(Plant, plant.plant_id).status = "archived"
    archived = reconcile_active_plants(
        ft008_database, PostgreSQLAgentIntroductionSink(ft008_database)
    )
    assert archived.scanned == 0
    assert _counts(ft008_database) == (0, 0, 0)

    with ft008_database.session() as session, session.begin():
        session.get(Plant, plant.plant_id).status = "active"
    assert _counts(ft008_database) == (0, 0, 0)
    restored = reconcile_active_plants(
        ft008_database, PostgreSQLAgentIntroductionSink(ft008_database)
    )
    assert (restored.scanned, restored.durable) == (1, 1)
    assert _counts(ft008_database) == (1, 8, 0)

    with ft008_database.session() as session, session.begin():
        session.get(Plant, plant.plant_id).status = "archived"
    assert _counts(ft008_database) == (1, 8, 0)
