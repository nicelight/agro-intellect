from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import uuid

from .credential_service import (
    AuthenticationFailed,
    AuthenticationFailureReason,
    CredentialService,
    _AuthenticatedIdentity,
)
from .models import Account, FarmMembership, LocalSession
from .repository import AccessSessionRepository
from .security import (
    generate_session_token,
    hash_session_token,
    verify_session_token,
)


DEFAULT_SESSION_TTL = timedelta(days=7)


@dataclass(frozen=True, slots=True)
class IssuedSession:
    session: LocalSession
    account: Account
    membership: FarmMembership
    raw_token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class ValidatedSession:
    session: LocalSession
    account: Account
    membership: FarmMembership


class SessionValidationFailureReason(StrEnum):
    SESSION_INVALID = "session_invalid"
    SESSION_EXPIRED = "session_expired"
    ACCOUNT_DISABLED = "account_disabled"
    MEMBERSHIP_REQUIRED = "membership_required"
    MEMBERSHIP_DISABLED = "membership_disabled"


class SessionValidationFailed(Exception):
    """Internal typed failure with a generic, non-sensitive public message."""

    def __init__(self, reason: SessionValidationFailureReason) -> None:
        self.reason = reason
        super().__init__("Session validation failed.")


class SessionService:
    """Issue, validate, and revoke digest-only local password sessions."""

    def __init__(
        self,
        repository: AccessSessionRepository,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._credentials = CredentialService(repository)
        self._now = now or (lambda: datetime.now(timezone.utc))

    def login(
        self,
        login_name: object,
        password: object,
        *,
        client_label: str | None = None,
    ) -> IssuedSession:
        identity = self._credentials.authenticate(login_name, password)
        return self._issue_authenticated(identity, client_label=client_label)

    def _issue_authenticated(
        self,
        identity: _AuthenticatedIdentity,
        *,
        client_label: str | None = None,
    ) -> IssuedSession:
        current_identity = self._load_login_identity(identity.account.account_id)
        if (
            current_identity.membership.membership_id
            != identity.membership.membership_id
        ):
            raise AuthenticationFailed

        created_at = _as_utc(self._now())
        raw_token = generate_session_token()
        local_session = LocalSession(
            account_id=current_identity.account.account_id,
            token_hash=hash_session_token(raw_token),
            created_at=created_at,
            expires_at=created_at + DEFAULT_SESSION_TTL,
            auth_method="local_password",
            client_label=client_label,
        )
        self._repository.add_session(local_session)
        return IssuedSession(
            session=local_session,
            account=current_identity.account,
            membership=current_identity.membership,
            raw_token=raw_token,
        )

    def validate_session(self, raw_token: object) -> ValidatedSession | None:
        try:
            return self.require_valid_session(raw_token)
        except SessionValidationFailed:
            return None

    def require_valid_session(self, raw_token: object) -> ValidatedSession:
        """Return a valid session or preserve its safe HTTP-relevant failure."""

        local_session = self._find_verified_session(raw_token)
        if local_session is None:
            raise SessionValidationFailed(
                SessionValidationFailureReason.SESSION_INVALID
            )
        if local_session.revoked_at is not None:
            raise SessionValidationFailed(
                SessionValidationFailureReason.SESSION_INVALID
            )
        if _as_utc(local_session.expires_at) <= _as_utc(self._now()):
            raise SessionValidationFailed(
                SessionValidationFailureReason.SESSION_EXPIRED
            )

        identity = self._load_session_identity(local_session.account_id)
        return ValidatedSession(
            session=local_session,
            account=identity.account,
            membership=identity.membership,
        )

    def revoke_session(self, raw_token: object) -> bool:
        local_session = self._find_verified_session(raw_token)
        if local_session is None or local_session.revoked_at is not None:
            return False

        local_session.revoked_at = _as_utc(self._now())
        self._repository.flush()
        return True

    def _find_verified_session(self, raw_token: object) -> LocalSession | None:
        if not isinstance(raw_token, str):
            return None
        try:
            token_hash = hash_session_token(raw_token)
        except ValueError:
            return None

        local_session = self._repository.find_session_by_token_hash(token_hash)
        if local_session is None:
            return None
        if not verify_session_token(raw_token, local_session.token_hash):
            return None
        return local_session

    def _load_login_identity(
        self,
        account_id: uuid.UUID,
    ) -> _AuthenticatedIdentity:
        account = self._repository.get_account(account_id)
        if account is None:
            raise AuthenticationFailed
        if account.account_status != "active":
            raise AuthenticationFailed(
                AuthenticationFailureReason.ACCOUNT_DISABLED
            )

        memberships = self._repository.list_memberships(account_id)
        if not memberships:
            raise AuthenticationFailed(
                AuthenticationFailureReason.MEMBERSHIP_REQUIRED
            )
        if len(memberships) != 1:
            raise AuthenticationFailed
        membership = memberships[0]
        if membership.membership_status != "active":
            raise AuthenticationFailed(
                AuthenticationFailureReason.MEMBERSHIP_DISABLED
            )
        return _AuthenticatedIdentity(account=account, membership=membership)

    def _load_session_identity(
        self,
        account_id: uuid.UUID,
    ) -> _AuthenticatedIdentity:
        account = self._repository.get_account(account_id)
        if account is None:
            raise SessionValidationFailed(
                SessionValidationFailureReason.SESSION_INVALID
            )
        if account.account_status != "active":
            raise SessionValidationFailed(
                SessionValidationFailureReason.ACCOUNT_DISABLED
            )

        memberships = self._repository.list_memberships(account_id)
        if not memberships:
            raise SessionValidationFailed(
                SessionValidationFailureReason.MEMBERSHIP_REQUIRED
            )
        if len(memberships) != 1:
            raise SessionValidationFailed(
                SessionValidationFailureReason.SESSION_INVALID
            )

        membership = memberships[0]
        if membership.membership_status != "active":
            raise SessionValidationFailed(
                SessionValidationFailureReason.MEMBERSHIP_DISABLED
            )
        return _AuthenticatedIdentity(account=account, membership=membership)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


__all__ = [
    "DEFAULT_SESSION_TTL",
    "IssuedSession",
    "SessionValidationFailed",
    "SessionValidationFailureReason",
    "SessionService",
    "ValidatedSession",
]
