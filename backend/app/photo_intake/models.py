from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..access_admin.models import Base, JSON_DOCUMENT


class PhotoCatalogItem(Base):
    __tablename__ = "photo_catalog_items"
    __table_args__ = (
        CheckConstraint(
            "photo_type IN ('whole_plant', 'leaf_closeup', 'roots', "
            "'problem_area', 'other')",
            name="ck_photo_catalog_items_photo_type",
        ),
        CheckConstraint(
            "content_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_photo_catalog_items_content_type",
        ),
        CheckConstraint(
            "size_bytes >= 0 AND size_bytes <= 20971520",
            name="ck_photo_catalog_items_size_bytes_range",
        ),
        CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_photo_catalog_items_sha256_lower_hex",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "original_file_ref ~ "
            "'^plants/[0-9a-f-]{36}/photos/[0-9a-f-]{36}/original\\."
            "(jpg|png|webp)$'",
            name="ck_photo_catalog_items_original_file_ref_shape",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "manifest_ref ~ "
            "'^plants/[0-9a-f-]{36}/photos/[0-9a-f-]{36}/"
            "manifest\\.initial_capture\\.json$'",
            name="ck_photo_catalog_items_manifest_ref_shape",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(source_refs) = 'object'",
            name="ck_photo_catalog_items_source_refs_object",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "jsonb_typeof(event_refs) = 'object'",
            name="ck_photo_catalog_items_event_refs_object",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "local_only IS TRUE",
            name="ck_photo_catalog_items_local_only_true",
        ),
        CheckConstraint(
            "can_train_on IS FALSE",
            name="ck_photo_catalog_items_can_train_on_false",
        ),
        Index(
            "ix_photo_catalog_items_plant_uploaded_desc",
            "plant_id",
            "uploaded_at",
            "photo_id",
        ),
        Index("ix_photo_catalog_items_check_in_id", "check_in_id"),
    )

    photo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farms.farm_id", ondelete="RESTRICT"),
        nullable=False,
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plants.plant_id", ondelete="RESTRICT"),
        nullable=False,
    )
    check_in_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("daily_checkins.check_in_id", ondelete="RESTRICT"),
        nullable=True,
    )
    uploaded_by_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.account_id", ondelete="RESTRICT"),
        nullable=False,
    )
    uploaded_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farm_memberships.membership_id", ondelete="RESTRICT"),
        nullable=False,
    )
    photo_type: Mapped[str] = mapped_column(String(32), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    original_file_ref: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_ref: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict, server_default=text("'{}'")
    )
    event_refs: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict, server_default=text("'{}'")
    )
    local_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    can_train_on: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["PhotoCatalogItem"]

