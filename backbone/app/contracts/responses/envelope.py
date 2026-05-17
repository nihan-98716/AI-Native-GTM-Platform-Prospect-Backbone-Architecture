from pydantic import BaseModel, ConfigDict
from pydantic import Field


class SuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool = True
    data: dict


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool = False
    error: str
    code: str
    details: dict = Field(default_factory=dict)
