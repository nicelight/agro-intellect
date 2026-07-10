from __future__ import annotations

from pathlib import Path
import subprocess

import pytest
from sqlalchemy import func, select

from backend.app.access_admin.admin_repository import AdminRepository
from backend.app.access_admin.admin_service import (
    AdminCommandError,
    AdminCommandErrorCode,
    AdminService,
)
from backend.app.access_admin.models import (
    Account,
    AdminAuditRecord,
    Farm,
    FarmMembership,
    LocalSession,
)
from backend.app.access_admin.security import verify_password
from tests.backend.access_admin.test_ft002_farm_plant_services import (
    _postgres_database,
    _seed_farm,
)


def _counts(database) -> tuple[int, int, int, int]:
    with database.session() as session:
        return (
            int(session.scalar(select(func.count(Account.account_id))) or 0),
            int(session.scalar(select(func.count(FarmMembership.membership_id))) or 0),
            int(session.scalar(select(func.count(AdminAuditRecord.admin_audit_id))) or 0),
            int(session.scalar(select(func.count(LocalSession.session_id))) or 0),
        )


def test_first_boss_bootstrap_requires_existing_canonical_farm_without_mutation():
    with _postgres_database() as database:
        with database.session() as session:
            with pytest.raises(AdminCommandError) as missing:
                AdminService(session).bootstrap_first_boss(
                    login_name="boss",
                    display_name="Boss",
                    password="first-secret",
                )
        assert missing.value.code is AdminCommandErrorCode.FARM_NOT_INITIALIZED
        assert _counts(database) == (0, 0, 0, 0)

        class ConflictingFarmRepository(AdminRepository):
            def lock_farms(self):
                return [
                    Farm(farm_key="local_farm", display_name="Local Farm"),
                    Farm(farm_key="local_farm", display_name="Duplicate Farm"),
                ]

        with database.session() as session:
            with pytest.raises(AdminCommandError) as conflict:
                AdminService(
                    session, repository_factory=ConflictingFarmRepository
                ).bootstrap_first_boss(
                    login_name="boss",
                    display_name="Boss",
                    password="first-secret",
                )
        assert conflict.value.code is AdminCommandErrorCode.FARM_STATE_CONFLICT
        assert _counts(database) == (0, 0, 0, 0)


def test_first_boss_bootstrap_creates_one_boss_audit_and_no_session():
    with _postgres_database() as database:
        farm = _seed_farm(database)

        with database.session() as session:
            result = AdminService(session).bootstrap_first_boss(
                login_name=" Boss ",
                display_name=" Local Boss ",
                password="first-secret",
            )

        assert result.account.login_name == "boss"
        assert result.account.display_name == "Local Boss"
        assert result.account.account_status == "active"
        assert result.account.password_hash.startswith("$argon2id$")
        assert verify_password("first-secret", result.account.password_hash)
        assert result.membership.farm_id == farm.farm_id
        assert result.membership.role_preset == "boss"
        assert result.membership.membership_status == "active"

        with database.session() as session:
            audits = list(session.scalars(select(AdminAuditRecord)))
            sessions = list(session.scalars(select(LocalSession)))
        assert sessions == []
        assert len(audits) == 1
        audit = audits[0]
        assert audit.action_type == "account_created"
        assert audit.actor_kind == "system_bootstrap"
        assert audit.actor_account_id is None
        assert audit.actor_membership_id is None
        assert audit.actor_role_preset is None
        assert audit.after_summary["login_name"] == "boss"
        assert audit.after_summary["membership"]["role_preset"] == "boss"
        assert "first-secret" not in str(audit.after_summary)
        assert "password_hash" not in str(audit.after_summary)

        before_repeat = _counts(database)
        with database.session() as session:
            with pytest.raises(AdminCommandError) as repeated:
                AdminService(session).bootstrap_first_boss(
                    login_name="second-boss",
                    display_name="Second Boss",
                    password="second-secret",
                )
        assert repeated.value.code is AdminCommandErrorCode.LAST_BOSS_CONFLICT
        assert _counts(database) == before_repeat


def test_first_boss_duplicate_login_and_audit_failure_roll_back_without_leakage():
    with _postgres_database() as database:
        _seed_farm(database)
        with database.session() as session, session.begin():
            session.add(
                Account(
                    login_name="boss",
                    display_name="Existing Boss",
                    account_status="active",
                    password_hash="test-only-hash",
                )
            )
        baseline = _counts(database)

        with database.session() as session:
            with pytest.raises(AdminCommandError) as duplicate:
                AdminService(session).bootstrap_first_boss(
                    login_name=" boss ",
                    display_name="Boss",
                    password="first-secret",
                )
        assert duplicate.value.code is AdminCommandErrorCode.ACCOUNT_CONFLICT
        assert _counts(database) == baseline

    with _postgres_database() as database:
        _seed_farm(database)

        class FailingAuditRepository(AdminRepository):
            def add_system_audit(self, **values) -> None:
                raise RuntimeError("postgresql://admin:plain-secret@localhost/db")

        with database.session() as session:
            with pytest.raises(AdminCommandError) as failure:
                AdminService(
                    session, repository_factory=FailingAuditRepository
                ).bootstrap_first_boss(
                    login_name="boss",
                    display_name="Boss",
                    password="first-secret",
                )
        assert failure.value.code is AdminCommandErrorCode.PERSISTENCE_FAILED
        assert "plain-secret" not in str(failure.value)
        assert _counts(database) == (0, 0, 0, 0)


def test_first_boss_script_uses_getpass_only_and_redacts_unsupported_arguments():
    script = Path("scripts/bootstrap-first-boss-local.sh")
    assert script.stat().st_mode & 0o111
    source = script.read_text(encoding="utf-8")
    assert "set -x" not in source
    assert "cat .env" not in source
    assert "getpass.getpass" in source
    assert "FIRST_BOSS_PASSWORD" not in source
    assert "--password" not in source

    dry_run = subprocess.run(
        ["bash", str(script), "--dry-run"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert dry_run.returncode == 0
    assert "would inspect canonical Farm" in dry_run.stdout
    assert "password" not in dry_run.stdout.lower()

    rejected = subprocess.run(
        ["bash", str(script), "--password=plain-secret"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode == 2
    assert "plain-secret" not in rejected.stdout + rejected.stderr
