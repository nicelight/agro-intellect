from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.app.agent_chat import AgentBusEvent, UIFeedEvent
from backend.app.main import create_app
from tests.backend.api.test_ft002_plant_routes import api_runtime, _cookies


def _introduction_and_bus_counts(database, plant_id: uuid.UUID) -> tuple[int, int]:
    with database.session() as session:
        return (
            session.scalar(
                select(func.count(UIFeedEvent.ui_event_id)).where(
                    UIFeedEvent.plant_id == plant_id,
                    UIFeedEvent.display_kind == "agent_introduction",
                )
            ),
            session.scalar(
                select(func.count(AgentBusEvent.event_id)).where(
                    AgentBusEvent.plant_id == plant_id
                )
            ),
        )


@pytest.mark.parametrize("actor_name", ["boss", "engineer"])
def test_plant_create_preserves_201_and_writes_no_introduction_or_bus(
    api_runtime,
    actor_name,
):
    client, database, seed = api_runtime
    actor = getattr(seed, actor_name)
    response = client.post(
        "/api/plants",
        json={
            "plant_key": f"write_free_{actor_name}",
            "display_name": f"Write Free {actor_name.title()}",
        },
        cookies=_cookies(actor),
    )

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert set(response.json()) == {
        "plant_id",
        "farm_id",
        "plant_key",
        "display_name",
        "status",
        "created_at",
        "updated_at",
        "permissions",
    }
    if actor_name == "engineer":
        assert response.json()["permissions"]["source"] == "plant_access_grant"
    plant_id = uuid.UUID(response.json()["plant_id"])
    assert _introduction_and_bus_counts(database, plant_id) == (0, 0)
    assert not hasattr(client.app.state, "agent_introduction_sink")


def test_process_startup_performs_no_introduction_write(api_runtime):
    client, database, seed = api_runtime
    created = client.post(
        "/api/plants",
        json={"plant_key": "startup_free", "display_name": "Startup Free"},
        cookies=_cookies(seed.boss),
    )
    plant_id = uuid.UUID(created.json()["plant_id"])
    assert _introduction_and_bus_counts(database, plant_id) == (0, 0)

    app = create_app(database=database)
    with TestClient(app, base_url="http://127.0.0.1"):
        pass

    assert _introduction_and_bus_counts(database, plant_id) == (0, 0)
