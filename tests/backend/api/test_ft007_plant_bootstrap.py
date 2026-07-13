from __future__ import annotations

import uuid

from sqlalchemy import func, select

from backend.app.access_admin.models import Plant
from backend.app.agent_chat import PostgreSQLAgentIntroductionSink, UIFeedEvent
from backend.app.agent_runtime import AgentIntroductionBatchResultV1
from tests.backend.api.test_ft002_plant_routes import api_runtime, _cookies


class RecordingSink:
    def __init__(self, *, raises=False):
        self.raises = raises
        self.batches = []

    def store_batch(self, batch):
        self.batches.append(batch)
        if self.raises:
            raise RuntimeError("downstream unavailable")
        return AgentIntroductionBatchResultV1(
            batch_id=batch.batch_id,
            status="accepted",
            durable=True,
            accepted_count=8,
            reason_code=None,
        )


def test_production_composition_uses_durable_sink_and_preserves_create_contract(
    api_runtime,
):
    client, database, seed = api_runtime
    assert isinstance(
        client.app.state.agent_introduction_sink, PostgreSQLAgentIntroductionSink
    )
    response = client.post(
        "/api/plants",
        json={"plant_key": "durable_sink", "display_name": "Durable Sink"},
        cookies=_cookies(seed.boss),
    )
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert set(response.json()) == {
        "plant_id", "farm_id", "plant_key", "display_name", "status",
        "created_at", "updated_at", "permissions",
    }
    with database.session() as session:
        count = session.scalar(
            select(func.count(UIFeedEvent.ui_event_id)).where(
                UIFeedEvent.plant_id == uuid.UUID(response.json()["plant_id"])
            )
        )
    assert count == 8


def test_plant_create_commits_before_one_eight_item_handoff(api_runtime):
    client, database, seed = api_runtime
    sink = RecordingSink()
    client.app.state.agent_introduction_sink = sink
    response = client.post(
        "/api/plants",
        json={"plant_key": "bootstrap_hook", "display_name": "Bootstrap Hook"},
        cookies=_cookies(seed.boss),
    )
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert set(response.json()) == {
        "plant_id", "farm_id", "plant_key", "display_name", "status", "created_at", "updated_at", "permissions"
    }
    assert len(sink.batches) == 1
    assert len(sink.batches[0].introductions) == 8
    assert str(sink.batches[0].plant_id) == response.json()["plant_id"]
    with database.session() as session:
        assert session.scalar(
            select(Plant).where(Plant.plant_id == sink.batches[0].plant_id)
        ) is not None


def test_sink_failure_cannot_change_committed_201_or_create_provider_work(api_runtime):
    client, database, seed = api_runtime
    sink = RecordingSink(raises=True)
    client.app.state.agent_introduction_sink = sink
    response = client.post(
        "/api/plants",
        json={"plant_key": "bootstrap_failure", "display_name": "Still Created"},
        cookies=_cookies(seed.engineer),
    )
    assert response.status_code == 201
    assert response.json()["display_name"] == "Still Created"
    assert response.json()["permissions"]["source"] == "plant_access_grant"
    assert len(sink.batches) == 1
    with database.session() as session:
        plant = session.scalar(
            select(Plant).where(Plant.plant_id == sink.batches[0].plant_id)
        )
        assert plant is not None and plant.status == "active"
