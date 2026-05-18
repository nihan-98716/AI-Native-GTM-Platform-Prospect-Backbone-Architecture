from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.integrations.common import (
    IntegrationAuthType,
    IntegrationConnectionStatus,
    IntegrationExecutionStatus,
    IntegrationOperationType,
    IntegrationSyncStatus,
)


class IntegrationCredentials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    auth_type: IntegrationAuthType
    api_key: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class IntegrationConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    provider: str = Field(min_length=1, max_length=80)
    connection_name: str = Field(default="default", min_length=1, max_length=120)
    is_default: bool = True
    auth_type: IntegrationAuthType
    credentials: IntegrationCredentials | None = None
    scopes: list[str] = Field(default_factory=list)
    health: dict = Field(default_factory=dict)


class IntegrationConnectionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    provider: str
    connection_name: str
    is_default: bool
    auth_type: IntegrationAuthType
    status: IntegrationConnectionStatus
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    health: dict = Field(default_factory=dict)
    has_credentials: bool = False
    created_at: datetime
    updated_at: datetime


class IntegrationConnectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: IntegrationConnectionStatus | None = None
    is_default: bool | None = None
    scopes: list[str] | None = None
    expires_at: datetime | None = None
    health: dict | None = None
    has_credentials: bool | None = None


class IntegrationExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    connection_id: str
    provider: str
    operation: IntegrationOperationType
    input: dict = Field(default_factory=dict)
    request_metadata: dict = Field(default_factory=dict)
    trace_id: str | None = None
    correlation_id: str | None = None


class IntegrationExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    tenant_id: str
    connection_id: str
    provider: str
    operation: IntegrationOperationType
    status: IntegrationExecutionStatus
    request_metadata: dict = Field(default_factory=dict)
    response_metadata: dict = Field(default_factory=dict)
    counts: dict = Field(default_factory=dict)
    error_message: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    started_at: datetime
    finished_at: datetime
    duration_ms: int = 0


class IntegrationExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    operation: IntegrationOperationType
    status: IntegrationExecutionStatus
    source_provider: str | None = None
    source_type: str | None = None
    source_record_id: str | None = None
    ingestion_timestamp: datetime | None = None
    response_payload: dict = Field(default_factory=dict)
    response_metadata: dict = Field(default_factory=dict)
    counts: dict = Field(default_factory=dict)
    error_message: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    started_at: datetime
    finished_at: datetime
    duration_ms: int = 0


class IntegrationSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    connection_id: str
    provider: str
    source_type: str
    cursor_name: str
    sync_cursor: dict = Field(default_factory=dict)
    request_metadata: dict = Field(default_factory=dict)
    trace_id: str | None = None
    correlation_id: str | None = None


class IntegrationSyncRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sync_cursor_id: str
    tenant_id: str
    connection_id: str
    provider: str
    source_provider: str | None = None
    source_type: str
    source_record_id: str | None = None
    ingestion_timestamp: datetime | None = None
    status: IntegrationSyncStatus
    request_metadata: dict = Field(default_factory=dict)
    response_metadata: dict = Field(default_factory=dict)
    sync_cursor: dict = Field(default_factory=dict)
    error_message: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    started_at: datetime
    finished_at: datetime
    duration_ms: int = 0


class IntegrationSyncResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    source_provider: str | None = None
    status: IntegrationSyncStatus
    sync_cursor: dict = Field(default_factory=dict)
    source_record_id: str | None = None
    ingestion_timestamp: datetime | None = None
    response_payload: dict = Field(default_factory=dict)
    response_metadata: dict = Field(default_factory=dict)
    error_message: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    started_at: datetime
    finished_at: datetime
    duration_ms: int = 0

