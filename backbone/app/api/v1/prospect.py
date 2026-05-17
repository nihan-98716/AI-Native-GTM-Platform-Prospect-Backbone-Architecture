from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    enforce_rate_limit,
    get_authorizer,
    get_current_claims,
    get_prospect_workflow_service,
    get_tenant_context,
)
from app.contracts.api.auth import TokenClaims
from app.contracts.api.prospect import (
    ProspectWorkflowActionResponse,
    ProspectWorkflowStatusResponse,
    ResumeProspectWorkflowRequest,
    StartProspectWorkflowRequest,
)
from app.contracts.responses.envelope import SuccessEnvelope
from app.core.tenancy import TenantContext
from app.services.prospect import ProspectWorkflowService

router = APIRouter(prefix="/prospect", tags=["prospect"])


@router.post("/workflows/start", response_model=SuccessEnvelope)
def start_workflow(
    request: StartProspectWorkflowRequest,
    claims: TokenClaims = Depends(get_current_claims),
    context: TenantContext = Depends(get_tenant_context),
    _: None = Depends(enforce_rate_limit),
    authorizer=Depends(get_authorizer),
    service: ProspectWorkflowService = Depends(get_prospect_workflow_service),
) -> SuccessEnvelope:
    authorizer.require(claims=claims, required_permission="prospect:write")
    response: ProspectWorkflowActionResponse = service.start_workflow(context=context, request=request)
    return SuccessEnvelope(data=response.model_dump(mode="json"))


@router.post("/workflows/resume", response_model=SuccessEnvelope)
def resume_workflow(
    request: ResumeProspectWorkflowRequest,
    claims: TokenClaims = Depends(get_current_claims),
    context: TenantContext = Depends(get_tenant_context),
    _: None = Depends(enforce_rate_limit),
    authorizer=Depends(get_authorizer),
    service: ProspectWorkflowService = Depends(get_prospect_workflow_service),
) -> SuccessEnvelope:
    authorizer.require(claims=claims, required_permission="prospect:write")
    try:
        response: ProspectWorkflowActionResponse = service.resume_workflow(context=context, request=request)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SuccessEnvelope(data=response.model_dump(mode="json"))


@router.get("/workflows/{workflow_run_id}", response_model=SuccessEnvelope)
def get_workflow_status(
    workflow_run_id: str,
    claims: TokenClaims = Depends(get_current_claims),
    context: TenantContext = Depends(get_tenant_context),
    _: None = Depends(enforce_rate_limit),
    authorizer=Depends(get_authorizer),
    service: ProspectWorkflowService = Depends(get_prospect_workflow_service),
) -> SuccessEnvelope:
    authorizer.require(claims=claims, required_permission="prospect:read")
    try:
        response: ProspectWorkflowStatusResponse = service.get_status(context=context, workflow_run_id=workflow_run_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SuccessEnvelope(data=response.model_dump(mode="json"))

