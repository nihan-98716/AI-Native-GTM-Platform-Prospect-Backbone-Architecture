from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TenantOwnedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class WorkflowRun(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_workflow_runs_tenant_id"),
        ForeignKeyConstraint(["tenant_id", "icp_id"], ["icp_definitions.tenant_id", "icp_definitions.id"]),
        ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_workflow_runs_tenant_idempotency_key"),
        CheckConstraint(
            "status in ('queued', 'running', 'waiting_for_approval', 'succeeded', 'failed', 'cancelled', 'timed_out')",
            name="ck_workflow_runs_status",
        ),
        Index("ix_workflow_runs_tenant_status", "tenant_id", "status"),
        Index("ix_workflow_runs_tenant_created", "tenant_id", "created_at"),
    )

    workflow_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="queued")
    icp_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    account_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    input: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_heartbeat_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))


class WorkflowStep(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "workflow_steps"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_workflow_steps_tenant_id"),
        ForeignKeyConstraint(["tenant_id", "workflow_run_id"], ["workflow_runs.tenant_id", "workflow_runs.id"]),
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'failed', 'timed_out', 'cancelled')",
            name="ck_workflow_steps_job_status",
        ),
        Index("ix_workflow_steps_tenant_run", "tenant_id", "workflow_run_id"),
    )

    workflow_run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    step_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    input: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)


class ToolCall(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "tool_calls"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "workflow_run_id"], ["workflow_runs.tenant_id", "workflow_runs.id"]),
        ForeignKeyConstraint(["tenant_id", "workflow_step_id"], ["workflow_steps.tenant_id", "workflow_steps.id"]),
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'failed', 'timed_out', 'cancelled')",
            name="ck_tool_calls_job_status",
        ),
        Index("ix_tool_calls_tenant_run", "tenant_id", "workflow_run_id"),
    )

    workflow_run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    workflow_step_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    input: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)


class ApprovalRequest(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "workflow_run_id"], ["workflow_runs.tenant_id", "workflow_runs.id"]),
        ForeignKeyConstraint(["tenant_id", "workflow_step_id"], ["workflow_steps.tenant_id", "workflow_steps.id"]),
        ForeignKeyConstraint(["tenant_id", "reviewer_user_id"], ["users.tenant_id", "users.id"]),
        CheckConstraint("status in ('pending', 'approved', 'rejected', 'expired')", name="ck_approval_requests_status"),
        Index("ix_approval_requests_tenant_status", "tenant_id", "status"),
    )

    workflow_run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    workflow_step_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    reviewer_user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    reviewed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)
    decision_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class IdempotencyKey(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_idempotency_keys_tenant_key"),)

    key: Mapped[str] = mapped_column(String(160), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))


class LLMUsageRecord(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "llm_usage_records"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "workflow_run_id"], ["workflow_runs.tenant_id", "workflow_runs.id"]),
        Index("ix_llm_usage_records_tenant_run", "tenant_id", "workflow_run_id"),
    )

    workflow_run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    token_input: Mapped[int] = mapped_column(nullable=False, default=0)
    token_output: Mapped[int] = mapped_column(nullable=False, default=0)
    estimated_cost: Mapped[object | None] = mapped_column(Numeric(12, 6))
    latency_ms: Mapped[int | None] = mapped_column()
