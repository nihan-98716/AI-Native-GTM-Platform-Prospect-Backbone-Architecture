from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TenantOwnedMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.provenance import ProvenanceMixin


class Account(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_accounts_tenant_id"),
        UniqueConstraint("tenant_id", "domain", name="uq_accounts_tenant_domain"),
        CheckConstraint("source_type in ('seeded', 'imported', 'generated')", name="ck_accounts_source_type"),
        Index("ix_accounts_tenant_stage", "tenant_id", "lifecycle_stage"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255))
    lifecycle_stage: Mapped[str] = mapped_column(String(80), nullable=False, default="prospect")
    firmographics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class Persona(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "personas"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_personas_tenant_id"),
        UniqueConstraint("tenant_id", "name", name="uq_personas_tenant_name"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    buying_committee_role: Mapped[str | None] = mapped_column(String(120))


class Contact(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_contacts_tenant_id"),
        ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]),
        ForeignKeyConstraint(["tenant_id", "persona_id"], ["personas.tenant_id", "personas.id"]),
        UniqueConstraint("tenant_id", "email", name="uq_contacts_tenant_email"),
        CheckConstraint("source_type in ('seeded', 'imported', 'generated')", name="ck_contacts_source_type"),
        Index("ix_contacts_tenant_account", "tenant_id", "account_id"),
    )

    account_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    persona_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    email: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class Opportunity(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_opportunities_tenant_id"),
        ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]),
        Index("ix_opportunities_tenant_account", "tenant_id", "account_id"),
    )

    account_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[str] = mapped_column(String(120), nullable=False, default="discovery")
    amount: Mapped[object | None] = mapped_column(Numeric(12, 2))
    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class Activity(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_activities_tenant_id"),
        ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]),
        ForeignKeyConstraint(["tenant_id", "contact_id"], ["contacts.tenant_id", "contacts.id"]),
        CheckConstraint("account_id is not null or contact_id is not null", name="ck_activities_not_orphaned"),
        CheckConstraint("source_type in ('seeded', 'imported', 'generated')", name="ck_activities_source_type"),
        Index("ix_activities_tenant_created", "tenant_id", "created_at"),
    )

    account_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    contact_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    activity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class Signal(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_signals_tenant_id"),
        ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]),
        CheckConstraint("strength is null or (strength >= 0 and strength <= 100)", name="ck_signals_strength_range"),
        CheckConstraint("source_type in ('seeded', 'imported', 'generated')", name="ck_signals_source_type"),
        Index("ix_signals_tenant_observed", "tenant_id", "observed_at"),
        Index("ix_signals_tenant_type", "tenant_id", "signal_type"),
    )

    account_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(120), nullable=False)
    strength: Mapped[object | None] = mapped_column(Numeric(5, 2))
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    observed_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
