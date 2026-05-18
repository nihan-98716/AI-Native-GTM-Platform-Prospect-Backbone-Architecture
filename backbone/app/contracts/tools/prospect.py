from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import ApprovalStatus, JobStatus, WorkflowStatus


class ICPToolRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    icp_id: str
    name: str
    description: str | None = None
    criteria: dict = Field(default_factory=dict)


class AccountToolRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    name: str
    domain: str | None = None
    lifecycle_stage: str
    firmographics: dict = Field(default_factory=dict)


class ContactToolRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_id: str
    account_id: str
    full_name: str
    email: str | None = None
    title: str | None = None
    custom_fields: dict = Field(default_factory=dict)


class SignalToolRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    account_id: str
    signal_type: str
    strength: float | None = None
    source: str
    payload: dict = Field(default_factory=dict)
    observed_at: datetime


class WorkflowStepRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    workflow_step_id: str
    step_name: str
    status: JobStatus
    trace_id: str | None = None
    correlation_id: str | None = None
    input: dict = Field(default_factory=dict)
    output: dict = Field(default_factory=dict)
    error_message: str | None = None


class ToolCallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    tool_call_id: str
    tool_name: str
    status: JobStatus
    trace_id: str | None = None
    correlation_id: str | None = None
    input: dict = Field(default_factory=dict)
    output: dict = Field(default_factory=dict)
    error_message: str | None = None


class ApprovalCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_request_id: str
    status: ApprovalStatus
    tenant_id: str
    workflow_run_id: str
    workflow_step_id: str | None = None
    reviewer_user_id: str | None = None
    reviewed_at: datetime | None = None
    reason: str | None = None


class WorkflowRunToolRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    status: WorkflowStatus
    workflow_type: str
    input: dict = Field(default_factory=dict)
    output: dict = Field(default_factory=dict)
    last_heartbeat_at: datetime | None = None


class WorkflowRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    status: WorkflowStatus
    workflow_type: str
    created_at: datetime
    updated_at: datetime
    duration_ms: int
    trace_id: str | None = None

