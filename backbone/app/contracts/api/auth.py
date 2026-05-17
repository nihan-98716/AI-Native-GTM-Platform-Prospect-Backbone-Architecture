from pydantic import BaseModel, ConfigDict, Field


class TokenClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sub: str
    tenant_id: str
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    iss: str | None = None
    aud: str | None = None
    exp: int | None = None
    iat: int | None = None


class TokenValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: TokenClaims
    token_id: str | None = None

