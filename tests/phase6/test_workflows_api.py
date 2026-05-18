import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.contracts.api.auth import TokenClaims
from app.core.tenancy import TenantContext
from app.api.deps import (
    get_current_claims,
    get_tenant_context,
    enforce_rate_limit,
    get_authorizer,
    get_prospect_workflow_service,
)


class DummyAuthorizer:
    def require(self, claims, required_permission):
        return None


class FakeWorkflowService:
    def __init__(self):
        self.sample_summary = {
            "workflow_id": "w-1",
            "workflow_type": "prospect",
            "workflow_status": "succeeded",
            "created_at": "2026-05-18T00:00:00Z",
            "updated_at": "2026-05-18T00:01:00Z",
            "duration": 60000,
            "tenant_id": "t1",
            "trace_id": "t-1",
        }
        self.sample_detail = {
            "metadata": {
                "workflow_run_id": "w-1",
                "tenant_id": "t1",
                "workflow_type": "prospect",
                "status": "succeeded",
                "created_at": "2026-05-18T00:00:00Z",
                "updated_at": "2026-05-18T00:01:00Z",
                "duration": 60000,
                "trace_id": "t-1",
            },
            "timeline": [],
            "tool_calls": [],
            "audit_references": [],
        }

    def list_workflows(self, context, limit=50, offset=0):
        return [self.sample_summary]

    def get_workflow_detail(self, context, workflow_run_id):
        if workflow_run_id == "missing":
            raise LookupError("Workflow run not found.")
        return self.sample_detail


# dependency overrides

def _claims_stub():
    return TokenClaims(sub="u1", tenant_id="t1", roles=["admin"], permissions=["prospect:read"])


def _tenant_context_stub():
    return TenantContext.from_claims(_claims_stub())


def _noop_rate_limit():
    return None


def _authorizer_stub():
    return DummyAuthorizer()


def _service_stub():
    return FakeWorkflowService()


@pytest.fixture(autouse=True)
def override_dependencies():
    app.dependency_overrides[get_current_claims] = lambda: _claims_stub()
    app.dependency_overrides[get_tenant_context] = lambda: _tenant_context_stub()
    app.dependency_overrides[enforce_rate_limit] = lambda: _noop_rate_limit()
    app.dependency_overrides[get_authorizer] = lambda: _authorizer_stub()
    app.dependency_overrides[get_prospect_workflow_service] = lambda: _service_stub()
    yield
    app.dependency_overrides.clear()


def test_list_workflows_endpoint():
    client = TestClient(app)
    headers = {"Authorization": "Bearer dummy"}
    resp = client.get("/v1/workflows", headers=headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    data = payload["data"]
    assert isinstance(data, dict)
    assert "items" in data and "count" in data
    items = data["items"]
    assert isinstance(items, list)
    assert items[0]["tenant_id"] == "t1"
    assert "trace_id" in items[0]


def test_get_workflow_detail_ok():
    client = TestClient(app)
    headers = {"Authorization": "Bearer dummy"}
    resp = client.get("/v1/workflows/w-1", headers=headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"]
    assert payload["data"]["metadata"]["workflow_run_id"] == "w-1"


def test_get_workflow_detail_missing():
    client = TestClient(app)
    headers = {"Authorization": "Bearer dummy"}
    resp = client.get("/v1/workflows/missing", headers=headers)
    assert resp.status_code == 404
