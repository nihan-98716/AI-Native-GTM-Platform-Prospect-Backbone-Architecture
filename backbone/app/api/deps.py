from collections.abc import Generator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.audit.service import SqlAuditService
from app.agents.llm import OpenAIChatLLM
from app.auth import Hs256TokenVerifier, RbacAuthorizer, TokenValidationError
from app.contracts.api.auth import TokenClaims
from app.core.config import Settings, get_settings
from app.core.rate_limit import FixedWindowRateLimiter
from app.core.tenancy import TenantContext, set_tenant_context
from app.repositories.account_repository import SqlAccountRepository
from app.repositories.audit_repository import SqlAuditEventRepository
from app.repositories.prospect_workflow_repository import SqlProspectWorkflowRepository
from app.services.accounts import AccountsService
from app.services.prospect import ProspectWorkflowService
from app.storage.db import get_session


def get_db_session() -> Generator[Session, None, None]:
    yield from get_session()


def get_token_verifier(settings: Settings = Depends(get_settings)) -> Hs256TokenVerifier:
    return Hs256TokenVerifier(settings)


def get_authorizer() -> RbacAuthorizer:
    return RbacAuthorizer()


_rate_limiter: FixedWindowRateLimiter | None = None


def get_rate_limiter(settings: Settings = Depends(get_settings)) -> FixedWindowRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = FixedWindowRateLimiter(settings.rate_limit_per_minute)
    return _rate_limiter


def get_current_claims(
    authorization: str = Header(default="", alias="Authorization"),
    verifier: Hs256TokenVerifier = Depends(get_token_verifier),
) -> TokenClaims:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token is required.")
    token = authorization[7:].strip()
    try:
        claims = verifier.verify(token)
    except TokenValidationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return claims


def get_tenant_context(claims: TokenClaims = Depends(get_current_claims)) -> TenantContext:
    context = TenantContext.from_claims(claims)
    set_tenant_context(context)
    return context


def enforce_rate_limit(
    context: TenantContext = Depends(get_tenant_context),
    limiter: FixedWindowRateLimiter = Depends(get_rate_limiter),
) -> None:
    key = f"{context.tenant_id}:{context.actor_user_id}"
    if not limiter.allow(key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded.")


def get_accounts_service(session: Session = Depends(get_db_session)) -> AccountsService:
    return AccountsService(repository=SqlAccountRepository(session))


def get_audit_service(session: Session = Depends(get_db_session)) -> SqlAuditService:
    return SqlAuditService(repository=SqlAuditEventRepository(session))


def get_agent_llm(settings: Settings = Depends(get_settings)) -> OpenAIChatLLM:
    return OpenAIChatLLM.from_settings(settings)


def get_prospect_workflow_service(
    session: Session = Depends(get_db_session),
    audit_service: SqlAuditService = Depends(get_audit_service),
    llm: OpenAIChatLLM = Depends(get_agent_llm),
) -> ProspectWorkflowService:
    return ProspectWorkflowService(repository=SqlProspectWorkflowRepository(session), audit_service=audit_service, llm=llm)

