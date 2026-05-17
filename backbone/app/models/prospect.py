from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TenantOwnedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ICPDefinition(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "icp_definitions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_icp_definitions_tenant_id"),
        UniqueConstraint("tenant_id", "name", name="uq_icp_definitions_tenant_name"),
        Index("ix_icp_definitions_tenant_status", "tenant_id", "status"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    criteria: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    target_personas: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
