from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKeyConstraint, Index, LargeBinary, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TenantOwnedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class IntegrationConnection(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "integration_connections"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_integration_connections_tenant_id"),
        UniqueConstraint("tenant_id", "provider", "connection_name", name="uq_integration_connections_tenant_provider_name"),
        CheckConstraint("auth_type in ('api_key', 'oauth2', 'manual_config')", name="ck_integration_connections_auth_type"),
        CheckConstraint("status in ('not_configured', 'live', 'failed', 'rate_limited')", name="ck_integration_connections_status"),
        Index("ix_integration_connections_tenant_provider_status", "tenant_id", "provider", "status"),
        Index(
            "uq_integration_connections_one_live_default",
            "tenant_id",
            "provider",
            unique=True,
            postgresql_where=text("is_default = true and status = 'live'"),
        ),
    )

    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    connection_name: Mapped[str] = mapped_column(String(120), nullable=False, default="default")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auth_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="not_configured")
    scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    encrypted_credentials: Mapped[bytes | None] = mapped_column(LargeBinary)
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    health: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class IntegrationRun(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "integration_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "connection_id"],
            ["integration_connections.tenant_id", "integration_connections.id"],
        ),
        CheckConstraint("status in ('pending', 'running', 'completed', 'failed', 'timed_out', 'cancelled')", name="ck_integration_runs_status"),
        Index("ix_integration_runs_tenant_provider_status", "tenant_id", "provider", "status"),
        Index("ix_integration_runs_tenant_created", "tenant_id", "created_at"),
    )

    connection_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    request_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    counts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class SyncCursor(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "sync_cursors"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "connection_id"],
            ["integration_connections.tenant_id", "integration_connections.id"],
        ),
        UniqueConstraint("tenant_id", "connection_id", "cursor_name", name="uq_sync_cursors_tenant_connection_name"),
        Index("ix_sync_cursors_tenant_provider", "tenant_id", "provider"),
    )

    connection_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    cursor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    cursor_value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
