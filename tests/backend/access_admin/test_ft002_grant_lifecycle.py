from __future__ import annotations

from collections import Counter

import pytest
from sqlalchemy import event, func, select

from backend.app.access_admin.farm_repository import FarmRepository
from backend.app.access_admin.farm_service import (
    FarmCommandError,
    FarmCommandErrorCode,
    FarmService,
)
from backend.app.access_admin.models import (
    Account,
    AdminAuditRecord,
    FarmMembership,
    PlantAccessGrant,
)
from tests.backend.access_admin.test_ft002_farm_plant_services import (
    _audit_actions,
    _create_actor,
    _postgres_database,
    _seed_farm,
)


def test_grant_lifecycle_preserves_identity_and_exact_noop_audits():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, _ = _create_actor(database, farm, "boss")
        engineer, engineer_membership = _create_actor(database, farm, "engineer")
        with database.session() as session:
            plant = FarmService(session).create_plant(
                boss, plant_key="lettuce_001", display_name="Lettuce"
            ).plant

        with database.session() as session:
            granted = FarmService(session).grant_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=engineer_membership.membership_id,
                plant_approve_actions=False,
            )
        grant_id = granted.entity.grant_id
        first_timestamp = granted.entity.updated_at
        assert granted.changed is True
        assert granted.entity.status == "active"

        with database.session() as session:
            no_op = FarmService(session).grant_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=engineer_membership.membership_id,
                plant_approve_actions=False,
            )
        assert no_op.changed is False
        assert no_op.entity.grant_id == grant_id
        assert no_op.entity.updated_at == first_timestamp

        with database.session() as session:
            updated = FarmService(session).grant_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=engineer_membership.membership_id,
                plant_approve_actions=True,
            )
        assert updated.changed is True
        assert updated.entity.grant_id == grant_id
        assert updated.entity.plant_approve_actions is True

        with database.session() as session:
            revoked = FarmService(session).revoke_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=engineer_membership.membership_id,
            )
        assert revoked.changed is True and revoked.entity.status == "revoked"
        revoke_timestamp = revoked.entity.updated_at
        with database.session() as session:
            repeated_revoke = FarmService(session).revoke_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=engineer_membership.membership_id,
            )
        assert repeated_revoke.changed is False
        assert repeated_revoke.entity.updated_at == revoke_timestamp

        with database.session() as session:
            reactivated = FarmService(session).grant_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=engineer_membership.membership_id,
                plant_approve_actions=False,
            )
        assert reactivated.entity.grant_id == grant_id
        assert reactivated.entity.status == "active"
        assert reactivated.entity.plant_approve_actions is False
        assert Counter(_audit_actions(database)) == Counter(
            {
                "plant_created": 1,
                "plant_access_granted": 2,
                "plant_approve_actions_changed": 1,
                "plant_access_revoked": 1,
            }
        )
        assert engineer.role_preset.value == "engineer"


def test_archived_grant_administration_persists_without_mutating_plant_or_identity():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, _ = _create_actor(database, farm, "boss")
        _engineer, membership = _create_actor(database, farm, "engineer")
        with database.session() as session:
            plant = FarmService(session).create_plant(
                boss, plant_key="mint_001", display_name="Mint"
            ).plant
        with database.session() as session:
            initial = FarmService(session).grant_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=membership.membership_id,
            ).entity
        grant_id = initial.grant_id
        with database.session() as session:
            FarmService(session).archive_plant(boss, plant_id=plant.plant_id)
        with database.session() as session:
            changed = FarmService(session).grant_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=membership.membership_id,
                plant_approve_actions=True,
            )
        assert changed.entity.grant_id == grant_id
        assert changed.entity.status == "active"
        assert changed.entity.plant_approve_actions is True
        with database.session() as session:
            current_plant = session.get(type(plant), plant.plant_id)
            assert current_plant.status == "archived"
        with database.session() as session:
            FarmService(session).restore_plant(boss, plant_id=plant.plant_id)
        with database.session() as session:
            restored_grant = session.get(PlantAccessGrant, grant_id)
            assert restored_grant.status == "active"
            assert restored_grant.plant_approve_actions is True


def test_grant_target_and_role_policy_fail_without_audit_or_partial_grant():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, boss_membership = _create_actor(database, farm, "boss")
        _engineer, engineer_membership = _create_actor(database, farm, "engineer")
        _consultant, consultant_membership = _create_actor(
            database, farm, "consultant"
        )
        with database.session() as session:
            plant = FarmService(session).create_plant(
                boss, plant_key="basil_001", display_name="Basil"
            ).plant
        baseline_audits = len(_audit_actions(database))

        with database.session() as session:
            with pytest.raises(FarmCommandError) as engineer_management:
                FarmService(session).grant_access(
                    _engineer,
                    plant_id=plant.plant_id,
                    membership_id=consultant_membership.membership_id,
                )
        assert engineer_management.value.code is FarmCommandErrorCode.FORBIDDEN

        with database.session() as session:
            with pytest.raises(FarmCommandError) as consultant_flag:
                FarmService(session).grant_access(
                    boss,
                    plant_id=plant.plant_id,
                    membership_id=consultant_membership.membership_id,
                    plant_approve_actions=True,
                )
        assert consultant_flag.value.code is FarmCommandErrorCode.INVALID_INPUT

        with database.session() as session:
            with pytest.raises(FarmCommandError) as boss_target:
                FarmService(session).grant_access(
                    boss,
                    plant_id=plant.plant_id,
                    membership_id=boss_membership.membership_id,
                )
        assert boss_target.value.code is FarmCommandErrorCode.MEMBERSHIP_UNAVAILABLE

        with database.session() as session, session.begin():
            target = session.get(FarmMembership, engineer_membership.membership_id)
            target.membership_status = "disabled"
        with database.session() as session:
            with pytest.raises(FarmCommandError) as disabled:
                FarmService(session).grant_access(
                    boss,
                    plant_id=plant.plant_id,
                    membership_id=engineer_membership.membership_id,
                )
        assert disabled.value.code is FarmCommandErrorCode.MEMBERSHIP_UNAVAILABLE

        with database.session() as session, session.begin():
            target = session.get(FarmMembership, engineer_membership.membership_id)
            target.membership_status = "active"
            account = session.get(Account, target.account_id)
            account.account_status = "disabled"
        with database.session() as session:
            with pytest.raises(FarmCommandError) as disabled_account:
                FarmService(session).grant_access(
                    boss,
                    plant_id=plant.plant_id,
                    membership_id=engineer_membership.membership_id,
                )
        assert (
            disabled_account.value.code
            is FarmCommandErrorCode.MEMBERSHIP_UNAVAILABLE
        )

        assert len(_audit_actions(database)) == baseline_audits
        with database.session() as session:
            assert session.scalar(select(func.count(PlantAccessGrant.grant_id))) == 0


def test_injected_grant_audit_failure_rolls_back_without_raw_error():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, _ = _create_actor(database, farm, "boss")
        _engineer, membership = _create_actor(database, farm, "engineer")
        with database.session() as session:
            plant = FarmService(session).create_plant(
                boss, plant_key="roots_001", display_name="Roots"
            ).plant

        class FailingAuditRepository(FarmRepository):
            def add_account_audit(self, **values) -> None:
                raise RuntimeError("postgresql://admin:plain-secret@localhost/db")

        with database.session() as session:
            with pytest.raises(FarmCommandError) as failure:
                FarmService(
                    session, repository_factory=FailingAuditRepository
                ).grant_access(
                    boss,
                    plant_id=plant.plant_id,
                    membership_id=membership.membership_id,
                )
        assert failure.value.code is FarmCommandErrorCode.PERSISTENCE_FAILED
        assert "plain-secret" not in str(failure.value)
        with database.session() as session:
            assert session.scalar(select(func.count(PlantAccessGrant.grant_id))) == 0
            assert session.scalar(
                select(func.count(AdminAuditRecord.admin_audit_id)).where(
                    AdminAuditRecord.action_type == "plant_access_granted"
                )
            ) == 0


def test_grant_mutation_uses_current_state_row_locks_before_write():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, _ = _create_actor(database, farm, "boss")
        _engineer, membership = _create_actor(database, farm, "engineer")
        with database.session() as session:
            plant = FarmService(session).create_plant(
                boss, plant_key="lock_001", display_name="Lock Test"
            ).plant
        with database.session() as session:
            FarmService(session).grant_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=membership.membership_id,
            )

        statements: list[str] = []

        def capture(_connection, _cursor, statement, _parameters, _context, _many):
            statements.append(" ".join(statement.lower().split()))

        event.listen(database.engine(), "before_cursor_execute", capture)
        try:
            with database.session() as session:
                FarmService(session).grant_access(
                    boss,
                    plant_id=plant.plant_id,
                    membership_id=membership.membership_id,
                    plant_approve_actions=True,
                )
        finally:
            event.remove(database.engine(), "before_cursor_execute", capture)

        locked_selects = [
            statement
            for statement in statements
            if statement.startswith("select") and " for update" in statement
        ]
        assert sum(
            "from accounts join farm_memberships" in item for item in locked_selects
        ) >= 2
        assert any("from plants" in item for item in locked_selects)
        assert any("from plant_access_grants" in item for item in locked_selects)
