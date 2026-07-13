from __future__ import annotations

from dataclasses import replace

from sqlalchemy import func, select

from backend.app.agent_chat import (
    AgentIntroductionBatch,
    PostgreSQLAgentIntroductionSink,
    UIFeedEvent,
)
from backend.app.agent_runtime import build_introduction_batch


def _batch(plant):
    return build_introduction_batch(farm_id=plant.farm_id, plant_id=plant.plant_id)


def _counts(database):
    with database.session() as session:
        return (
            session.scalar(select(func.count(AgentIntroductionBatch.batch_id))),
            session.scalar(select(func.count(UIFeedEvent.ui_event_id))),
        )


def test_sink_accepts_exactly_eight_then_duplicates_without_timestamp_change(
    ft008_database, ft008_seed
):
    _farm, _boss, plant = ft008_seed
    sink = PostgreSQLAgentIntroductionSink(ft008_database)
    batch = _batch(plant)

    accepted = sink.store_batch(batch)
    assert (accepted.status, accepted.durable, accepted.accepted_count, accepted.reason_code) == (
        "accepted", True, 8, None
    )
    with ft008_database.session() as session:
        before = {
            event.ui_event_id: event.created_at
            for event in session.scalars(select(UIFeedEvent))
        }
        assert all(
            not event.visible_to_agents and not event.consumable_by_agents
            for event in session.scalars(select(UIFeedEvent))
        )
    duplicate = sink.store_batch(batch)
    assert (duplicate.status, duplicate.durable, duplicate.accepted_count) == (
        "duplicate", True, 8
    )
    assert _counts(ft008_database) == (1, 8)
    with ft008_database.session() as session:
        assert {
            event.ui_event_id: event.created_at
            for event in session.scalars(select(UIFeedEvent))
        } == before


def test_sink_rejects_noncanonical_input_and_existing_content_conflict(
    ft008_database, ft008_seed
):
    _farm, _boss, plant = ft008_seed
    sink = PostgreSQLAgentIntroductionSink(ft008_database)
    batch = _batch(plant)
    altered_item = replace(batch.introductions[0], introduction_text="altered")
    altered = replace(batch, introductions=(altered_item, *batch.introductions[1:]))
    invalid = sink.store_batch(altered)
    assert (invalid.status, invalid.accepted_count, invalid.reason_code) == (
        "rejected", 0, "batch_invalid"
    )
    assert _counts(ft008_database) == (0, 0)

    assert sink.store_batch(batch).status == "accepted"
    with ft008_database.session() as session, session.begin():
        event = session.get(UIFeedEvent, batch.introductions[0].introduction_id)
        event.display_payload = {**event.display_payload, "introduction_text": "conflict"}
    conflict = sink.store_batch(batch)
    assert (conflict.status, conflict.accepted_count, conflict.reason_code) == (
        "rejected", 0, "content_conflict"
    )
    assert _counts(ft008_database) == (1, 8)


def test_sink_failure_rolls_back_batch_and_all_events(
    ft008_database, ft008_seed, monkeypatch
):
    _farm, _boss, plant = ft008_seed
    batch = _batch(plant)
    from backend.app.agent_chat import introduction_sink as module

    original = module._event_from
    calls = 0

    def invalid_second(item):
        nonlocal calls
        calls += 1
        event = original(item)
        if calls == 2:
            event.visible_to_agents = True
        return event

    monkeypatch.setattr(module, "_event_from", invalid_second)
    failed = PostgreSQLAgentIntroductionSink(ft008_database).store_batch(batch)
    assert (failed.status, failed.durable, failed.accepted_count, failed.reason_code) == (
        "failed", False, 0, "persistence_failed"
    )
    assert _counts(ft008_database) == (0, 0)
