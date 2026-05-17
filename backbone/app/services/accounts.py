import time

from app.contracts.api.accounts import AccountSummary, ListAccountsQuery, ListAccountsResponse
from app.core.tenancy import TenantContext
from app.observability.runtime import ObservabilityRuntime, get_observability_runtime
from app.repositories.interfaces import AccountRepository


class AccountsService:
    def __init__(self, repository: AccountRepository, observability: ObservabilityRuntime | None = None) -> None:
        self._repository = repository
        self._obs = observability or get_observability_runtime()

    def list_accounts(self, context: TenantContext, query: ListAccountsQuery) -> ListAccountsResponse:
        started = time.perf_counter()
        items: list[AccountSummary] = list(self._repository.list_by_tenant(
            tenant_id=context.tenant_id,
            limit=query.limit,
            offset=query.offset,
        ))
        self._obs.emit_operation(
            service="services.accounts.list_accounts",
            status="ok",
            duration_ms=int((time.perf_counter() - started) * 1000),
            tenant_id=context.tenant_id,
        )
        return ListAccountsResponse(items=items, count=len(items))

