from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

from app.contracts.integrations.common import IntegrationExecutionStatus, IntegrationSyncStatus


class IntegrationAccountRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_account_id: str
    name: str
    domain: str | None = None
    website: str | None = None
    confidence_score: float = Field(ge=0, le=100)
    metadata: dict = Field(default_factory=dict)


class IntegrationContactRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_contact_id: str
    provider_account_id: str | None = None
    full_name: str
    email: str | None = None
    title: str | None = None
    confidence_score: float = Field(ge=0, le=100)
    metadata: dict = Field(default_factory=dict)


class IntegrationSignalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_signal_id: str
    provider_account_id: str | None = None
    signal_type: str
    strength: float = Field(ge=0, le=100)
    source: str
    observed_at: str
    metadata: dict = Field(default_factory=dict)


class IntegrationSearchAccountsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: IntegrationExecutionStatus
    provider: str
    source_provider: str | None = None
    source_type: str | None = None
    source_record_id: str | None = None
    ingestion_timestamp: datetime | None = None
    records: list[IntegrationAccountRecord] = Field(default_factory=list)
    response_metadata: dict = Field(default_factory=dict)
    error_message: str | None = None


class IntegrationEnrichContactsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: IntegrationExecutionStatus
    provider: str
    source_provider: str | None = None
    source_type: str | None = None
    source_record_id: str | None = None
    ingestion_timestamp: datetime | None = None
    records: list[IntegrationContactRecord] = Field(default_factory=list)
    response_metadata: dict = Field(default_factory=dict)
    error_message: str | None = None


class IntegrationDiscoverSignalsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: IntegrationExecutionStatus
    provider: str
    source_provider: str | None = None
    source_type: str | None = None
    source_record_id: str | None = None
    ingestion_timestamp: datetime | None = None
    records: list[IntegrationSignalRecord] = Field(default_factory=list)
    response_metadata: dict = Field(default_factory=dict)
    error_message: str | None = None


class IntegrationSyncOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: IntegrationSyncStatus
    provider: str
    source_provider: str | None = None
    sync_cursor: dict = Field(default_factory=dict)
    source_record_id: str | None = None
    ingestion_timestamp: datetime | None = None
    response_metadata: dict = Field(default_factory=dict)
    error_message: str | None = None

