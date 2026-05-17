import enum


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"


class IntegrationStatus(str, enum.Enum):
    not_configured = "not_configured"
    live = "live"
    failed = "failed"
    rate_limited = "rate_limited"


class IntegrationAuthType(str, enum.Enum):
    api_key = "api_key"
    oauth2 = "oauth2"
    manual_config = "manual_config"


class SourceType(str, enum.Enum):
    seeded = "seeded"
    imported = "imported"
    generated = "generated"


class WorkflowStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    waiting_for_approval = "waiting_for_approval"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
    timed_out = "timed_out"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    timed_out = "timed_out"
    cancelled = "cancelled"
