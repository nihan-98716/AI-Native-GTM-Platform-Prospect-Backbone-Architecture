from typing import Protocol, Sequence

from app.contracts.api.accounts import AccountSummary
from app.contracts.events.audit import AuditEventRecord, AuditEventScoped


class AccountRepository(Protocol):
    def list_by_tenant(self, *, tenant_id: str, limit: int, offset: int) -> Sequence[AccountSummary]:
        ...


class AuditEventRepository(Protocol):
    def create(self, event: AuditEventScoped) -> AuditEventRecord:
        ...

