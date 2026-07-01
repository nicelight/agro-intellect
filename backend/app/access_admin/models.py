from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, validates


def normalize_login_name(login_name: str) -> str:
    """Return the canonical persisted representation of a local login name."""

    return login_name.strip().lower()


class Base(DeclarativeBase):
    """Declarative metadata for Access & Admin persistence models."""


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "account_status IN ('active', 'disabled')",
            name="ck_accounts_account_status",
        ),
        CheckConstraint(
            "login_name = lower(btrim(login_name)) AND btrim(login_name) <> ''",
            name="ck_accounts_login_name_canonical",
        ),
        Index("uq_accounts_login_name", "login_name", unique=True),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    login_name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    account_status: Mapped[str] = mapped_column(String(32), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    @validates("login_name")
    def _normalize_login_name(self, _key: str, value: str) -> str:
        return normalize_login_name(value)


class FarmMembership(Base):
    __tablename__ = "farm_memberships"
    __table_args__ = (
        CheckConstraint(
            "role_preset IN ('boss', 'engineer', 'consultant')",
            name="ck_farm_memberships_role_preset",
        ),
        CheckConstraint(
            "membership_status IN ('active', 'disabled')",
            name="ck_farm_memberships_membership_status",
        ),
        Index(
            "uq_farm_memberships_account_farm",
            "account_id",
            "farm_id",
            unique=True,
        ),
    )

    membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.account_id", ondelete="RESTRICT"),
        nullable=False,
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    role_preset: Mapped[str] = mapped_column(String(16), nullable=False)
    membership_status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class LocalSession(Base):
    __tablename__ = "local_sessions"
    __table_args__ = (
        CheckConstraint(
            "auth_method IN ('local_password')",
            name="ck_local_sessions_auth_method",
        ),
        Index("uq_local_sessions_token_hash", "token_hash", unique=True),
        Index("ix_local_sessions_account_id", "account_id"),
        Index("ix_local_sessions_expires_at", "expires_at"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.account_id", ondelete="RESTRICT"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    auth_method: Mapped[str] = mapped_column(String(32), nullable=False)
    client_label: Mapped[str | None] = mapped_column(Text, nullable=True)
