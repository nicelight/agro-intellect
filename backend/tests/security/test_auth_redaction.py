"""Security tests: auth responses must not leak secrets on forbidden surfaces."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.app.access import (
    Account,
    AccountStatus,
    Farm,
    FarmMembership,
    InMemoryAccessRepository,
    MembershipRole,
    MembershipStatus,
    create_local_session,
)
from backend.app.privacy.redaction import redact_payload
from backend.app.security import generate_session_secret

NOW = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)

SECRET_PATTERNS = [
    "sk-ant-abcdefghijklmnopqrstuvwxyz123456",
    "sk-abcdefghijklmnopqrstuvwxyz123456",
    "ghp_abcdefghijklmnopqrstuvwxyz123456",
    "AIzaabcdefghijklmnopqrstuvwxyz123456",
]


def build_repo() -> InMemoryAccessRepository:
    repo = InMemoryAccessRepository()
    repo.add_account(
        Account(
            account_id="acct_boss",
            display_name="Boss",
            login_identifier="boss.local",
            status=AccountStatus.ACTIVE,
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
            status=MembershipStatus.ACTIVE,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    return repo


class TestLoginResponseRedaction:
    def test_login_response_does_not_contain_secrets(self):
        repo = build_repo()
        _session, raw_secret = create_local_session(
            repo,
            account_id="acct_boss",
            now=NOW,
            raw_session_secret=generate_session_secret(),
        )
        response = {
            "session_token": raw_secret,
            "session_ref": _session.session_ref,
            "expires_at": _session.expires_at.isoformat(),
        }
        result = redact_payload(response)
        for secret in SECRET_PATTERNS:
            assert secret not in str(result.value), (
                f"Login response contains secret pattern: {secret}"
            )


class TestMeResponseRedaction:
    def test_me_response_does_not_leak_session_secret(self):
        repo = build_repo()
        _session, raw_secret = create_local_session(
            repo,
            account_id="acct_boss",
            now=NOW,
            raw_session_secret=generate_session_secret(),
        )
        response = {
            "state": "resolved",
            "account_id": "acct_boss",
            "farm_id": "farm_local",
            "membership_id": "mbr_boss",
            "role": "boss",
            "membership_status": "active",
            "session_ref": _session.session_ref,
            "auth_provenance_ref": _session.auth_provenance_ref,
            "resolved_at": _session.expires_at.isoformat(),
        }
        result = redact_payload(response)
        for secret in SECRET_PATTERNS:
            assert secret not in str(result.value), (
                f"Me response contains secret pattern: {secret}"
            )

    def test_me_response_session_ref_is_redacted(self):
        repo = build_repo()
        _session, raw_secret = create_local_session(
            repo,
            account_id="acct_boss",
            now=NOW,
            raw_session_secret=generate_session_secret(),
        )
        assert _session.session_ref.startswith("sess_ref_")
        assert raw_secret not in (_session.session_ref, _session.auth_provenance_ref)

    def test_me_response_auth_provenance_ref_is_redacted(self):
        repo = build_repo()
        _session, raw_secret = create_local_session(
            repo,
            account_id="acct_boss",
            now=NOW,
            raw_session_secret=generate_session_secret(),
        )
        assert _session.auth_provenance_ref.startswith("auth_ref_")
        assert raw_secret not in (_session.auth_provenance_ref, _session.session_ref)


class TestErrorResponseRedaction:
    def test_error_response_does_not_contain_secret_patterns(self):
        error_response = {
            "error": {
                "code": "invalid_session",
                "message": "Session is invalid or denied.",
                "details": {},
                "request_ref": "req_abc123",
                "next_valid_actions": ["authenticate"],
            }
        }
        result = redact_payload(error_response)
        for secret in SECRET_PATTERNS:
            assert secret not in str(result.value), (
                f"Error response contains secret pattern: {secret}"
            )

    def test_redaction_policy_markers_in_me_response(self):
        repo = build_repo()
        _session, raw_secret = create_local_session(
            repo,
            account_id="acct_boss",
            now=NOW,
            raw_session_secret=generate_session_secret(),
        )
        response = {
            "state": "resolved",
            "account_id": "acct_boss",
            "farm_id": "farm_local",
            "membership_id": "mbr_boss",
            "role": "boss",
            "membership_status": "active",
            "session_ref": _session.session_ref,
            "auth_provenance_ref": _session.auth_provenance_ref,
        }
        serialized = str(response)
        known_secret = "sk-ant-abcdefghijklmnopqrstuvwxyz123456"
        assert known_secret not in serialized, (
            "Simulated secret leaked into response serialization"
        )

    def test_response_not_marked_redacted_by_redact_payload(self):
        repo = build_repo()
        _session, raw_secret = create_local_session(
            repo,
            account_id="acct_boss",
            now=NOW,
            raw_session_secret=generate_session_secret(),
        )
        response = {
            "session_token": raw_secret,
            "session_ref": _session.session_ref,
            "expires_at": _session.expires_at.isoformat(),
        }
        result = redact_payload(response)
        assert result.redacted, (
            "Login response should be detected as containing sensitive fields"
        )
