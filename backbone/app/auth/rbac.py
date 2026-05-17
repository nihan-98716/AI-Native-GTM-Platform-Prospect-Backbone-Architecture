import time

from app.contracts.api.auth import TokenClaims
from app.observability.runtime import ObservabilityRuntime, get_observability_runtime


class AuthorizationError(PermissionError):
    pass


class RbacAuthorizer:
    def __init__(self, observability: ObservabilityRuntime | None = None) -> None:
        self._obs = observability or get_observability_runtime()

    def require(self, claims: TokenClaims, required_permission: str) -> None:
        started = time.perf_counter()
        if "platform_admin" in claims.roles:
            self._obs.emit_operation(
                service="auth.rbac.require",
                status="ok",
                duration_ms=int((time.perf_counter() - started) * 1000),
                tenant_id=claims.tenant_id,
            )
            return
        if required_permission in claims.permissions:
            self._obs.emit_operation(
                service="auth.rbac.require",
                status="ok",
                duration_ms=int((time.perf_counter() - started) * 1000),
                tenant_id=claims.tenant_id,
            )
            return
        wildcard_domain = required_permission.split(":", maxsplit=1)[0] + ":*"
        if wildcard_domain in claims.permissions or "*:*" in claims.permissions:
            self._obs.emit_operation(
                service="auth.rbac.require",
                status="ok",
                duration_ms=int((time.perf_counter() - started) * 1000),
                tenant_id=claims.tenant_id,
            )
            return
        self._obs.emit_operation(
            service="auth.rbac.require",
            status="error",
            duration_ms=int((time.perf_counter() - started) * 1000),
            tenant_id=claims.tenant_id,
        )
        raise AuthorizationError(f"Missing required permission '{required_permission}'.")

