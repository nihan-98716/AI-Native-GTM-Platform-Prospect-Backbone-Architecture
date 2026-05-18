from __future__ import annotations

import uuid
from datetime import UTC, datetime
import importlib.util
from pathlib import Path

_seed_module_path = Path(__file__).resolve().parents[1] / "phase7_seed_data.py"
_seed_spec = importlib.util.spec_from_file_location("phase7_seed_data", _seed_module_path)
assert _seed_spec is not None and _seed_spec.loader is not None
_seed_module = importlib.util.module_from_spec(_seed_spec)
_seed_spec.loader.exec_module(_seed_module)
SeedDataGenerator = _seed_module.TestDataGenerator


class FakeSession:
    def __init__(self) -> None:
        self._objects: list[object] = []
        self.committed = False

    def add(self, obj: object) -> None:
        self._objects.append(obj)

    def add_all(self, objects: list[object]) -> None:
        self._objects.extend(objects)

    def flush(self) -> None:
        for obj in self._objects:
            if hasattr(obj, "id") and getattr(obj, "id", None) is None:
                setattr(obj, "id", str(uuid.uuid4()))

    def commit(self) -> None:
        self.committed = True


def test_seed_generation_executes_with_model_aligned_payloads():
    session = FakeSession()
    generator = SeedDataGenerator(session=session)  # type: ignore[arg-type]

    results = generator.generate_all()

    assert session.committed is True
    assert len(results["tenants"]) == 3
    assert set(results.keys()) >= {
        "tenants",
        "users",
        "accounts",
        "contacts",
        "signals",
        "icps",
        "workflow_runs",
        "workflow_steps",
        "hypotheses",
        "outreach_drafts",
        "approval_requests",
        "integration_connections",
        "integration_runs",
        "audit_events",
    }


def test_seed_generation_preserves_tenant_ownership_traceability_and_timestamps():
    session = FakeSession()
    generator = SeedDataGenerator(session=session)  # type: ignore[arg-type]
    results = generator.generate_all()

    now = datetime.now(tz=UTC)
    for tenant in results["tenants"]:
        tenant_id = tenant.id
        accounts = results["accounts"][tenant_id]
        workflows = results["workflow_runs"][tenant_id]
        integrations = results["integration_connections"][tenant_id]
        audits = results["audit_events"][tenant_id]

        assert len(accounts) == 25
        assert len(workflows) == 5
        assert len(integrations) == 2
        assert len(audits) == 5

        account_domains = {a.domain for a in accounts}
        assert len(account_domains) == len(accounts)
        assert all(a.tenant_id == tenant_id for a in accounts)
        assert all(a.source_type == "seeded" for a in accounts)
        assert all(a.ingestion_timestamp is not None for a in accounts)
        assert all(a.created_at <= now for a in accounts)

        workflow_statuses = {w.status for w in workflows}
        assert workflow_statuses == {"succeeded", "running", "queued", "waiting_for_approval", "failed"}
        assert all("trace_id" in w.input and "correlation_id" in w.input for w in workflows)
        assert all("trace_id" in w.output and "correlation_id" in w.output for w in workflows)

        assert all(c.tenant_id == tenant_id for c in integrations)
        assert {c.provider for c in integrations} == {"apollo", "hubspot"}

        assert all(event.tenant_id == tenant_id for event in audits)
        assert all(event.metadata_.get("trace_id") for event in audits)
