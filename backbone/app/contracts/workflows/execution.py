from pydantic import BaseModel, ConfigDict, Field

from app.contracts.agents import (
    AgentTraceEntry,
    EnrichedContact,
    IntentAssessment,
    OutreachDraftProposal,
    RankedAccount,
    ValueHypothesisDraft,
)
from app.contracts.common import ApprovalStatus, WorkflowStatus


class WorkflowEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_ids: list[str] = Field(default_factory=list)
    tool_call_ids: list[str] = Field(default_factory=list)
    approval_request_ids: list[str] = Field(default_factory=list)
    trace_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class WorkflowExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_run_id: str
    status: WorkflowStatus
    current_step: str | None = None
    approval_status: ApprovalStatus | None = None
    approval_request_id: str | None = None
    evidence: WorkflowEvidence = Field(default_factory=WorkflowEvidence)
    estimated_cost_usd: float = 0
    estimated_latency_ms: int = 0


class ProspectWorkflowExecutionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    workflow_type: str = "prospect"
    icp_id: str | None = None
    account_id: str | None = None
    idempotency_key: str
    require_human_approval: bool = True
    status: WorkflowStatus = WorkflowStatus.queued
    current_step: str | None = None
    ranked_accounts: list[RankedAccount] = Field(default_factory=list)
    enriched_contacts: list[EnrichedContact] = Field(default_factory=list)
    intent_assessments: list[IntentAssessment] = Field(default_factory=list)
    hypotheses: list[ValueHypothesisDraft] = Field(default_factory=list)
    outreach_drafts: list[OutreachDraftProposal] = Field(default_factory=list)
    approval_status: ApprovalStatus | None = None
    approval_request_id: str | None = None
    evidence: WorkflowEvidence = Field(default_factory=WorkflowEvidence)
    estimated_cost_usd: float = 0
    estimated_latency_ms: int = 0
    traces: list[AgentTraceEntry] = Field(default_factory=list)
    trace_summary: list[str] = Field(default_factory=list)
    last_error: str | None = None

