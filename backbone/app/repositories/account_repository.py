from typing import Sequence
import time

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.contracts.api.accounts import AccountSummary
from app.models.gtm import Account
from app.observability.runtime import ObservabilityRuntime, get_observability_runtime


class SqlAccountRepository:
    def __init__(self, session: Session, observability: ObservabilityRuntime | None = None) -> None:
        self._session = session
        self._obs = observability or get_observability_runtime()

    @staticmethod
    def build_query(*, tenant_id: str, limit: int, offset: int) -> Select:
        return (
            select(Account)
            .where(Account.tenant_id == tenant_id)
            .order_by(Account.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

    def list_by_tenant(self, *, tenant_id: str, limit: int, offset: int) -> Sequence[AccountSummary]:
        started = time.perf_counter()
        stmt = self.build_query(tenant_id=tenant_id, limit=limit, offset=offset)
        rows = self._session.execute(stmt).scalars().all()
        items = [
            AccountSummary(
                id=row.id,
                tenant_id=row.tenant_id,
                name=row.name,
                domain=row.domain,
                lifecycle_stage=row.lifecycle_stage,
            )
            for row in rows
        ]
        self._obs.emit_operation(
            service="repositories.accounts.list_by_tenant",
            status="ok",
            duration_ms=int((time.perf_counter() - started) * 1000),
            tenant_id=tenant_id,
        )
        return items

