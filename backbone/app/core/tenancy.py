from contextvars import ContextVar
from dataclasses import dataclass

from app.contracts.api.auth import TokenClaims


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    actor_user_id: str
    roles: tuple[str, ...]
    permissions: tuple[str, ...]

    @classmethod
    def from_claims(cls, claims: TokenClaims) -> "TenantContext":
        return cls(
            tenant_id=claims.tenant_id,
            actor_user_id=claims.sub,
            roles=tuple(claims.roles),
            permissions=tuple(claims.permissions),
        )


tenant_context_var: ContextVar[TenantContext | None] = ContextVar("tenant_context", default=None)


def set_tenant_context(context: TenantContext) -> None:
    tenant_context_var.set(context)


def get_tenant_context() -> TenantContext:
    context = tenant_context_var.get()
    if context is None:
        raise RuntimeError("Tenant context is not set for this request.")
    return context

