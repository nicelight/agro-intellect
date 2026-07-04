from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event, func, select

from backend.app.access_admin import credential_service as credential_service_module
from backend.app.access_admin.credential_service import (
    AuthenticationFailed,
    AuthenticationFailureReason,
)
from backend.app.access_admin.models import Account, Base, FarmMembership, LocalSession
from backend.app.access_admin.repository import AccessSessionRepository
from backend.app.access_admin.security import (
    hash_password,
    hash_session_token,
    verify_session_token,
)
from backend.app.access_admin.session_service import (
    DEFAULT_SESSION_TTL,
    SessionValidationFailed,
    SessionValidationFailureReason,
    SessionService,
)
from backend.app.core.security import generate_session_token


NOW = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
PASSWORD = "test-only-local-password"


@pytest.fixture
def lifecycle_session(backend_database):
    engine = backend_database.engine()

    def configure_sqlite(dbapi_connection, _connection_record) -> None:
        dbapi_connection.create_function(
            "btrim",
            1,
            lambda value: value.strip() if value is not None else None,
        )
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    event.listen(engine, "connect", configure_sqlite)
    Base.metadata.create_all(engine)
    try:
        with backend_database.test_session() as session:
            yield session
    finally:
        Base.metadata.drop_all(engine)


def _add_identity(
    session,
    *,
    login_name: str = "boss",
    account_status: str = "active",
    membership_status: str = "active",
):
    account = Account(
        login_name=login_name,
        display_name="Test User",
        account_status=account_status,
        password_hash=hash_password(PASSWORD),
    )
    session.add(account)
    session.flush()
    membership = FarmMembership(
        account_id=account.account_id,
        farm_id=uuid.uuid4(),
        role_preset="boss",
        membership_status=membership_status,
    )
    session.add(membership)
    session.flush()
    return account, membership


def _services(session, *, now=NOW):
    repository = AccessSessionRepository(session)
    sessions = SessionService(repository, now=lambda: now)
    return repository, sessions


def test_login_flow_issues_digest_only_session_with_exact_default_ttl(
    lifecycle_session,
):
    account, membership = _add_identity(lifecycle_session)
    _repository, sessions = _services(lifecycle_session)

    issued = sessions.login("  BOSS  ", PASSWORD, client_label="test-client")
    persisted = lifecycle_session.scalar(select(LocalSession))

    assert issued.account is account
    assert issued.membership is membership
    assert persisted is issued.session
    assert persisted.account_id == account.account_id
    assert persisted.token_hash == hash_session_token(issued.raw_token)
    assert persisted.created_at == NOW
    assert persisted.expires_at == NOW + DEFAULT_SESSION_TTL
    assert DEFAULT_SESSION_TTL == timedelta(days=7)
    assert persisted.auth_method == "local_password"
    assert persisted.client_label == "test-client"
    assert "raw_token" not in repr(issued)
    assert lifecycle_session.scalar(select(func.count(Account.account_id))) == 1
    assert lifecycle_session.scalar(
        select(func.count(FarmMembership.membership_id))
    ) == 1
    assert not hasattr(sessions, "issue_session")
    assert "AuthenticatedIdentity" not in credential_service_module.__all__
    assert "_AuthenticatedIdentity" not in credential_service_module.__all__


def test_failed_auth_and_manually_created_identity_never_create_session(
    lifecycle_session,
):
    account, membership = _add_identity(lifecycle_session)
    _repository, sessions = _services(lifecycle_session)

    failures = [
        ("missing", PASSWORD),
        ("boss", "wrong-test-password"),
        (None, PASSWORD),
    ]
    for login_name, password in failures:
        with pytest.raises(AuthenticationFailed) as caught:
            sessions.login(login_name, password)
        assert str(caught.value) == "Authentication failed."

    account.account_status = "disabled"
    lifecycle_session.flush()
    with pytest.raises(AuthenticationFailed):
        sessions.login("boss", PASSWORD)

    account.account_status = "active"
    membership.membership_status = "disabled"
    lifecycle_session.flush()
    with pytest.raises(AuthenticationFailed):
        sessions.login("boss", PASSWORD)

    membership.membership_status = "active"
    lifecycle_session.add(
        FarmMembership(
            account_id=account.account_id,
            farm_id=uuid.uuid4(),
            role_preset="engineer",
            membership_status="active",
        )
    )
    lifecycle_session.flush()
    with pytest.raises(AuthenticationFailed):
        sessions.login("boss", PASSWORD)

    assert lifecycle_session.scalar(select(func.count(LocalSession.session_id))) == 0


def test_missing_and_wrong_login_both_run_one_password_verification(
    lifecycle_session,
    monkeypatch,
):
    _add_identity(lifecycle_session)
    _repository, sessions = _services(lifecycle_session)
    verification_inputs: list[object | None] = []
    original_verify = credential_service_module.verify_password_for_account

    def tracked_verify(password: object, password_hash: object | None) -> bool:
        verification_inputs.append(password_hash)
        return original_verify(password, password_hash)

    monkeypatch.setattr(
        credential_service_module,
        "verify_password_for_account",
        tracked_verify,
    )

    with pytest.raises(AuthenticationFailed) as missing:
        sessions.login("missing", "wrong-test-password")
    with pytest.raises(AuthenticationFailed) as known_wrong:
        sessions.login("boss", "wrong-test-password")

    assert missing.value.reason is AuthenticationFailureReason.CREDENTIAL_INVALID
    assert (
        known_wrong.value.reason
        is AuthenticationFailureReason.CREDENTIAL_INVALID
    )
    assert len(verification_inputs) == 2
    assert verification_inputs[0] is None
    assert isinstance(verification_inputs[1], str)


def test_login_preserves_safe_account_and_membership_failure_reasons(
    lifecycle_session,
):
    account, membership = _add_identity(lifecycle_session)
    _repository, sessions = _services(lifecycle_session)

    with pytest.raises(AuthenticationFailed) as wrong_password:
        sessions.login("boss", "wrong-test-password")
    assert (
        wrong_password.value.reason
        is AuthenticationFailureReason.CREDENTIAL_INVALID
    )

    account.account_status = "disabled"
    lifecycle_session.flush()
    with pytest.raises(AuthenticationFailed) as account_disabled:
        sessions.login("boss", PASSWORD)
    assert (
        account_disabled.value.reason
        is AuthenticationFailureReason.ACCOUNT_DISABLED
    )

    account.account_status = "active"
    membership.membership_status = "disabled"
    lifecycle_session.flush()
    with pytest.raises(AuthenticationFailed) as membership_disabled:
        sessions.login("boss", PASSWORD)
    assert (
        membership_disabled.value.reason
        is AuthenticationFailureReason.MEMBERSHIP_DISABLED
    )

    lifecycle_session.delete(membership)
    lifecycle_session.flush()
    with pytest.raises(AuthenticationFailed) as membership_required:
        sessions.login("boss", PASSWORD)
    assert (
        membership_required.value.reason
        is AuthenticationFailureReason.MEMBERSHIP_REQUIRED
    )


def test_validation_uses_digest_lookup_and_constant_time_primitive(
    lifecycle_session,
    monkeypatch,
):
    _add_identity(lifecycle_session)
    _repository, sessions = _services(lifecycle_session)
    issued = sessions.login("boss", PASSWORD)
    comparisons: list[tuple[object, object]] = []

    def tracked_verify(raw_token: object, stored_hash: object) -> bool:
        comparisons.append((raw_token, stored_hash))
        return verify_session_token(raw_token, stored_hash)

    monkeypatch.setattr(
        "backend.app.access_admin.session_service.verify_session_token",
        tracked_verify,
    )

    validated = sessions.validate_session(issued.raw_token)

    assert validated is not None
    assert validated.session is issued.session
    assert comparisons == [(issued.raw_token, issued.session.token_hash)]
    assert sessions.validate_session("malformed") is None
    assert sessions.validate_session(generate_session_token()) is None
    assert comparisons == [(issued.raw_token, issued.session.token_hash)]


def test_validation_fails_closed_for_revoked_expired_and_disabled_state(
    lifecycle_session,
    monkeypatch,
):
    account, membership = _add_identity(lifecycle_session)
    _repository, sessions = _services(lifecycle_session)
    comparisons: list[tuple[object, object]] = []

    def tracked_verify(raw_token: object, stored_hash: object) -> bool:
        comparisons.append((raw_token, stored_hash))
        return verify_session_token(raw_token, stored_hash)

    monkeypatch.setattr(
        "backend.app.access_admin.session_service.verify_session_token",
        tracked_verify,
    )

    revoked = sessions.login("boss", PASSWORD)
    revoked.session.revoked_at = NOW
    lifecycle_session.flush()
    assert sessions.validate_session(revoked.raw_token) is None

    expired_token = generate_session_token()
    expired = LocalSession(
        account_id=account.account_id,
        token_hash=hash_session_token(expired_token),
        created_at=NOW - timedelta(days=8),
        expires_at=NOW - timedelta(days=1),
        auth_method="local_password",
    )
    lifecycle_session.add(expired)
    lifecycle_session.flush()
    assert sessions.validate_session(expired_token) is None

    active = sessions.login("boss", PASSWORD)
    account.account_status = "disabled"
    lifecycle_session.flush()
    assert sessions.validate_session(active.raw_token) is None

    account.account_status = "active"
    membership.membership_status = "disabled"
    lifecycle_session.flush()
    assert sessions.validate_session(active.raw_token) is None
    assert comparisons == [
        (revoked.raw_token, revoked.session.token_hash),
        (expired_token, expired.token_hash),
        (active.raw_token, active.session.token_hash),
        (active.raw_token, active.session.token_hash),
    ]


def test_required_validation_preserves_safe_lifecycle_failure_reasons(
    lifecycle_session,
):
    account, membership = _add_identity(lifecycle_session)
    _repository, sessions = _services(lifecycle_session)

    expired_token = generate_session_token()
    lifecycle_session.add(
        LocalSession(
            account_id=account.account_id,
            token_hash=hash_session_token(expired_token),
            created_at=NOW - timedelta(days=8),
            expires_at=NOW - timedelta(days=1),
            auth_method="local_password",
        )
    )
    lifecycle_session.flush()
    with pytest.raises(SessionValidationFailed) as expired:
        sessions.require_valid_session(expired_token)
    assert expired.value.reason is SessionValidationFailureReason.SESSION_EXPIRED

    active = sessions.login("boss", PASSWORD)
    account.account_status = "disabled"
    lifecycle_session.flush()
    with pytest.raises(SessionValidationFailed) as account_disabled:
        sessions.require_valid_session(active.raw_token)
    assert (
        account_disabled.value.reason
        is SessionValidationFailureReason.ACCOUNT_DISABLED
    )

    account.account_status = "active"
    membership.membership_status = "disabled"
    lifecycle_session.flush()
    with pytest.raises(SessionValidationFailed) as membership_disabled:
        sessions.require_valid_session(active.raw_token)
    assert (
        membership_disabled.value.reason
        is SessionValidationFailureReason.MEMBERSHIP_DISABLED
    )

    lifecycle_session.delete(membership)
    lifecycle_session.flush()
    with pytest.raises(SessionValidationFailed) as membership_required:
        sessions.require_valid_session(active.raw_token)
    assert (
        membership_required.value.reason
        is SessionValidationFailureReason.MEMBERSHIP_REQUIRED
    )


def test_login_never_revives_expired_or_revoked_sessions(lifecycle_session):
    account, _membership = _add_identity(lifecycle_session)
    _repository, sessions = _services(lifecycle_session)

    old_token = generate_session_token()
    old_session = LocalSession(
        account_id=account.account_id,
        token_hash=hash_session_token(old_token),
        created_at=NOW - timedelta(days=10),
        expires_at=NOW - timedelta(days=3),
        revoked_at=NOW - timedelta(days=4),
        auth_method="local_password",
    )
    lifecycle_session.add(old_session)
    lifecycle_session.flush()

    issued = sessions.login("boss", PASSWORD)

    assert issued.session.session_id != old_session.session_id
    assert old_session.revoked_at == NOW - timedelta(days=4)
    assert old_session.expires_at == NOW - timedelta(days=3)
    assert lifecycle_session.scalar(select(func.count(LocalSession.session_id))) == 2


def test_logout_revokes_only_presented_session_and_is_idempotent(
    lifecycle_session,
):
    _add_identity(lifecycle_session)
    _repository, sessions = _services(lifecycle_session)
    first = sessions.login("boss", PASSWORD)
    second = sessions.login("boss", PASSWORD)

    assert sessions.revoke_session(first.raw_token) is True
    assert first.session.revoked_at == NOW
    assert second.session.revoked_at is None
    assert sessions.revoke_session(first.raw_token) is False
    assert sessions.revoke_session("malformed") is False
    assert sessions.revoke_session(generate_session_token()) is False
    assert sessions.validate_session(second.raw_token) is not None
