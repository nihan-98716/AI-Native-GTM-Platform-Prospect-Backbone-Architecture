import time
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.contracts.events.audit import AuditEventRecord, AuditEventScoped
from app.models.identity import AuditEvent
from app.observability.runtime import ObservabilityRuntime, get_observability_runtime


class SqlAuditEventRepository:
    def __init__(self, session: Session, observability: ObservabilityRuntime | None = None) -> None:
        self._session = session
        self._obs = observability or get_observability_runtime()

    def create(self, event: AuditEventScoped) -> AuditEventRecord:
        started = time.perf_counter()
        record = AuditEvent(
            tenant_id=event.tenant_id,
            actor_user_id=event.actor_user_id,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            metadata_=event.metadata,
        )
        self._session.add(record)
        self._session.flush()
        self._obs.emit_operation(
            service="repositories.audit.create",
            status="ok",
            duration_ms=int((time.perf_counter() - started) * 1000),
            tenant_id=event.tenant_id,
        )
        return AuditEventRecord(
            id=record.id,
            tenant_id=record.tenant_id,
            actor_user_id=record.actor_user_id,
            action=record.action,
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            metadata=record.metadata_,
            created_at=record.created_at if isinstance(record.created_at, datetime) else datetime.now(tz=UTC),
        )

