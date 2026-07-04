from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Account, FarmMembership, LocalSession, normalize_login_name


class AccessSessionRepository:
    """SQLAlchemy adapter for the FT-001 credential/session service boundary."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_account_by_login(self, login_name: str) -> Account | None:
        normalized_login = normalize_login_name(login_name)
        if not normalized_login:
            return None
        return self._session.scalar(
            select(Account).where(Account.login_name == normalized_login)
        )

    def get_account(self, account_id: uuid.UUID) -> Account | None:
        return self._session.get(Account, account_id)

    def list_memberships(self, account_id: uuid.UUID) -> list[FarmMembership]:
        return list(
            self._session.scalars(
                select(FarmMembership)
                .where(FarmMembership.account_id == account_id)
                .order_by(FarmMembership.created_at, FarmMembership.membership_id)
            )
        )

    def find_session_by_token_hash(self, token_hash: str) -> LocalSession | None:
        return self._session.scalar(
            select(LocalSession).where(LocalSession.token_hash == token_hash)
        )

    def add_session(self, local_session: LocalSession) -> None:
        self._session.add(local_session)
        self._session.flush()

    def flush(self) -> None:
        self._session.flush()


__all__ = ["AccessSessionRepository"]
