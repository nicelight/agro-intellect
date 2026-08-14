from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, func, select

from backend.app.access_admin.models import Base
from backend.app.config import AppSettings
from backend.app.database import build_database
from backend.app.main import create_app
from backend.app.photo_intake import PhotoCatalogItem
from tests.backend.api.test_ft015_storage_status import (
    EXPECTED_FIELDS,
    _cookies,
    _seed,
    _seed_catalog,
)

TWO_HUNDRED_MIB = 209715200


class PromptPageModel:
    """Deterministic FT-016-style consumer model of one rendered prompt page.

    Holds only in-memory, Account-local closure state for a single page load.
    It never writes backend state: a fresh page load creates a new model, so
    any local closure is discarded and the prompt may appear again while
    pressure remains eligible. There is no durable preference, cooldown, or
    shared state between Accounts.
    """

    def __init__(self, status: dict[str, object]) -> None:
        self._eligible = bool(status["prompt_eligible"])
        self._sync_status = status["sync_status"]
        self._closed = False

    @property
    def shown(self) -> bool:
        return (
            self._sync_status == "local_only"
            and self._eligible
            and not self._closed
        )

    def acknowledge(self) -> None:
        self._closed = True

    def dismiss(self) -> None:
        self._closed = True


@dataclass(frozen=True)
class ConsumerSeed:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    boss: object
    engineer: object
    consultant: object


@pytest.fixture
def consumer_runtime(tmp_path: Path):
    settings = AppSettings(
        database_url="sqlite+pysqlite:///:memory:",
        local_artifact_root=tmp_path / "artifacts",
        local_timeline_root=tmp_path / "timeline",
    )
    database = build_database(settings)
    engine = database.engine()
    event.listen(
        engine,
        "connect",
        lambda connection, _record: connection.create_function(
            "btrim",
            1,
            lambda value: value.strip() if isinstance(value, str) else value,
        ),
    )
    Base.metadata.create_all(engine)
    seed = _seed(database)
    app = create_app(settings=settings, database=database)
    try:
        with TestClient(app, base_url="http://127.0.0.1") as client:
            yield (
                client,
                database,
                ConsumerSeed(
                    farm_id=seed.farm_id,
                    plant_id=seed.plant_id,
                    boss=seed.boss,
                    engineer=seed.engineer,
                    consultant=seed.consultant,
                ),
            )
    finally:
        database.dispose()


def test_model_acknowledge_and_dismiss_close_only_the_current_page():
    eligible = {"sync_status": "local_only", "prompt_eligible": True}
    ack_page = PromptPageModel(eligible)
    ack_page.acknowledge()
    assert ack_page.shown is False
    dismiss_page = PromptPageModel(eligible)
    dismiss_page.dismiss()
    assert dismiss_page.shown is False
    untouched = PromptPageModel(eligible)
    assert untouched.shown is True


def test_model_fresh_page_reappears_after_local_closure_while_eligible():
    eligible = {"sync_status": "local_only", "prompt_eligible": True}
    page = PromptPageModel(eligible)
    page.dismiss()
    assert page.shown is False
    fresh = PromptPageModel(eligible)
    assert fresh.shown is True


def test_model_never_shown_when_not_eligible_or_not_local_only():
    below_threshold = {"sync_status": "local_only", "prompt_eligible": False}
    assert PromptPageModel(below_threshold).shown is False


def test_two_accounts_transient_actions_with_fresh_request_reappearance(
    consumer_runtime,
):
    client, database, seed = consumer_runtime
    _seed_catalog(
        database=database,
        actor=seed.boss,
        plant_id=seed.plant_id,
        total=TWO_HUNDRED_MIB + 1,
    )

    def fetch(actor, request_id):
        response = client.get(
            "/api/photos/storage-status",
            cookies=_cookies(actor),
            headers={"x-request-id": request_id},
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert set(response.json()) == EXPECTED_FIELDS
        return response.json()

    account_a = seed.engineer
    account_b = seed.consultant

    status_a1 = fetch(account_a, "req-cons-a1")
    assert status_a1["prompt_eligible"] is True
    page_a1 = PromptPageModel(status_a1)
    page_a1.dismiss()
    assert page_a1.shown is False

    status_a2 = fetch(account_a, "req-cons-a2")
    assert status_a2["prompt_eligible"] is True
    assert PromptPageModel(status_a2).shown is True

    status_b1 = fetch(account_b, "req-cons-b1")
    assert status_b1 == status_a2
    page_b1 = PromptPageModel(status_b1)
    page_b1.acknowledge()
    assert page_b1.shown is False

    status_b2 = fetch(account_b, "req-cons-b2")
    assert PromptPageModel(status_b2).shown is True
    status_a3 = fetch(account_a, "req-cons-a3")
    assert PromptPageModel(status_a3).shown is True

    responses = (status_a1, status_a2, status_b1, status_b2, status_a3)
    assert all(response["sync_status"] == "local_only" for response in responses)

    with database.session() as session:
        total = session.scalar(
            select(func.coalesce(func.sum(PhotoCatalogItem.size_bytes), 0))
        )
        count = session.scalar(select(func.count(PhotoCatalogItem.photo_id)))
    assert total == TWO_HUNDRED_MIB + 1
    assert count == 11


def test_no_prompt_mutation_surface_and_no_durable_state(consumer_runtime):
    client, database, seed = consumer_runtime
    for route in client.app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", "")
        assert "acknowledge" not in path and "dismiss" not in path
        if path.startswith("/api/photos"):
            assert not (methods and methods & {"POST", "PATCH", "DELETE"}), path

    table_names = set(Base.metadata.tables)
    assert not {
        name
        for name in table_names
        if any(token in name for token in ("prompt", "acknowledg", "dismiss"))
    }

    for actor in (seed.boss, seed.engineer, seed.consultant):
        response = client.get(
            "/api/photos/storage-status",
            cookies=_cookies(actor),
        )
        assert response.status_code == 200
        assert response.json()["sync_status"] == "local_only"
