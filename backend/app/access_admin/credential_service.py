from __future__ import annotations

from dataclasses import dataclass

from .models import Account, FarmMembership
from .repository import AccessSessionRepository
from .security import verify_password


class AuthenticationFailed(Exception):
    """Generic local authentication failure without identity disclosure."""

    def __init__(self) -> None:
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
        if account is None or not verify_password(password, account.password_hash):
            raise AuthenticationFailed
        if account.account_status != "active":
            raise AuthenticationFailed

        memberships = self._repository.list_memberships(account.account_id)
        if len(memberships) != 1:
            raise AuthenticationFailed

        membership = memberships[0]
        if membership.membership_status != "active":
            raise AuthenticationFailed

        return _AuthenticatedIdentity(account=account, membership=membership)


__all__ = [
    "AuthenticationFailed",
    "CredentialService",
]
