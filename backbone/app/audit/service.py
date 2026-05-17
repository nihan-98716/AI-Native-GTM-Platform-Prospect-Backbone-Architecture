import time

from app.contracts.events.audit import AuditEventCreate, AuditEventRecord, AuditEventScoped
from app.core.tenancy import TenantContext
from app.observability.runtime import ObservabilityRuntime, get_observability_runtime
from app.repositories.interfaces import AuditEventRepository


class AuditTenantMismatchError(PermissionError):
    pass


class SqlAuditService:
    def __init__(self, repository: AuditEventRepository, observability: ObservabilityRuntime | None = None) -> None:
        self._repository = repository
        self._obs = observability or get_observability_runtime()

    def record(self, context: TenantContext, event: AuditEventCreate) -> AuditEventRecord:
        return self.record_scoped(
            context,
            AuditEventScoped(
                tenant_id=context.tenant_id,
                actor_user_id=event.actor_user_id or context.actor_user_id,
                action=event.action,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                metadata=event.metadata,
                occurred_at=event.occurred_at,
            ),
        )

    def record_scoped(self, context: TenantContext, event: AuditEventScoped) -> AuditEventRecord:
        started = time.perf_counter()
        if event.tenant_id != context.tenant_id:
            self._obs.emit_operation(
                service="audit.record_scoped",
                status="error",
                duration_ms=int((time.perf_counter() - started) * 1000),
                tenant_id=context.tenant_id,
            )
            raise AuditTenantMismatchError("Cross-tenant audit writes are not allowed.")
        result = self._repository.create(event)
        self._obs.emit_operation(
            service="audit.record_scoped",
            status="ok",
            duration_ms=int((time.perf_counter() - started) * 1000),
            tenant_id=context.tenant_id,
        )
        return result

