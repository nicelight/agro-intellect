"""Isolated PostgreSQL substrate for FT-013 governance tests."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy.engine import make_url

from backend.app import AppSettings
from backend.app.companion_governance import PersistCompanionProposalCommandV1
from backend.app.database import DatabaseHandle, build_database
from backend.app.safety_gate import SafetyClassification
from backend.migrations import build_alembic_config
from tests.backend.plant_operations.conftest import (
    create_active_plant,
    create_actor,
    seed_farm,
)

FT013_NOW = datetime(2026, 7, 24, 7, 0, tzinfo=timezone.utc)


class TimelineRecorder:
    def __init__(self, *, fail_on: str | None = None) -> None:
        self.events = []
        self.fail_on = fail_on

    def __call__(self, event):
        if event.event_type == self.fail_on:
            from backend.app.timeline import TimelineAppendError

            raise TimelineAppendError()
        self.events.append(event)
        event_id = uuid.uuid4()
        return {
            "timeline_event_id": str(event_id),
            "timeline_ref": f"timeline.jsonl#{event_id}",
            "event_type": event.event_type,
            "created_at": FT013_NOW.isoformat(),
        }


@pytest.fixture
def ft013_database():
    with _postgres_database() as database:
        yield database


@pytest.fixture
def ft013_pre_simplification_database():
    with _postgres_database(include_companion_simplification=False) as database:
        yield database


@pytest.fixture
def ft013_seed(ft013_database):
    farm = seed_farm(ft013_database)
    boss, membership = create_actor(ft013_database, farm, "boss")
    plant = create_active_plant(
        ft013_database,
        boss,
        plant_key=f"ft013_{uuid.uuid4().hex[:10]}",
    )
    return farm, boss, membership, plant


def seed_companion_classification(
    database,
    *,
    farm_id: uuid.UUID,
    plant_id: uuid.UUID,
    effect: str = "discussion_only",
    message_id: uuid.UUID | None = None,
    origin_agent_id: str = "companion",
) -> uuid.UUID:
    message_id = message_id or uuid.uuid4()
    task_kind = effect if effect in {"check", "measurement", "follow_up"} else None
    classification = "safe_task_request" if task_kind is not None else "safe_information"
    reason_code = (
        f"safe_{task_kind}_request"
        if task_kind is not None
        else "non_physical_information"
    )
    with database.session() as session, session.begin():
        session.add(
            SafetyClassification(
                message_id=message_id,
                farm_id=farm_id,
                plant_id=plant_id,
                origin_agent_id=origin_agent_id,
                classifier_version="safety_gate_v1",
                classification=classification,
                safe_task_kind=task_kind,
                reason_code=reason_code,
                physical_action_kind=None,
                provider_status="completed",
                model_ref=None,
                input_sha256=hashlib.sha256(f"input:{message_id}".encode()).hexdigest(),
                result_sha256=hashlib.sha256(
                    f"result:{message_id}".encode()
                ).hexdigest(),
                created_at=FT013_NOW,
            )
        )
    return message_id


def make_proposal_command(
    actor,
    *,
    plant_id: uuid.UUID,
    message_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
    target_issue_id: uuid.UUID | None = None,
    expected_issue_version: int | None = None,
    effect: str = "discussion_only",
    marker: str = "initial",
    fingerprint: str | None = None,
) -> PersistCompanionProposalCommandV1:
    run_id = run_id or uuid.uuid4()
    provider_refs = [f"plant:{plant_id}"]
    if target_issue_id is not None:
        provider_refs.append(f"companion_issue:{target_issue_id}")
    return PersistCompanionProposalCommandV1(
        actor_context=actor,
        run_id=run_id,
        message_id=message_id,
        plant_id=plant_id,
        target_issue_id=target_issue_id,
        expected_issue_version=expected_issue_version,
        issue_summary_text=(
            f"Контроль состояния растения: {marker}."
            if target_issue_id is None
            else None
        ),
        attention_summary_text=f"Требуется решение оператора: {marker}.",
        proposal_summary=f"Краткое предложение: {marker}.",
        proposal_text=f"Подробное предложение для оператора: {marker}.",
        rationale_text=f"Проверенная причина: {marker}.",
        proposed_effect=effect,
        task_display_text=(
            f"Выполнить задачу: {marker}."
            if effect in {"check", "measurement", "follow_up"}
            else None
        ),
        suggested_resolution="keep_open",
        provider_input_refs=tuple(provider_refs),
        run_request_fingerprint=(
            fingerprint
            or hashlib.sha256(f"run:{run_id}:{marker}".encode()).hexdigest()
        ),
    )


@contextmanager
def _postgres_database(*, include_companion_simplification: bool = True):
    settings = AppSettings.from_env()
    base = build_database(settings)
    schema = f"task041_ft013_{uuid.uuid4().hex}"
    scoped: DatabaseHandle | None = None
    try:
        assert base.engine().dialect.name == "postgresql"
        with base.engine().connect() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.commit()
        url = make_url(settings.database_url).update_query_dict(
            {"options": f"-csearch_path={schema},public"}
        )
        scoped = build_database(
            settings.model_copy(
                update={"database_url": url.render_as_string(hide_password=False)}
            )
        )
        script = ScriptDirectory.from_config(build_alembic_config(settings))
        revision_ids = [
            "ft001_access_sessions",
            "ft002_farm_plant_access",
            "ft004_plant_operations",
            "ft005_photo_intake",
            "ft008_agent_chat_ui_feed",
            "ft009_plant_state",
            "ft011_safety_classifications",
            "ft011_safety_action_decisions",
            "ft012_task_approval_outcomes",
            "ft012_runtime_dispositions",
            "ft013_governance_aggregate",
            "ft012_simplify_follow_up_runtime",
        ]
        if include_companion_simplification:
            revision_ids.append("ft013_simplify_companion")
        with scoped.engine().connect() as connection:
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                for revision_id in revision_ids:
                    script.get_revision(revision_id).module.upgrade()
            connection.commit()
        yield scoped
    finally:
        if scoped is not None:
            scoped.dispose()
        with base.engine().connect() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            connection.commit()
        base.dispose()


__all__ = [
    "FT013_NOW",
    "TimelineRecorder",
    "ft013_database",
    "ft013_pre_simplification_database",
    "ft013_seed",
    "make_proposal_command",
    "seed_companion_classification",
]
