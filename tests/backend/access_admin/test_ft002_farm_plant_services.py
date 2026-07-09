from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from backend.app import AppSettings
from backend.app.access_admin.actor_context import ActorContextResolver, AuthTransport
from backend.app.access_admin.farm_repository import FarmRepository
from backend.app.access_admin.farm_service import (
    FarmCommandError,
    FarmCommandErrorCode,
    FarmService,
)
from backend.app.access_admin.models import (
    Account,
    AdminAuditRecord,
    Farm,
    FarmMembership,
    LocalSession,
    Plant,
    PlantAccessGrant,
)
from backend.app.access_admin.permissions import ROLE_POLICIES, RolePreset
from backend.app.access_admin.session_service import ValidatedSession
from backend.app.database import DatabaseHandle, build_database
from backend.migrations import build_alembic_config


class StaticValidator:
    def __init__(self, validated: ValidatedSession) -> None:
        self.validated = validated

    def validate_session(self, _token: object) -> ValidatedSession:
        return self.validated


@contextmanager
def _postgres_database():
    settings = AppSettings.from_env()
    base = build_database(settings)
    schema = f"task013_service_{uuid.uuid4().hex}"
    scoped: DatabaseHandle | None = None
    try:
        assert base.engine().dialect.name == "postgresql"
        with base.engine().connect() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.commit()
        url = make_url(settings.database_url).update_query_dict(
            {"options": f"-csearch_path={schema},public"}
        )
        scoped_settings = settings.model_copy(
            update={"database_url": url.render_as_string(hide_password=False)}
        )
        scoped = build_database(scoped_settings)
        script = ScriptDirectory.from_config(build_alembic_config(settings))
        with scoped.engine().connect() as connection:
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                script.get_revision("ft001_access_sessions").module.upgrade()
                script.get_revision("ft002_farm_plant_access").module.upgrade()
            connection.commit()
        yield scoped
    finally:
        if scoped is not None:
            scoped.dispose()
        with base.engine().connect() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            connection.commit()
        base.dispose()


def _seed_farm(database: DatabaseHandle) -> Farm:
    with database.session() as session, session.begin():
        farm = Farm(farm_key="local_farm", display_name="Local Farm")
        session.add(farm)
        session.flush()
        return farm


def _create_actor(
    database: DatabaseHandle,
    farm: Farm,
    role: str,
    *,
    membership_status: str = "active",
):
    with database.session() as session, session.begin():
        account = Account(
            login_name=f"{role}-{uuid.uuid4().hex}",
            display_name=f"{role.title()} User",
            account_status="active",
            password_hash="test-only-hash",
        )
        session.add(account)
        session.flush()
        membership = FarmMembership(
            account_id=account.account_id,
            farm_id=farm.farm_id,
            role_preset=role,
            membership_status=membership_status,
        )
        session.add(membership)
        session.flush()
        now = datetime.now(timezone.utc)
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
            session=local_session, account=account, membership=membership
        )
        actor = ActorContextResolver(
            session_validator=StaticValidator(validated),
            snapshot_provider=lambda **_kwargs: None,
        ).resolve(
            request_id=f"req-{role}",
            raw_session_token="synthetic-test-token",
            transport=AuthTransport.COOKIE,
        )
        return actor, membership


def _audit_actions(database: DatabaseHandle) -> list[str]:
    with database.session() as session:
        return list(
            session.scalars(
                select(AdminAuditRecord.action_type).order_by(
                    AdminAuditRecord.created_at, AdminAuditRecord.admin_audit_id
                )
            )
        )


def test_role_policy_exposes_creation_and_lifecycle_authority():
    assert ROLE_POLICIES[RolePreset.BOSS].can_create_plants is True
    assert ROLE_POLICIES[RolePreset.BOSS].can_manage_lifecycle is True
    assert ROLE_POLICIES[RolePreset.ENGINEER].can_create_plants is True
    assert ROLE_POLICIES[RolePreset.ENGINEER].can_manage_lifecycle is False
    assert ROLE_POLICIES[RolePreset.CONSULTANT].can_create_plants is False
    assert ROLE_POLICIES[RolePreset.CONSULTANT].can_manage_lifecycle is False


def test_boss_farm_display_and_plant_create_are_audited_without_synthetic_grant():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, _membership = _create_actor(database, farm, "boss")
        with database.session() as session:
            service = FarmService(session)
            changed = service.change_farm_display_name(
                boss, display_name="  Production Farm  "
            )
        with database.session() as session:
            created = FarmService(session).create_plant(
                boss, plant_key="lettuce_001", display_name="Lettuce 001"
            )
        assert changed.changed is True
        assert changed.entity.display_name == "Production Farm"
        assert created.creator_grant is None
        assert Counter(_audit_actions(database)) == Counter(
            ["farm_display_name_changed", "plant_created"]
        )
        with database.session() as session:
            assert session.scalar(select(func.count(PlantAccessGrant.grant_id))) == 0

        timestamp = changed.entity.updated_at
        with database.session() as session:
            repeated = FarmService(session).change_farm_display_name(
                boss, display_name="Production Farm"
            )
        assert repeated.changed is False
        assert repeated.entity.updated_at == timestamp
        assert len(_audit_actions(database)) == 2


def test_engineer_create_commits_creator_grant_and_two_audits_atomically():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        engineer, membership = _create_actor(database, farm, "engineer")
        with database.session() as session:
            result = FarmService(session).create_plant(
                engineer,
                plant_key="lettuce_001",
                display_name="Lettuce 001",
            )
        assert result.plant.status == "active"
        assert result.creator_grant is not None
        assert result.creator_grant.membership_id == membership.membership_id
        assert result.creator_grant.status == "active"
        assert result.creator_grant.plant_approve_actions is False
        assert Counter(_audit_actions(database)) == Counter(
            ["plant_created", "plant_access_granted"]
        )


def test_create_policy_invalid_key_duplicate_and_disabled_current_state_fail_closed():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        engineer, membership = _create_actor(database, farm, "engineer")
        consultant, _ = _create_actor(database, farm, "consultant")
        with database.session() as session:
            with pytest.raises(FarmCommandError) as denied:
                FarmService(session).create_plant(
                    consultant, plant_key="basil_001", display_name="Basil"
                )
        assert denied.value.code is FarmCommandErrorCode.FORBIDDEN

        with database.session() as session:
            with pytest.raises(FarmCommandError) as invalid:
                FarmService(session).create_plant(
                    engineer, plant_key="Bad-Key", display_name="Bad"
                )
        assert invalid.value.code is FarmCommandErrorCode.INVALID_INPUT

        with database.session() as session:
            FarmService(session).create_plant(
                engineer, plant_key="basil_001", display_name="Basil"
            )
        with database.session() as session:
            with pytest.raises(FarmCommandError) as duplicate:
                FarmService(session).create_plant(
                    engineer, plant_key="basil_001", display_name="Duplicate"
                )
        assert duplicate.value.code is FarmCommandErrorCode.CONFLICT

        with database.session() as session, session.begin():
            current = session.get(FarmMembership, membership.membership_id)
            current.membership_status = "disabled"
        with database.session() as session:
            with pytest.raises(FarmCommandError) as stale:
                FarmService(session).create_plant(
                    engineer, plant_key="mint_001", display_name="Mint"
                )
        assert stale.value.code is FarmCommandErrorCode.FORBIDDEN
        with database.session() as session:
            assert session.scalar(
                select(func.count(Plant.plant_id)).where(Plant.plant_key == "mint_001")
            ) == 0


def test_rename_archive_restore_preserve_grants_and_noop_evidence():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, _ = _create_actor(database, farm, "boss")
        engineer, membership = _create_actor(database, farm, "engineer")
        consultant, consultant_membership = _create_actor(
            database, farm, "consultant"
        )
        with database.session() as session:
            created = FarmService(session).create_plant(
                engineer, plant_key="mint_001", display_name="Mint"
            )
        with database.session() as session:
            FarmService(session).grant_access(
                boss,
                plant_id=created.plant.plant_id,
                membership_id=consultant_membership.membership_id,
            )
        grant_id = created.creator_grant.grant_id
        grant_state = (
            created.creator_grant.status,
            created.creator_grant.plant_approve_actions,
        )
        with database.session() as session:
            renamed = FarmService(session).rename_plant(
                engineer, plant_id=created.plant.plant_id, display_name="Fresh Mint"
            )
        assert renamed.changed and renamed.entity.display_name == "Fresh Mint"

        with database.session() as session:
            with pytest.raises(FarmCommandError) as consultant_rename:
                FarmService(session).rename_plant(
                    consultant,
                    plant_id=created.plant.plant_id,
                    display_name="Consultant Rename",
                )
        assert consultant_rename.value.code is FarmCommandErrorCode.PLANT_UNAVAILABLE
        with database.session() as session:
            with pytest.raises(FarmCommandError) as engineer_archive:
                FarmService(session).archive_plant(
                    engineer, plant_id=created.plant.plant_id
                )
        assert engineer_archive.value.code is FarmCommandErrorCode.FORBIDDEN

        with database.session() as session:
            archived = FarmService(session).archive_plant(
                boss, plant_id=created.plant.plant_id
            )
        assert archived.changed and archived.entity.status == "archived"
        archived_timestamp = archived.entity.updated_at
        with database.session() as session:
            repeated = FarmService(session).archive_plant(
                boss, plant_id=created.plant.plant_id
            )
        assert repeated.changed is False
        assert repeated.entity.updated_at == archived_timestamp
        with database.session() as session:
            with pytest.raises(FarmCommandError) as denied:
                FarmService(session).rename_plant(
                    engineer,
                    plant_id=created.plant.plant_id,
                    display_name="Archived Rename",
                )
        assert denied.value.code is FarmCommandErrorCode.PLANT_UNAVAILABLE

        with database.session() as session:
            restored = FarmService(session).restore_plant(
                boss, plant_id=created.plant.plant_id
            )
        assert restored.changed and restored.entity.status == "active"
        with database.session() as session:
            grant = session.get(PlantAccessGrant, grant_id)
            assert grant.membership_id == membership.membership_id
            assert (grant.status, grant.plant_approve_actions) == grant_state


def test_injected_second_audit_failure_rolls_back_engineer_create():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        engineer, _ = _create_actor(database, farm, "engineer")

        class FailingSecondAuditRepository(FarmRepository):
            calls = 0

            def add_account_audit(self, **values) -> None:
                type(self).calls += 1
                if type(self).calls == 2:
                    raise RuntimeError("synthetic audit failure with secret=hidden")
                super().add_account_audit(**values)

        with database.session() as session:
            with pytest.raises(FarmCommandError) as failure:
                FarmService(
                    session, repository_factory=FailingSecondAuditRepository
                ).create_plant(
                    engineer, plant_key="rollback_001", display_name="Rollback"
                )
        assert failure.value.code is FarmCommandErrorCode.PERSISTENCE_FAILED
        assert "hidden" not in str(failure.value)
        with database.session() as session:
            assert session.scalar(
                select(func.count(Plant.plant_id)).where(
                    Plant.plant_key == "rollback_001"
                )
            ) == 0
            assert session.scalar(select(func.count(PlantAccessGrant.grant_id))) == 0
            assert session.scalar(select(func.count(AdminAuditRecord.admin_audit_id))) == 0


def test_named_plant_key_unique_race_is_the_only_integrity_conflict():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, _ = _create_actor(database, farm, "boss")

        class ConstraintDiagnostic:
            constraint_name = "uq_plants_farm_plant_key"

        class NamedUniqueViolation(Exception):
            diag = ConstraintDiagnostic()

        class NamedRaceRepository(FarmRepository):
            def flush(self) -> None:
                raise IntegrityError(
                    "redacted statement",
                    {},
                    NamedUniqueViolation("secret=hidden"),
                )

        with database.session() as session:
            with pytest.raises(FarmCommandError) as conflict:
                FarmService(
                    session,
                    repository_factory=NamedRaceRepository,
                ).create_plant(
                    boss,
                    plant_key="race_001",
                    display_name="Race",
                )
        assert conflict.value.code is FarmCommandErrorCode.CONFLICT
        assert "hidden" not in str(conflict.value)

        class UnknownDiagnostic:
            constraint_name = "some_other_constraint"

        class UnknownIntegrityViolation(Exception):
            diag = UnknownDiagnostic()

        class UnknownIntegrityRepository(FarmRepository):
            def flush(self) -> None:
                raise IntegrityError(
                    "redacted statement",
                    {},
                    UnknownIntegrityViolation("password=hidden"),
                )

        with database.session() as session:
            with pytest.raises(FarmCommandError) as generic:
                FarmService(
                    session,
                    repository_factory=UnknownIntegrityRepository,
                ).create_plant(
                    boss,
                    plant_key="unknown_001",
                    display_name="Unknown",
                )
        assert generic.value.code is FarmCommandErrorCode.PERSISTENCE_FAILED
        assert "hidden" not in str(generic.value)

        with database.session() as session:
            assert session.scalar(
                select(func.count(Plant.plant_id)).where(
                    Plant.plant_key.in_(["race_001", "unknown_001"])
                )
            ) == 0
            assert session.scalar(select(func.count(AdminAuditRecord.admin_audit_id))) == 0
