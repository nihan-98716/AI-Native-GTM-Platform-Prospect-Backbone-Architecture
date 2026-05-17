from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import ApprovalStatus, WorkflowStatus
from app.contracts.workflows.execution import WorkflowEvidence
from app.contracts.workflows.lifecycle import WorkflowStartInput


class StartProspectWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_type: str = "prospect"
    icp_id: str | None = None
    account_id: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=160)
    input: WorkflowStartInput = Field(default_factory=WorkflowStartInput)
    require_human_approval: bool = True


class ResumeProspectWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_run_id: str
    approval_request_id: str
    decision: ApprovalStatus
    reason: str | None = None


class ProspectWorkflowStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_run_id: str
    status: WorkflowStatus
    current_step: str | None = None
    approval_status: ApprovalStatus | None = None
    approval_request_id: str | None = None
    hypothesis_count: int = 0
    outreach_count: int = 0
    trace_count: int = 0
    estimated_cost_usd: float = 0
    estimated_latency_ms: int = 0


class ProspectWorkflowActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_run_id: str
    status: WorkflowStatus
    current_step: str | None = None
    approval_status: ApprovalStatus | None = None
    approval_request_id: str | None = None
    evidence: WorkflowEvidence = Field(default_factory=WorkflowEvidence)
    estimated_cost_usd: float = 0
    estimated_latency_ms: int = 0

