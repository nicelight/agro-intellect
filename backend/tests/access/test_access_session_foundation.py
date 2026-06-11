from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from backend.app.access import (
    Account,
    AccountStatus,
    Farm,
    FarmMembership,
    MembershipRole,
    MembershipStatus,
    SessionValidationState,
    create_local_session,
    revoke_local_session,
    validate_local_session,
)
from backend.tests.doubles import FakeAccessRepository, OneFarmViolation
from backend.app.security import (
    AUTH_MATERIAL_REDACTION_MARKER,
    hash_session_secret,
    redact_auth_payload,
)
from backend.app.security.session_refs import (
    auth_provenance_ref_from_hash,
    generate_session_secret,
    session_ref_from_hash,
)


NOW = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)


async def build_repo(
    *,
    account_status: AccountStatus = AccountStatus.ACTIVE,
    membership_status: MembershipStatus = MembershipStatus.ACTIVE,
) -> FakeAccessRepository:
    repo = FakeAccessRepository()
    await repo.add_account(
        Account(
            account_id="acct_boss",
            display_name="Boss",
            login_identifier="boss.local",
            status=account_status,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    await repo.add_farm(
        Farm(
            farm_id="farm_local",
            display_name="Local Farm",
            created_at=NOW,
            updated_at=NOW,
        )
    )
    await repo.add_membership(
        FarmMembership(
            membership_id="mbr_boss",
            account_id="acct_boss",
            farm_id="farm_local",
            role=MembershipRole.BOSS,
            status=membership_status,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    return repo


async def test_account_membership_and_session_lifecycle_resolves_with_redacted_refs():
    repo = await build_repo()
    session, raw_secret = await create_local_session(
        repo,
        account_id="acct_boss",
        now=NOW,
        raw_session_secret=generate_session_secret(),
        request_ref="req-bootstrap",
    )

    result = await validate_local_session(repo, raw_secret, now=NOW + timedelta(minutes=1))

    assert result.state is SessionValidationState.RESOLVED
    assert result.account_id == "acct_boss"
    assert result.farm_id == "farm_local"
    assert result.membership_id == "mbr_boss"
    assert result.role is MembershipRole.BOSS
    assert session.to_safe_dict()["session_ref"].startswith("sess_ref_")
    assert result.to_safe_dict()["auth_provenance_ref"].startswith("auth_ref_")
    assert raw_secret not in repr(session)
    assert raw_secret not in repr(result)
    assert raw_secret not in str(session.to_safe_dict())
    assert raw_secret not in str(result.to_safe_dict())

    revoked = await revoke_local_session(repo, session.session_id, now=NOW + timedelta(hours=1))
    denied = await validate_local_session(repo, raw_secret, now=NOW + timedelta(hours=1))

    assert revoked.revoked_at == NOW + timedelta(hours=1)
    assert denied.state is SessionValidationState.DENIED
    assert denied.reason == "revoked_session"


@pytest.mark.parametrize(
    ("raw_secret", "expected_state", "expected_reason"),
    [
        (None, SessionValidationState.DENIED, "missing_session"),
        ("", SessionValidationState.DENIED, "missing_session"),
        ("short", SessionValidationState.DENIED, "malformed_session"),
        (
            "wellformed-invalid-session-secret-value-12345",
            SessionValidationState.DENIED,
            "invalid_session",
        ),
    ],
)
async def test_missing_malformed_or_invalid_session_fails_closed(
    raw_secret,
    expected_state,
    expected_reason,
):
    repo = await build_repo()

    result = await validate_local_session(repo, raw_secret, now=NOW)

    assert result.state is expected_state
    assert result.reason == expected_reason
    assert not result.is_resolved
    assert result.account_id is None
    assert result.farm_id is None
    assert result.membership_id is None


async def test_expired_session_fails_closed_with_expired_state():
    repo = await build_repo()
    _session, raw_secret = await create_local_session(
        repo,
        account_id="acct_boss",
        now=NOW,
        ttl=timedelta(minutes=5),
        raw_session_secret=generate_session_secret(),
    )

    result = await validate_local_session(repo, raw_secret, now=NOW + timedelta(minutes=6))

    assert result.state is SessionValidationState.EXPIRED
    assert result.reason == "expired_session"
    assert not result.is_resolved


async def test_disabled_account_fails_closed_even_with_valid_session():
    repo = await build_repo()
    _session, raw_secret = await create_local_session(
        repo,
        account_id="acct_boss",
        now=NOW,
        raw_session_secret=generate_session_secret(),
    )
    await repo.update_account_status("acct_boss", AccountStatus.DISABLED)

    result = await validate_local_session(repo, raw_secret, now=NOW + timedelta(minutes=1))

    assert result.state is SessionValidationState.DENIED
    assert result.reason == "inactive_account"
    assert not result.is_resolved


@pytest.mark.parametrize(
    "membership_status",
    [MembershipStatus.DISABLED, MembershipStatus.REMOVED],
)
async def test_disabled_or_removed_membership_fails_closed(membership_status):
    repo = await build_repo()
    _session, raw_secret = await create_local_session(
        repo,
        account_id="acct_boss",
        now=NOW,
        raw_session_secret=generate_session_secret(),
    )
    await repo.update_membership_status("mbr_boss", membership_status)

    result = await validate_local_session(repo, raw_secret, now=NOW + timedelta(minutes=1))

    assert result.state is SessionValidationState.DENIED
    assert result.reason == "inactive_membership"
    assert not result.is_resolved


async def test_one_farm_assumption_blocks_second_local_farm():
    repo = await build_repo()

    with pytest.raises(OneFarmViolation):
        await repo.add_farm(Farm(farm_id="farm_second", display_name="Second Farm"))


async def test_multi_farm_membership_is_forbidden_even_if_repository_is_corrupted():
    repo = await build_repo()
    repo.farms["farm_second"] = Farm(farm_id="farm_second", display_name="Second Farm")

    with pytest.raises(OneFarmViolation):
        await repo.add_membership(
            FarmMembership(
                membership_id="mbr_second",
                account_id="acct_boss",
                farm_id="farm_second",
                role=MembershipRole.CONSULTANT,
            )
        )


def test_session_hashes_and_refs_do_not_expose_raw_auth_material():
    raw_secret = "session-secret-with-enough-entropy-123456789"
    session_hash = hash_session_secret(raw_secret)
    session_ref = session_ref_from_hash(session_hash)
    auth_ref = auth_provenance_ref_from_hash(session_hash)

    assert session_hash != raw_secret
    assert raw_secret not in session_hash
    assert raw_secret not in session_ref
    assert raw_secret not in auth_ref
    assert session_ref.startswith("sess_ref_")
    assert auth_ref.startswith("auth_ref_")


def test_redaction_helper_removes_auth_material_from_foundation_surfaces():
    raw_secret = "session-secret-with-enough-entropy-abcdef123456"
    payload = {
        "message": f"login used {raw_secret}",
        "session_token": raw_secret,
        "nested": {
            "Authorization": f"Bearer {raw_secret}",
            "safe_ref": "sess_ref_1234567890abcdef",
        },
    }

    redacted = redact_auth_payload(payload, sensitive_values=(raw_secret,))

    assert raw_secret not in str(redacted)
    assert redacted["session_token"] == AUTH_MATERIAL_REDACTION_MARKER
    assert redacted["nested"]["Authorization"] == AUTH_MATERIAL_REDACTION_MARKER
    assert redacted["nested"]["safe_ref"] == "sess_ref_1234567890abcdef"


async def test_validate_fails_closed_when_session_membership_link_is_invalid():
    repo = await build_repo()
    session, raw_secret = await create_local_session(
        repo,
        account_id="acct_boss",
        now=NOW,
        raw_session_secret=generate_session_secret(),
    )
    corrupted = replace(session, membership_id="missing_membership")
    repo.sessions_by_id[session.session_id] = corrupted
    repo.sessions_by_hash[session.session_hash] = corrupted

    result = await validate_local_session(repo, raw_secret, now=NOW + timedelta(minutes=1))

    assert result.state is SessionValidationState.DENIED
    assert result.reason == "inactive_membership"
