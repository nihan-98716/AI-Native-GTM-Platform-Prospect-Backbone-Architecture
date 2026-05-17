from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TenantOwnedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CustomFieldDefinition(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "custom_field_definitions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "entity_type",
            "field_name",
            name="uq_custom_field_definitions_tenant_entity_field",
        ),
        Index("ix_custom_field_definitions_tenant_entity", "tenant_id", "entity_type"),
    )

    entity_type: Mapped[str] = mapped_column(String(120), nullable=False)
    field_name: Mapped[str] = mapped_column(String(120), nullable=False)
    field_type: Mapped[str] = mapped_column(String(80), nullable=False)
    validation_rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    default_value: Mapped[dict | None] = mapped_column(JSONB)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
