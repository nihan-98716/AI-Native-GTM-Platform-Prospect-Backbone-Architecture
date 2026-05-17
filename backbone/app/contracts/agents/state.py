from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import JobStatus

class AgentStepState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_name: str
    status: JobStatus
    input: dict = Field(default_factory=dict)
    output: dict = Field(default_factory=dict)
    error_message: str | None = None


class ProspectWorkflowState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    account_ids: list[str] = Field(default_factory=list)
    contact_ids: list[str] = Field(default_factory=list)
    signal_ids: list[str] = Field(default_factory=list)
    hypothesis_ids: list[str] = Field(default_factory=list)
    outreach_ids: list[str] = Field(default_factory=list)
    current_step: str | None = None

