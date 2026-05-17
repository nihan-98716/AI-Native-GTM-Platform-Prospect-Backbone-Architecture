import enum

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    waiting_for_approval = "waiting_for_approval"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
    timed_out = "timed_out"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    timed_out = "timed_out"
    cancelled = "cancelled"


class WorkflowEventType(str, enum.Enum):
    workflow_started = "workflow_started"
    workflow_paused = "workflow_paused"
    workflow_resumed = "workflow_resumed"
    workflow_cancelled = "workflow_cancelled"
    workflow_completed = "workflow_completed"
    workflow_failed = "workflow_failed"


class DecisionType(str, enum.Enum):
    approved = "approved"
    rejected = "rejected"


class TerminalStatus(str, enum.Enum):
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
    timed_out = "timed_out"


class WorkflowTransitionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_status: WorkflowStatus | None = None
    to_status: WorkflowStatus
    decision: DecisionType | None = None
    reason: str | None = None
    metadata: dict = Field(default_factory=dict)

