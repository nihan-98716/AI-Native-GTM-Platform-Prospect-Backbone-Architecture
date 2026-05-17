from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TenantOwnedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ValueHypothesis(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "value_hypotheses"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]),
        ForeignKeyConstraint(["tenant_id", "contact_id"], ["contacts.tenant_id", "contacts.id"]),
        ForeignKeyConstraint(["tenant_id", "workflow_run_id"], ["workflow_runs.tenant_id", "workflow_runs.id"]),
        CheckConstraint(
            "confidence_score is null or (confidence_score >= 0 and confidence_score <= 100)",
            name="ck_value_hypotheses_confidence_range",
        ),
        Index("ix_value_hypotheses_tenant_account", "tenant_id", "account_id"),
        Index("ix_value_hypotheses_tenant_workflow", "tenant_id", "workflow_run_id"),
    )

    account_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    contact_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    workflow_run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    generated_by_agent: Mapped[str] = mapped_column(String(120), nullable=False)
    generated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    confidence_score: Mapped[object | None] = mapped_column(Numeric(5, 2))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class OutreachDraft(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "outreach_drafts"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]),
        ForeignKeyConstraint(["tenant_id", "contact_id"], ["contacts.tenant_id", "contacts.id"]),
        ForeignKeyConstraint(["tenant_id", "workflow_run_id"], ["workflow_runs.tenant_id", "workflow_runs.id"]),
        CheckConstraint(
            "confidence_score is null or (confidence_score >= 0 and confidence_score <= 100)",
            name="ck_outreach_drafts_confidence_range",
        ),
        CheckConstraint(
            "status in ('draft', 'pending_approval', 'approved', 'rejected')",
            name="ck_outreach_drafts_status",
        ),
        Index("ix_outreach_drafts_tenant_contact", "tenant_id", "contact_id"),
        Index("ix_outreach_drafts_tenant_workflow", "tenant_id", "workflow_run_id"),
        Index("ix_outreach_drafts_tenant_status", "tenant_id", "status"),
    )

    account_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    contact_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    workflow_run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    generated_by_agent: Mapped[str] = mapped_column(String(120), nullable=False)
    generated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    confidence_score: Mapped[object | None] = mapped_column(Numeric(5, 2))
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
