from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_user_id: str | None = None
    action: str = Field(min_length=1, max_length=120)
    resource_type: str = Field(min_length=1, max_length=120)
    resource_id: str | None = None
    metadata: dict = Field(default_factory=dict)
    occurred_at: datetime | None = None


class AuditEventScoped(AuditEventCreate):
    tenant_id: str


class AuditEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    actor_user_id: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime

