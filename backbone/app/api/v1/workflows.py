from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_current_claims,
    get_tenant_context,
    get_prospect_workflow_service,
    get_authorizer,
    enforce_rate_limit,
)
from app.contracts.api.workflows import WorkflowSummary, WorkflowDetail
from app.contracts.responses.envelope import SuccessEnvelope
from app.contracts.api.auth import TokenClaims
from app.core.tenancy import TenantContext

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/", response_model=SuccessEnvelope)
def list_workflows(
    limit: int = 50,
    offset: int = 0,
    claims: TokenClaims = Depends(get_current_claims),
    context: TenantContext = Depends(get_tenant_context),
    _: None = Depends(enforce_rate_limit),
    authorizer=Depends(get_authorizer),
    service=Depends(get_prospect_workflow_service),
) -> SuccessEnvelope:
    authorizer.require(claims=claims, required_permission="prospect:read")
    results = service.list_workflows(context=context, limit=limit, offset=offset)
    items = [r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in results]
    payload = {"items": items, "count": len(items)}
    return SuccessEnvelope(data=payload)


@router.get("/{workflow_run_id}", response_model=SuccessEnvelope)
def get_workflow_detail(
    workflow_run_id: str,
    claims: TokenClaims = Depends(get_current_claims),
    context: TenantContext = Depends(get_tenant_context),
    _: None = Depends(enforce_rate_limit),
    authorizer=Depends(get_authorizer),
    service=Depends(get_prospect_workflow_service),
) -> SuccessEnvelope:
    authorizer.require(claims=claims, required_permission="prospect:read")
    try:
        result = service.get_workflow_detail(context=context, workflow_run_id=workflow_run_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SuccessEnvelope(data=result)
