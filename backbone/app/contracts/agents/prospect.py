from datetime import datetime
import enum

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import ApprovalStatus, JobStatus, OutreachDraftStatus


class IntentClass(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class AgentEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    estimated_input_tokens: int = Field(ge=0)
    estimated_output_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)
    estimated_latency_ms: int = Field(ge=0)


class AgentRetryPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_attempts: int = Field(default=2, ge=1, le=5)
    backoff_ms: int = Field(default=100, ge=0, le=10_000)
    fallback_enabled: bool = True


class AgentTraceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str
    attempt: int = Field(ge=1)
    status: JobStatus
    reasoning_summary: str
    tool_invocations: list[str] = Field(default_factory=list)
    tenant_id: str | None = None
    workflow_run_id: str | None = None
    current_step: str | None = None
    approval_status: ApprovalStatus | None = None
    prompt_name: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    started_at: datetime
    finished_at: datetime
    error_message: str | None = None


class RankedAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    rank_score: float = Field(ge=0, le=100)
    reasoning_summary: str


class ProspectResearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    icp_id: str | None = None
    account_limit: int = Field(default=10, ge=1, le=100)


class ProspectResearchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ranked_accounts: list[RankedAccount] = Field(default_factory=list)
    estimate: AgentEstimate
    trace: AgentTraceEntry


class EnrichedContact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_id: str
    completeness_score: float = Field(ge=0, le=100)
    confidence_score: float = Field(ge=0, le=100)
    metadata: dict = Field(default_factory=dict)


class ContactEnrichmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    account_ids: list[str] = Field(default_factory=list)


class ContactEnrichmentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enriched_contacts: list[EnrichedContact] = Field(default_factory=list)
    estimate: AgentEstimate
    trace: AgentTraceEntry


class IntentAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    intent_class: IntentClass
    intent_strength: float = Field(ge=0, le=100)
    evidence_summary: str
    evidence_items: list[str] = Field(default_factory=list)


class IntentSignalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    account_ids: list[str] = Field(default_factory=list)


class IntentSignalOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessments: list[IntentAssessment] = Field(default_factory=list)
    estimate: AgentEstimate
    trace: AgentTraceEntry


class ValueHypothesisDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    contact_id: str | None = None
    title: str
    hypothesis: str
    supporting_evidence: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=100)


class ValueHypothesisInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    account_ids: list[str] = Field(default_factory=list)
    contact_ids: list[str] = Field(default_factory=list)
    assessments: list[IntentAssessment] = Field(default_factory=list)


class ValueHypothesisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypotheses: list[ValueHypothesisDraft] = Field(default_factory=list)
    estimate: AgentEstimate
    trace: AgentTraceEntry


class OutreachDraftProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    contact_id: str | None = None
    subject: str
    body: str
    status: OutreachDraftStatus
    review_notes: str | None = None


class OutreachInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    hypotheses: list[ValueHypothesisDraft] = Field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.pending


class OutreachOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drafts: list[OutreachDraftProposal] = Field(default_factory=list)
    estimate: AgentEstimate
    trace: AgentTraceEntry

