import enum


class IntegrationAuthType(str, enum.Enum):
    api_key = "api_key"
    oauth2 = "oauth2"
    manual_config = "manual_config"


class IntegrationConnectionStatus(str, enum.Enum):
    not_configured = "not_configured"
    live = "live"
    failed = "failed"
    rate_limited = "rate_limited"


class IntegrationExecutionStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    rate_limited = "rate_limited"
    cancelled = "cancelled"
    timed_out = "timed_out"


class IntegrationSyncStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    rate_limited = "rate_limited"
    cancelled = "cancelled"
    timed_out = "timed_out"


class IntegrationOperationType(str, enum.Enum):
    search_accounts = "search_accounts"
    enrich_contacts = "enrich_contacts"
    discover_signals = "discover_signals"
    sync = "sync"
    validate = "validate"
    health_check = "health_check"

