from typing import Protocol

from app.contracts.events.audit import AuditEventCreate, AuditEventRecord, AuditEventScoped
from app.core.tenancy import TenantContext


class AuditService(Protocol):
    def record(self, context: TenantContext, event: AuditEventCreate) -> AuditEventRecord:
        ...

    def record_scoped(self, context: TenantContext, event: AuditEventScoped) -> AuditEventRecord:
        ...

