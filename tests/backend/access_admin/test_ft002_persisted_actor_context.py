from __future__ import annotations

from contextlib import contextmanager
from threading import Event, Thread, get_ident
from types import SimpleNamespace
import uuid

from sqlalchemy import event, select

from backend.app.access_admin.actor_context import ActorContextResolver, AuthTransport
from backend.app.access_admin.dependencies import get_plant_access_snapshot_provider
from backend.app.access_admin.farm_repository import (
    PersistedPlantAccessSnapshotProvider,
)
from backend.app.access_admin.farm_service import FarmService
from backend.app.access_admin.models import Account, FarmMembership, LocalSession
from backend.app.access_admin.permissions import (
    OperationKind,
    PermissionSource,
    PlantStatus,
)
from backend.app.access_admin.session_service import ValidatedSession
from tests.backend.access_admin.test_ft002_farm_plant_services import (
    StaticValidator,
    _create_actor,
    _postgres_database,
    _seed_farm,
)


def _persisted_actor(database, membership_id: uuid.UUID):
    with database.session() as session:
        membership = session.get(FarmMembership, membership_id)
        account = session.get(Account, membership.account_id)
        local_session = session.scalar(
            select(LocalSession).where(LocalSession.account_id == account.account_id)
        )
        validated = ValidatedSession(
            session=local_session,
            account=account,
            membership=membership,
        )
    return ActorContextResolver(
        session_validator=StaticValidator(validated),
        snapshot_provider=PersistedPlantAccessSnapshotProvider(database),
    ).resolve(
        request_id="req-persisted",
        raw_session_token="synthetic-test-token",
        transport=AuthTransport.COOKIE,
    )


def test_engineer_creator_and_consultant_permissions_use_persisted_ft001_seam():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, boss_membership = _create_actor(database, farm, "boss")
        engineer, engineer_membership = _create_actor(database, farm, "engineer")
        _consultant, consultant_membership = _create_actor(
            database, farm, "consultant"
        )
        with database.session() as session:
            created = FarmService(session).create_plant(
                engineer,
                plant_key="lettuce_001",
                display_name="Lettuce",
            )
        plant_id = created.plant.plant_id

        persisted_engineer = _persisted_actor(
            database, engineer_membership.membership_id
        )
        engineer_permission = persisted_engineer.resolve_plant_permission(
            plant_id, OperationKind.NORMAL_READ
        )
        assert engineer_permission.source is PermissionSource.PLANT_ACCESS_GRANT
        assert engineer_permission.grant_id == created.creator_grant.grant_id
        assert engineer_permission.can_read is True
        assert engineer_permission.can_operate is True
        assert engineer_permission.can_manage_access is False
        assert engineer_permission.can_approve_actions is False

        persisted_boss = _persisted_actor(database, boss_membership.membership_id)
        boss_permission = persisted_boss.resolve_plant_permission(
            plant_id, OperationKind.NORMAL_READ
        )
        assert boss_permission.source is PermissionSource.BOSS_ROLE
        assert boss_permission.grant_id is None
        assert boss_permission.can_read and boss_permission.can_operate

        with database.session() as session:
            FarmService(session).grant_access(
                boss,
                plant_id=plant_id,
                membership_id=consultant_membership.membership_id,
            )
        persisted_consultant = _persisted_actor(
            database, consultant_membership.membership_id
        )
        consultant_permission = persisted_consultant.resolve_plant_permission(
            plant_id, OperationKind.NORMAL_READ
        )
        assert consultant_permission.can_read is True
        assert consultant_permission.can_comment is True
        assert consultant_permission.can_operate is False
        assert consultant_permission.can_create_domain_tasks is False
        assert consultant_permission.can_approve_actions is False


def test_archived_and_revoked_persisted_grants_fail_closed_then_restore_current_state():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, _ = _create_actor(database, farm, "boss")
        _engineer, membership = _create_actor(database, farm, "engineer")
        with database.session() as session:
            plant = FarmService(session).create_plant(
                boss, plant_key="mint_001", display_name="Mint"
            ).plant
        with database.session() as session:
            grant = FarmService(session).grant_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=membership.membership_id,
                plant_approve_actions=False,
            ).entity
        grant_id = grant.grant_id
        actor = _persisted_actor(database, membership.membership_id)
        assert actor.resolve_plant_permission(
            plant.plant_id, OperationKind.NORMAL_READ
        ).can_read

        with database.session() as session:
            FarmService(session).archive_plant(boss, plant_id=plant.plant_id)
        with database.session() as session:
            changed = FarmService(session).grant_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=membership.membership_id,
                plant_approve_actions=True,
            ).entity
        assert changed.grant_id == grant_id

        normal = actor.resolve_plant_permission(
            plant.plant_id, OperationKind.NORMAL_READ
        )
        retained = actor.resolve_plant_permission(
            plant.plant_id, OperationKind.RETAINED_HISTORY_READ
        )
        approval = actor.resolve_plant_permission(
            plant.plant_id, OperationKind.APPROVE_ACTION
        )
        assert normal.plant_status is PlantStatus.ARCHIVED
        assert normal.can_read is False and normal.can_operate is False
        assert retained.can_read is True and retained.can_operate is False
        assert approval.can_approve_actions is False

        with database.session() as session:
            FarmService(session).restore_plant(boss, plant_id=plant.plant_id)
        restored = actor.resolve_plant_permission(
            plant.plant_id, OperationKind.APPROVE_ACTION
        )
        assert restored.plant_status is PlantStatus.ACTIVE
        assert restored.can_approve_actions is True
        assert restored.grant_id == grant_id

        with database.session() as session:
            FarmService(session).revoke_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=membership.membership_id,
            )
        revoked = actor.resolve_plant_permission(
            plant.plant_id, OperationKind.NORMAL_READ
        )
        assert revoked.source is PermissionSource.DENIED
        assert revoked.plant_status is None
        assert revoked.grant_id is None


def test_persisted_provider_mismatch_and_repository_failure_are_no_leak_denials():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, membership = _create_actor(database, farm, "boss")
        with database.session() as session:
            plant = FarmService(session).create_plant(
                boss, plant_key="basil_001", display_name="Basil"
            ).plant
        provider = PersistedPlantAccessSnapshotProvider(database)
        assert provider(
            farm_id=uuid.uuid4(),
            membership_id=membership.membership_id,
            plant_id=plant.plant_id,
        ) is None
        assert provider(
            farm_id=farm.farm_id,
            membership_id=uuid.uuid4(),
            plant_id=plant.plant_id,
        ) is None

        class FailingDatabase:
            @contextmanager
            def session(self):
                raise RuntimeError("postgresql://admin:plain-secret@localhost/db")
                yield

        failing_actor = ActorContextResolver(
            session_validator=StaticValidator(
                _validated_for(database, membership.membership_id)
            ),
            snapshot_provider=PersistedPlantAccessSnapshotProvider(FailingDatabase()),
        ).resolve(
            request_id="req-failing-provider",
            raw_session_token="synthetic-test-token",
            transport="cookie",
        )
        denied = failing_actor.resolve_plant_permission(
            plant.plant_id, OperationKind.NORMAL_READ
        )
        assert denied.source is PermissionSource.DENIED
        assert "secret" not in repr(denied).lower()


def _validated_for(database, membership_id: uuid.UUID) -> ValidatedSession:
    with database.session() as session:
        membership = session.get(FarmMembership, membership_id)
        account = session.get(Account, membership.account_id)
        local_session = session.scalar(
            select(LocalSession).where(LocalSession.account_id == account.account_id)
        )
        return ValidatedSession(
            session=local_session, account=account, membership=membership
        )


def test_dependency_uses_persisted_provider_by_default_and_preserves_override():
    with _postgres_database() as database:
        request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(database=database))
        )
        provider = get_plant_access_snapshot_provider(request)
        assert isinstance(provider, PersistedPlantAccessSnapshotProvider)

        override = lambda **_kwargs: None
        request.app.state.plant_access_snapshot_provider = override
        assert get_plant_access_snapshot_provider(request) is override


def test_archive_and_archived_grant_interleaving_returns_one_consistent_snapshot():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, _ = _create_actor(database, farm, "boss")
        _engineer, membership = _create_actor(database, farm, "engineer")
        with database.session() as session:
            plant = FarmService(session).create_plant(
                boss, plant_key="race_001", display_name="Race Plant"
            ).plant
        actor = _persisted_actor(database, membership.membership_id)

        query_ready = Event()
        mutation_done = Event()
        worker_ids: list[int] = []
        snapshot_sql: list[str] = []
        permissions = []
        failures: list[BaseException] = []

        def pause_snapshot(_connection, _cursor, statement, _params, _ctx, _many):
            normalized = " ".join(statement.lower().split())
            if (
                worker_ids
                and get_ident() == worker_ids[0]
                and normalized.startswith("select")
                and "left outer join plant_access_grants" in normalized
            ):
                snapshot_sql.append(normalized)
                query_ready.set()
                if not mutation_done.wait(timeout=5):
                    raise RuntimeError("timed out waiting for concurrent mutation")

        def resolve_permission() -> None:
            worker_ids.append(get_ident())
            try:
                permissions.append(
                    actor.resolve_plant_permission(
                        plant.plant_id, OperationKind.NORMAL_READ
                    )
                )
            except BaseException as error:
                failures.append(error)

        event.listen(database.engine(), "before_cursor_execute", pause_snapshot)
        worker = Thread(target=resolve_permission)
        worker.start()
        try:
            assert query_ready.wait(timeout=5)
            with database.session() as session:
                FarmService(session).archive_plant(boss, plant_id=plant.plant_id)
            with database.session() as session:
                FarmService(session).grant_access(
                    boss,
                    plant_id=plant.plant_id,
                    membership_id=membership.membership_id,
                    plant_approve_actions=True,
                )
        finally:
            mutation_done.set()
            worker.join(timeout=5)
            event.remove(database.engine(), "before_cursor_execute", pause_snapshot)

        assert not worker.is_alive()
        assert failures == []
        assert len(snapshot_sql) == 1
        assert len(permissions) == 1
        permission = permissions[0]
        assert permission.plant_status is PlantStatus.ARCHIVED
        assert permission.source is PermissionSource.PLANT_ACCESS_GRANT
        assert permission.can_read is False
        assert permission.can_operate is False
        assert permission.can_approve_actions is False
