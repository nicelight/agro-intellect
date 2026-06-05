from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from backend.app.access import (
    Account,
    AccountStatus,
    Farm,
    FarmMembership,
    InMemoryAccessRepository,
    MembershipRole,
    MembershipStatus,
    OneFarmViolation,
    SessionValidationState,
    create_local_session,
    revoke_local_session,
    validate_local_session,
)
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


def build_repo(
    *,
    account_status: AccountStatus = AccountStatus.ACTIVE,
    membership_status: MembershipStatus = MembershipStatus.ACTIVE,
) -> InMemoryAccessRepository:
    repo = InMemoryAccessRepository()
    repo.add_account(
        Account(
            account_id="acct_boss",
            display_name="Boss",
            login_identifier="boss.local",
            status=account_status,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    repo.add_farm(
        Farm(
            farm_id="farm_local",
            display_name="Local Farm",
            created_at=NOW,
            updated_at=NOW,
        )
    )
    repo.add_membership(
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


def test_account_membership_and_session_lifecycle_resolves_with_redacted_refs():
    repo = build_repo()
    session, raw_secret = create_local_session(
        repo,
        account_id="acct_boss",
        now=NOW,
        raw_session_secret=generate_session_secret(),
        request_ref="req-bootstrap",
    )

    result = validate_local_session(repo, raw_secret, now=NOW + timedelta(minutes=1))

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

    revoked = revoke_local_session(repo, session.session_id, now=NOW + timedelta(hours=1))
    denied = validate_local_session(repo, raw_secret, now=NOW + timedelta(hours=1))

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
def test_missing_malformed_or_invalid_session_fails_closed(
    raw_secret,
    expected_state,
    expected_reason,
):
    repo = build_repo()

    result = validate_local_session(repo, raw_secret, now=NOW)

    assert result.state is expected_state
    assert result.reason == expected_reason
    assert not result.is_resolved
    assert result.account_id is None
    assert result.farm_id is None
    assert result.membership_id is None


def test_expired_session_fails_closed_with_expired_state():
    repo = build_repo()
    _session, raw_secret = create_local_session(
        repo,
        account_id="acct_boss",
        now=NOW,
        ttl=timedelta(minutes=5),
        raw_session_secret=generate_session_secret(),
    )

    result = validate_local_session(repo, raw_secret, now=NOW + timedelta(minutes=6))

    assert result.state is SessionValidationState.EXPIRED
    assert result.reason == "expired_session"
    assert not result.is_resolved


def test_disabled_account_fails_closed_even_with_valid_session():
    repo = build_repo()
    _session, raw_secret = create_local_session(
        repo,
        account_id="acct_boss",
        now=NOW,
        raw_session_secret=generate_session_secret(),
    )
    repo.update_account_status("acct_boss", AccountStatus.DISABLED)

    result = validate_local_session(repo, raw_secret, now=NOW + timedelta(minutes=1))

    assert result.state is SessionValidationState.DENIED
    assert result.reason == "inactive_account"
    assert not result.is_resolved


@pytest.mark.parametrize(
    "membership_status",
    [MembershipStatus.DISABLED, MembershipStatus.REMOVED],
)
def test_disabled_or_removed_membership_fails_closed(membership_status):
    repo = build_repo()
    _session, raw_secret = create_local_session(
        repo,
        account_id="acct_boss",
        now=NOW,
        raw_session_secret=generate_session_secret(),
    )
    repo.update_membership_status("mbr_boss", membership_status)

    result = validate_local_session(repo, raw_secret, now=NOW + timedelta(minutes=1))

    assert result.state is SessionValidationState.DENIED
    assert result.reason == "inactive_membership"
    assert not result.is_resolved


def test_one_farm_assumption_blocks_second_local_farm():
    repo = build_repo()

    with pytest.raises(OneFarmViolation):
        repo.add_farm(Farm(farm_id="farm_second", display_name="Second Farm"))


def test_multi_farm_membership_is_forbidden_even_if_repository_is_corrupted():
    repo = build_repo()
    repo.farms["farm_second"] = Farm(farm_id="farm_second", display_name="Second Farm")

    with pytest.raises(OneFarmViolation):
        repo.add_membership(
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


def test_validate_fails_closed_when_session_membership_link_is_invalid():
    repo = build_repo()
    session, raw_secret = create_local_session(
        repo,
        account_id="acct_boss",
        now=NOW,
        raw_session_secret=generate_session_secret(),
    )
    corrupted = replace(session, membership_id="missing_membership")
    repo.sessions_by_id[session.session_id] = corrupted
    repo.sessions_by_hash[session.session_hash] = corrupted

    result = validate_local_session(repo, raw_secret, now=NOW + timedelta(minutes=1))

    assert result.state is SessionValidationState.DENIED
    assert result.reason == "inactive_membership"
