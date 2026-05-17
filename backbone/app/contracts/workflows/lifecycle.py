from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import DecisionType, TerminalStatus


class WorkflowStartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_scope: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class WorkflowOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str | None = None
    metrics: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class WorkflowStart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    actor_user_id: str
    workflow_type: str = Field(min_length=1, max_length=80)
    icp_id: str | None = None
    account_id: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=160)
    input: WorkflowStartInput = Field(default_factory=WorkflowStartInput)


class WorkflowPause(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    reason: str = Field(min_length=1)
    checkpoint: str | None = None


class WorkflowResume(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    approval_request_id: str
    reviewer_user_id: str
    decision: DecisionType
    reason: str | None = None


class WorkflowCancel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    actor_user_id: str
    reason: str = Field(min_length=1)


class WorkflowComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    terminal_status: TerminalStatus
    output: WorkflowOutput = Field(default_factory=WorkflowOutput)

