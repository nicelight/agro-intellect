from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    login_identifier: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    created_by_account_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("accounts.account_id"), nullable=True,
    )
    updated_by_account_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("accounts.account_id"), nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'invited', 'disabled')",
            name="ck_accounts_status",
        ),
    )


class Farm(Base):
    __tablename__ = "farms"

    farm_id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="active",
    )
    sync_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="local_only",
    )
    one_farm_guard: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )

    __table_args__ = (
        CheckConstraint("status = 'active'", name="ck_farms_status"),
        CheckConstraint(
            "sync_status = 'local_only'", name="ck_farms_sync_status",
        ),
        CheckConstraint(
            "one_farm_guard IS TRUE", name="ck_farms_one_farm_guard",
        ),
    )


class FarmMembership(Base):
    __tablename__ = "farm_memberships"

    membership_id: Mapped[str] = mapped_column(Text, primary_key=True)
    account_id: Mapped[str] = mapped_column(
        Text, ForeignKey("accounts.account_id"), nullable=False,
    )
    farm_id: Mapped[str] = mapped_column(
        Text, ForeignKey("farms.farm_id"), nullable=False,
    )
    role_preset: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    changed_by_account_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("accounts.account_id"), nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "role_preset IN ('boss', 'engineer', 'consultant')",
            name="ck_farm_memberships_role_preset",
        ),
        CheckConstraint(
            "status IN ('active', 'invited', 'disabled', 'removed')",
            name="ck_farm_memberships_status",
        ),
        UniqueConstraint("account_id", name="uq_farm_memberships_account"),
        UniqueConstraint(
            "account_id", "farm_id", name="uq_farm_memberships_account_farm",
        ),
        Index("idx_farm_memberships_account_status", "account_id", "status"),
    )


class LocalSession(Base):
    __tablename__ = "local_sessions"

    session_id: Mapped[str] = mapped_column(Text, primary_key=True)
    account_id: Mapped[str] = mapped_column(
        Text, ForeignKey("accounts.account_id"), nullable=False,
    )
    farm_id: Mapped[str] = mapped_column(
        Text, ForeignKey("farms.farm_id"), nullable=False,
    )
    membership_id: Mapped[str] = mapped_column(
        Text, ForeignKey("farm_memberships.membership_id"), nullable=False,
    )
    session_hash: Mapped[str] = mapped_column(
        CHAR(64), nullable=False, unique=True,
    )
    session_ref: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    auth_provenance_ref: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_request_ref: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    revoked_request_ref: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'revoked')",
            name="ck_local_sessions_status",
        ),
        CheckConstraint(
            "session_hash ~ '^[a-f0-9]{64}$'",
            name="ck_local_sessions_session_hash",
        ),
        CheckConstraint(
            "session_ref LIKE 'sess_ref_%'",
            name="ck_local_sessions_session_ref",
        ),
        CheckConstraint(
            "auth_provenance_ref LIKE 'auth_ref_%'",
            name="ck_local_sessions_auth_provenance_ref",
        ),
        Index(
            "idx_local_sessions_account_status", "account_id", "status",
        ),
        Index("idx_local_sessions_expires_at", "expires_at"),
    )


class Plant(Base):
    __tablename__ = "plants"

    plant_id: Mapped[str] = mapped_column(Text, primary_key=True)
    farm_id: Mapped[str] = mapped_column(
        Text, ForeignKey("farms.farm_id"), nullable=False,
    )
    canonical_label: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(
        Text, nullable=False, default="active",
    )
    created_by_actor_ref: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    archived_by_actor_ref: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    archive_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    restored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    restored_by_actor_ref: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "state IN ('active', 'archived')",
            name="ck_plants_state",
        ),
        Index("idx_plants_farm_state", "farm_id", "state"),
    )


class PlantAccessGrant(Base):
    __tablename__ = "plant_access_grants"

    grant_id: Mapped[str] = mapped_column(Text, primary_key=True)
    farm_id: Mapped[str] = mapped_column(
        Text, ForeignKey("farms.farm_id"), nullable=False,
    )
    plant_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plants.plant_id"), nullable=False,
    )
    account_id: Mapped[str] = mapped_column(
        Text, ForeignKey("accounts.account_id"), nullable=False,
    )
    membership_id: Mapped[str] = mapped_column(
        Text, ForeignKey("farm_memberships.membership_id"), nullable=False,
    )
    state: Mapped[str] = mapped_column(
        Text, nullable=False, default="granted",
    )
    can_view: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    can_work: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    plant_approve_actions: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    created_by_actor_ref: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
    )
    updated_by_actor_ref: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "state IN ('granted', 'revoked')",
            name="ck_plant_access_grants_state",
        ),
        Index("idx_plant_access_grants_plant", "plant_id"),
        Index("idx_plant_access_grants_account", "account_id"),
    )


class AdminAuditRecord(Base):
    __tablename__ = "admin_audit_records"

    audit_id: Mapped[str] = mapped_column(Text, primary_key=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    actor_account_id: Mapped[str] = mapped_column(Text, nullable=False)
    target_account_id: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    farm_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    membership_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    auth_provenance_ref: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    request_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
