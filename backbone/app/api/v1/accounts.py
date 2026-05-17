from fastapi import APIRouter, Depends

from app.api.deps import (
    enforce_rate_limit,
    get_accounts_service,
    get_authorizer,
    get_current_claims,
    get_tenant_context,
)
from app.contracts.api.accounts import ListAccountsQuery, ListAccountsResponse
from app.contracts.api.auth import TokenClaims
from app.contracts.responses.envelope import SuccessEnvelope
from app.core.tenancy import TenantContext
from app.services.accounts import AccountsService

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=SuccessEnvelope)
def list_accounts(
    query: ListAccountsQuery = Depends(),
    claims: TokenClaims = Depends(get_current_claims),
    context: TenantContext = Depends(get_tenant_context),
    _: None = Depends(enforce_rate_limit),
    authorizer=Depends(get_authorizer),
    service: AccountsService = Depends(get_accounts_service),
) -> SuccessEnvelope:
    authorizer.require(claims=claims, required_permission="accounts:read")
    payload: ListAccountsResponse = service.list_accounts(context=context, query=query)
    return SuccessEnvelope(data=payload.model_dump())

