from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.tools.prospect import WorkflowStepRecord, ToolCallRecord
from app.contracts.common import WorkflowStatus


class WorkflowSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    workflow_type: str
    workflow_status: WorkflowStatus
    created_at: datetime
    updated_at: datetime
    duration: int
    tenant_id: str
    trace_id: str | None = None


class WorkflowDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_run_id: str
    tenant_id: str
    workflow_type: str
    status: WorkflowStatus
    created_at: datetime
    updated_at: datetime
    duration: int
    trace_id: str | None = None
    correlation_id: str | None = None
    timeline: list[WorkflowStepRecord] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    audit_references: list[str] = Field(default_factory=list)
