from __future__ import annotations

from collections import Counter
import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.app.access_admin.admin_repository import AdminRepository
from backend.app.access_admin.admin_service import (
    AdminCommandError,
    AdminCommandErrorCode,
    AdminService,
)
from backend.app.access_admin.farm_service import FarmService
from backend.app.access_admin.models import (
    Account,
    AdminAuditRecord,
    FarmMembership,
    LocalSession,
    PlantAccessGrant,
)
from backend.app.access_admin.security import verify_password
from tests.backend.access_admin.test_ft002_farm_plant_services import (
    _audit_actions,
    _create_actor,
    _postgres_database,
    _seed_farm,
)


def _count(database, model) -> int:
    with database.session() as session:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)


def test_boss_create_account_commits_account_membership_and_one_safe_audit():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, _boss_membership = _create_actor(database, farm, "boss")

        with database.session() as session:
            result = AdminService(session).create_account(
                boss,
                login_name=" engineer ",
                display_name=" Engineer ",
                password="initial-secret",
                role_preset="engineer",
            )

        assert result.account.login_name == "engineer"
        assert result.account.account_status == "active"
        assert result.membership.role_preset == "engineer"
        assert result.membership.membership_status == "active"
        assert result.account.password_hash.startswith("$argon2id$")
        assert verify_password("initial-secret", result.account.password_hash)

        with database.session() as session:
            audit = session.scalar(
                select(AdminAuditRecord).where(
                    AdminAuditRecord.action_type == "account_created",
                    AdminAuditRecord.target_id == result.account.account_id,
                )
            )
            assert audit is not None
            assert audit.actor_kind == "account"
            assert audit.actor_account_id == boss.account_id
            assert audit.actor_membership_id == boss.membership_id
            assert audit.actor_role_preset == "boss"
            assert audit.after_summary["login_name"] == "engineer"
            assert audit.after_summary["membership"]["role_preset"] == "engineer"
            assert "initial-secret" not in str(audit.after_summary)
            assert "password_hash" not in str(audit.after_summary)
            assert session.scalar(select(func.count(AdminAuditRecord.admin_audit_id))) == 1


def test_create_account_duplicate_and_generic_persistence_failures_are_classified():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, _ = _create_actor(database, farm, "boss")
        with database.session() as session:
            AdminService(session).create_account(
                boss,
                login_name="engineer",
                display_name="Engineer",
                password="initial-secret",
                role_preset="engineer",
            )
        baseline_accounts = _count(database, Account)
        baseline_memberships = _count(database, FarmMembership)
        baseline_audits = _count(database, AdminAuditRecord)

        with database.session() as session:
            with pytest.raises(AdminCommandError) as duplicate:
                AdminService(session).create_account(
                    boss,
                    login_name=" engineer ",
                    display_name="Duplicate",
                    password="other-secret",
                    role_preset="engineer",
                )
        assert duplicate.value.code is AdminCommandErrorCode.ACCOUNT_CONFLICT

        class UnknownDiagnostic:
            constraint_name = "some_other_constraint"

        class UnknownIntegrityViolation(Exception):
            diag = UnknownDiagnostic()

        class FailingRepository(AdminRepository):
            def flush(self) -> None:
                raise IntegrityError(
                    "redacted statement",
                    {},
                    UnknownIntegrityViolation("password=hidden"),
                )

        with database.session() as session:
            with pytest.raises(AdminCommandError) as generic:
                AdminService(
                    session, repository_factory=FailingRepository
                ).create_account(
                    boss,
                    login_name="new-engineer",
                    display_name="New Engineer",
                    password="other-secret",
                    role_preset="engineer",
                )
        assert generic.value.code is AdminCommandErrorCode.PERSISTENCE_FAILED
        assert "hidden" not in str(generic.value)

        assert _count(database, Account) == baseline_accounts
        assert _count(database, FarmMembership) == baseline_memberships
        assert _count(database, AdminAuditRecord) == baseline_audits


def test_disable_and_role_change_enforce_last_active_boss_and_exact_audits():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, boss_membership = _create_actor(database, farm, "boss")

        with database.session() as session:
            with pytest.raises(AdminCommandError) as last_disable:
                AdminService(session).disable_account(
                    boss, account_id=boss.account_id, reason="owner request"
                )
        assert last_disable.value.code is AdminCommandErrorCode.LAST_BOSS_CONFLICT

        with database.session() as session:
            with pytest.raises(AdminCommandError) as last_demote:
                AdminService(session).change_membership_role(
                    boss,
                    membership_id=boss_membership.membership_id,
                    role_preset="engineer",
                )
        assert last_demote.value.code is AdminCommandErrorCode.LAST_BOSS_CONFLICT
        assert _count(database, AdminAuditRecord) == 0

        second_boss, second_membership = _create_actor(database, farm, "boss")
        with database.session() as session:
            demoted = AdminService(session).change_membership_role(
                boss,
                membership_id=second_membership.membership_id,
                role_preset="engineer",
            )
        assert demoted.changed is True
        assert demoted.membership.role_preset == "engineer"

        with database.session() as session:
            disabled = AdminService(session).disable_account(
                boss,
                account_id=second_boss.account_id,
                reason="password=should-not-persist",
            )
        assert disabled.changed is True
        assert disabled.account.account_status == "disabled"

        with database.session() as session:
            actions = list(
                session.scalars(
                    select(AdminAuditRecord.action_type).order_by(
                        AdminAuditRecord.created_at, AdminAuditRecord.admin_audit_id
                    )
                )
            )
            disabled_audit = session.scalar(
                select(AdminAuditRecord).where(
                    AdminAuditRecord.action_type == "account_disabled"
                )
            )
        assert actions == ["membership_role_changed", "account_disabled"]
        assert disabled_audit.after_summary["reason"] == "[redacted]"
        assert "should-not-persist" not in str(disabled_audit.after_summary)


def test_admin_reads_return_safe_personnel_plant_projection_and_audit_summary():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, _ = _create_actor(database, farm, "boss")
        _engineer, engineer_membership = _create_actor(database, farm, "engineer")
        with database.session() as session:
            plant = FarmService(session).create_plant(
                boss, plant_key="mint_001", display_name="Mint"
            ).plant
        with database.session() as session:
            FarmService(session).grant_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=engineer_membership.membership_id,
                plant_approve_actions=True,
            )

        with database.session() as session:
            service = AdminService(session)
            personnel = service.list_personnel(boss, role_preset="engineer")
            projections = service.list_plant_projections(boss)
            audits = service.list_audit(boss, limit=10)

        assert [item.membership.role_preset for item in personnel] == ["engineer"]
        assert all("password_hash" not in str(item) for item in personnel)
        assert len(projections) == 1
        assert projections[0].plant.plant_key == "mint_001"
        assert projections[0].grant_counts == {
            "active": 1,
            "revoked": 0,
            "approve_actions_enabled": 1,
        }
        assert Counter(item["action_type"] for item in audits) == Counter(
            ["plant_created", "plant_access_granted"]
        )
        assert all("password_hash" not in str(item) for item in audits)


def test_non_boss_admin_service_access_is_denied_without_mutation():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        _boss, _ = _create_actor(database, farm, "boss")
        engineer, _ = _create_actor(database, farm, "engineer")
        baseline = _count(database, AdminAuditRecord)

        with database.session() as session:
            with pytest.raises(AdminCommandError) as denied:
                AdminService(session).create_account(
                    engineer,
                    login_name="consultant",
                    display_name="Consultant",
                    password="initial-secret",
                    role_preset="consultant",
                )
        assert denied.value.code is AdminCommandErrorCode.FORBIDDEN
        assert _count(database, AdminAuditRecord) == baseline
        with database.session() as session:
            assert session.scalar(
                select(func.count(Account.account_id)).where(
                    Account.login_name == "consultant"
                )
            ) == 0


def test_admin_service_does_not_create_sessions_for_new_accounts():
    with _postgres_database() as database:
        farm = _seed_farm(database)
        boss, _ = _create_actor(database, farm, "boss")
        baseline_sessions = _count(database, LocalSession)

        with database.session() as session:
            AdminService(session).create_account(
                boss,
                login_name="engineer",
                display_name="Engineer",
                password="initial-secret",
                role_preset="engineer",
            )

        assert _count(database, LocalSession) == baseline_sessions
        assert _audit_actions(database) == ["account_created"]
