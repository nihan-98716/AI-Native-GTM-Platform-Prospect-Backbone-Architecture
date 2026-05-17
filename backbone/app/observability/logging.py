from datetime import UTC, datetime
from uuid import uuid4


def request_log_fields(
    *,
    service: str,
    tenant_id: str | None = None,
    workflow_id: str | None = None,
    trace_id: str | None = None,
    correlation_id: str | None = None,
    request_id: str | None = None,
    status: str = "ok",
    duration_ms: int | None = None,
) -> dict:
    return {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "trace_id": trace_id or str(uuid4()),
        "correlation_id": correlation_id or str(uuid4()),
        "request_id": request_id or str(uuid4()),
        "tenant_id": tenant_id,
        "workflow_id": workflow_id,
        "service": service,
        "status": status,
        "duration_ms": duration_ms,
    }

