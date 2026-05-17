import logging
from uuid import uuid4

from app.observability.interfaces import Logger, Meter, Tracer
from app.observability.logging import request_log_fields


class UuidTracer:
    def next_ids(self) -> tuple[str, str]:
        return str(uuid4()), str(uuid4())


class NoOpMeter:
    def increment(self, name: str, *, value: int = 1, tags: dict[str, str] | None = None) -> None:
        _ = (name, value, tags)

    def timing(self, name: str, duration_ms: int, *, tags: dict[str, str] | None = None) -> None:
        _ = (name, duration_ms, tags)


class StructuredLogger:
    def __init__(self, logger_name: str = "gtm.observability") -> None:
        self._logger = logging.getLogger(logger_name)

    def info(self, payload: dict) -> None:
        self._logger.info(payload)

    def error(self, payload: dict) -> None:
        self._logger.error(payload)


class ObservabilityRuntime:
    def __init__(self, tracer: Tracer | None = None, meter: Meter | None = None, logger: Logger | None = None) -> None:
        self._tracer = tracer or UuidTracer()
        self._meter = meter or NoOpMeter()
        self._logger = logger or StructuredLogger()

    def emit_operation(
        self,
        *,
        service: str,
        status: str,
        duration_ms: int,
        tenant_id: str | None = None,
        workflow_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
    ) -> dict:
        resolved_trace, resolved_correlation = (trace_id, correlation_id)
        if not resolved_trace or not resolved_correlation:
            generated_trace, generated_correlation = self._tracer.next_ids()
            resolved_trace = resolved_trace or generated_trace
            resolved_correlation = resolved_correlation or generated_correlation

        payload = request_log_fields(
            service=service,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            trace_id=resolved_trace,
            correlation_id=resolved_correlation,
            request_id=request_id,
            status=status,
            duration_ms=duration_ms,
        )
        tags = {"service": service, "status": status}
        self._meter.increment("operations_total", value=1, tags=tags)
        self._meter.timing("operation_duration_ms", duration_ms=duration_ms, tags=tags)
        if status == "error":
            self._logger.error(payload)
        else:
            self._logger.info(payload)
        return payload


_runtime: ObservabilityRuntime | None = None


def get_observability_runtime() -> ObservabilityRuntime:
    global _runtime
    if _runtime is None:
        _runtime = ObservabilityRuntime()
    return _runtime

