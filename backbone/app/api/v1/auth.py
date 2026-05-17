from fastapi import APIRouter, Depends

from app.api.deps import get_current_claims
from app.contracts.api.auth import TokenClaims
from app.contracts.responses.envelope import SuccessEnvelope

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=SuccessEnvelope)
def me(claims: TokenClaims = Depends(get_current_claims)) -> SuccessEnvelope:
    return SuccessEnvelope(data=claims.model_dump())

