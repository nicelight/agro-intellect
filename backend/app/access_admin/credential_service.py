from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .models import Account, FarmMembership
from .repository import AccessSessionRepository
from .security import verify_password_for_account


class AuthenticationFailureReason(StrEnum):
    CREDENTIAL_INVALID = "credential_invalid"
    ACCOUNT_DISABLED = "account_disabled"
    MEMBERSHIP_REQUIRED = "membership_required"
    MEMBERSHIP_DISABLED = "membership_disabled"


class AuthenticationFailed(Exception):
    """Generic local authentication failure without identity disclosure."""

    def __init__(
        self,
        reason: AuthenticationFailureReason = (
            AuthenticationFailureReason.CREDENTIAL_INVALID
        ),
    ) -> None:
        self.reason = reason
        super().__init__("Authentication failed.")


@dataclass(frozen=True, slots=True)
class _AuthenticatedIdentity:
    account: Account
    membership: FarmMembership


class CredentialService:
    """Authenticate an existing active local Account and FarmMembership."""

    def __init__(self, repository: AccessSessionRepository) -> None:
        self._repository = repository

    def authenticate(
        self,
        login_name: object,
        password: object,
    ) -> _AuthenticatedIdentity:
        if not isinstance(login_name, str) or not isinstance(password, str):
            raise AuthenticationFailed

        account = self._repository.find_account_by_login(login_name)
        password_hash = account.password_hash if account is not None else None
        if not verify_password_for_account(password, password_hash):
            raise AuthenticationFailed
        if account.account_status != "active":
            raise AuthenticationFailed(AuthenticationFailureReason.ACCOUNT_DISABLED)

        memberships = self._repository.list_memberships(account.account_id)
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


__all__ = [
    "AuthenticationFailed",
    "AuthenticationFailureReason",
    "CredentialService",
]
