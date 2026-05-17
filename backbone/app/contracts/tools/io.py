from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import JobStatus


class ToolCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    tool_name: str = Field(min_length=1, max_length=120)
    payload: dict = Field(default_factory=dict)


class ToolCallResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: JobStatus
    output: dict = Field(default_factory=dict)
    error_message: str | None = None

