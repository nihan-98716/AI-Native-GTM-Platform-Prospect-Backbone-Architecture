from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import WorkflowEventType, WorkflowTransitionPayload

class WorkflowEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_run_id: str
    event_type: WorkflowEventType
    payload: WorkflowTransitionPayload
    occurred_at: datetime | None = None

