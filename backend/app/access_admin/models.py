from __future__ import annotations

import uuid
from datetime import datetime
import re

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, validates


PLANT_KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


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


class Farm(Base):
    __tablename__ = "farms"
    __table_args__ = (
        CheckConstraint("farm_key = 'local_farm'", name="ck_farms_farm_key"),
        CheckConstraint("btrim(display_name) <> ''", name="ck_farms_display_name"),
        UniqueConstraint("farm_key", name="uq_farms_farm_key"),
    )

    farm_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    farm_key: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    @validates("farm_key")
    def _validate_farm_key(self, _key: str, value: str) -> str:
        if value != "local_farm":
            raise ValueError("farm_key must be local_farm")
        return value

    @validates("display_name")
    def _trim_display_name(self, _key: str, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("display_name must not be blank")
        return normalized


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
        ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_farm_memberships_farm_id_farms",
            ondelete="RESTRICT",
        ).ddl_if(dialect="postgresql"),
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
    farm_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
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


class Plant(Base):
    __tablename__ = "plants"
    __table_args__ = (
        CheckConstraint(
            "plant_key ~ '^[a-z0-9]+(_[a-z0-9]+)*$'",
            name="ck_plants_plant_key",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint("btrim(display_name) <> ''", name="ck_plants_display_name"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_plants_status"),
        UniqueConstraint("farm_id", "plant_key", name="uq_plants_farm_plant_key"),
        Index("ix_plants_farm_status", "farm_id", "status"),
    )

    plant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farms.farm_id", ondelete="RESTRICT"),
        nullable=False,
    )
    plant_key: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    @validates("plant_key")
    def _validate_plant_key(self, _key: str, value: str) -> str:
        if PLANT_KEY_PATTERN.fullmatch(value) is None:
            raise ValueError("plant_key must be canonical lowercase input")
        return value

    @validates("display_name")
    def _trim_display_name(self, _key: str, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("display_name must not be blank")
        return normalized


class PlantAccessGrant(Base):
    __tablename__ = "plant_access_grants"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'revoked')", name="ck_plant_access_grants_status"
        ),
        UniqueConstraint(
            "membership_id",
            "plant_id",
            name="uq_plant_access_grants_membership_plant",
        ),
        Index("ix_plant_access_grants_plant_status", "plant_id", "status"),
    )

    grant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farm_memberships.membership_id", ondelete="RESTRICT"),
        nullable=False,
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plants.plant_id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    plant_approve_actions: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AdminAuditRecord(Base):
    __tablename__ = "admin_audit_records"
    __table_args__ = (
        CheckConstraint(
            "actor_kind IN ('account', 'system_bootstrap')",
            name="ck_admin_audit_records_actor_kind",
        ),
        CheckConstraint(
            "((actor_kind = 'account' AND actor_account_id IS NOT NULL "
            "AND actor_membership_id IS NOT NULL AND actor_role_preset IS NOT NULL) "
            "OR (actor_kind = 'system_bootstrap' AND actor_account_id IS NULL "
            "AND actor_membership_id IS NULL AND actor_role_preset IS NULL))",
            name="ck_admin_audit_records_actor_shape",
        ),
        CheckConstraint(
            "actor_role_preset IS NULL OR actor_role_preset IN "
            "('boss', 'engineer', 'consultant')",
            name="ck_admin_audit_records_actor_role",
        ),
        CheckConstraint(
            "action_type IN ('farm_created', 'farm_display_name_changed', "
            "'account_created', 'account_disabled', 'membership_role_changed', "
            "'membership_disabled', 'plant_created', "
            "'plant_display_name_changed', 'plant_archived', 'plant_restored', "
            "'plant_access_granted', 'plant_access_updated', "
            "'plant_access_revoked', 'plant_approve_actions_changed')",
            name="ck_admin_audit_records_action_type",
        ),
        CheckConstraint(
            "target_type IN ('farm', 'account', 'membership', 'plant', "
            "'plant_access_grant')",
            name="ck_admin_audit_records_target_type",
        ),
        CheckConstraint(
            "btrim(request_id) <> ''", name="ck_admin_audit_records_request_id"
        ),
        CheckConstraint(
            "jsonb_typeof(before_summary) = 'object'",
            name="ck_admin_audit_records_before_summary_object",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(after_summary) = 'object'",
            name="ck_admin_audit_records_after_summary_object",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(source_refs) = 'array'",
            name="ck_admin_audit_records_source_refs_array",
        ).ddl_if(dialect="postgresql"),
    )

    admin_audit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farms.farm_id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.account_id", ondelete="RESTRICT"),
        nullable=True,
    )
    actor_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farm_memberships.membership_id", ondelete="RESTRICT"),
        nullable=True,
    )
    actor_role_preset: Mapped[str | None] = mapped_column(String(16), nullable=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    plant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plants.plant_id", ondelete="RESTRICT"),
        nullable=True,
    )
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    before_summary: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict, server_default=text("'{}'")
    )
    after_summary: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict, server_default=text("'{}'")
    )
    source_refs: Mapped[list[object]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=list, server_default=text("'[]'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


Index(
    "ix_admin_audit_records_farm_created_desc",
    AdminAuditRecord.farm_id,
    AdminAuditRecord.created_at.desc(),
    AdminAuditRecord.admin_audit_id.desc(),
)
Index(
    "ix_admin_audit_records_plant_created_desc",
    AdminAuditRecord.plant_id,
    AdminAuditRecord.created_at.desc(),
    AdminAuditRecord.admin_audit_id.desc(),
    postgresql_where=AdminAuditRecord.plant_id.is_not(None),
)
