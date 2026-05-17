from app.observability.logging import request_log_fields


def test_request_log_fields_include_required_keys():
    fields = request_log_fields(service="api.test", tenant_id="t1", status="ok", duration_ms=12)
    required = {
        "trace_id",
        "correlation_id",
        "tenant_id",
        "request_id",
        "workflow_id",
        "service",
        "status",
        "duration_ms",
    }
    assert required.issubset(fields.keys())
    assert fields["tenant_id"] == "t1"

