from pydantic import BaseModel, ConfigDict, Field


class AccountSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    name: str
    domain: str | None = None
    lifecycle_stage: str


class ListAccountsQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ListAccountsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AccountSummary]
    count: int

