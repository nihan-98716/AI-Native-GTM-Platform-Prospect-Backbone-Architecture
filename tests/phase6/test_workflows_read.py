import os
from uuid import uuid4
from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.repositories.prospect_workflow_repository import SqlProspectWorkflowRepository
from app.models.workflows import WorkflowRun, WorkflowStep, ToolCall
from app.core.tenancy import TenantContext

DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.fixture()
def engine():
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL is required for DB-backed phase 6 tests")
    created = create_engine(DATABASE_URL)
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture()
def db(engine):
    with engine.begin() as connection:
        for table_name in ["tool_calls", "workflow_steps", "workflow_runs", "approval_requests"]:
            connection.execute(text(f"delete from {table_name}"))
    yield engine


def create_tenant(connection, slug: str):
    return connection.execute(text("insert into tenants (name, slug) values (:name, :slug) returning id"), {"name": slug, "slug": slug}).scalar_one()


def test_list_workflows_returns_summaries(db):
    with db.begin() as connection:
        tenant = create_tenant(connection, "workflows-a")

    session = Session(db)
    try:
        repo = SqlProspectWorkflowRepository(session)
        run = WorkflowRun(tenant_id=tenant, workflow_type="prospect", status="succeeded", idempotency_key=str(uuid4()), input={}, output={"traces": [{"trace_id": "t-123"}]})
        session.add(run)
        session.flush()
        step = WorkflowStep(tenant_id=tenant, workflow_run_id=run.id, step_name="research", status="completed", input={"trace_id": "t-123"}, output={})
        session.add(step)
        session.flush()
        session.commit()

        summaries = repo.list_workflow_runs(tenant_id=tenant, limit=10, offset=0)
        assert len(summaries) == 1
        s = summaries[0]
        assert s.workflow_run_id == run.id
        assert s.tenant_id == tenant
        assert s.trace_id == "t-123"
        assert s.duration_ms >= 0
    finally:
        session.close()


def test_cross_tenant_access_denied(db):
    with db.begin() as connection:
        tenant_a = create_tenant(connection, "ta")
        tenant_b = create_tenant(connection, "tb")

    session = Session(db)
    try:
        repo = SqlProspectWorkflowRepository(session)
        run = WorkflowRun(tenant_id=tenant_a, workflow_type="prospect", status="succeeded", idempotency_key=str(uuid4()), input={}, output={})
        session.add(run)
        session.flush()
        session.commit()

        retrieved = repo.get_workflow_run(tenant_id=tenant_b, workflow_run_id=run.id)
        assert retrieved is None
    finally:
        session.close()


def test_missing_workflow_returns_none(db):
    with db.begin() as connection:
        tenant = create_tenant(connection, "missing")

    session = Session(db)
    try:
        repo = SqlProspectWorkflowRepository(session)
        assert repo.get_workflow_run(tenant_id=tenant, workflow_run_id=str(uuid4())) is None
    finally:
        session.close()


def test_trace_fields_present(db):
    with db.begin() as connection:
        tenant = create_tenant(connection, "trace")

    session = Session(db)
    try:
        repo = SqlProspectWorkflowRepository(session)
        run = WorkflowRun(tenant_id=tenant, workflow_type="prospect", status="running", idempotency_key=str(uuid4()), input={}, output={})
        session.add(run)
        session.flush()
        step = WorkflowStep(tenant_id=tenant, workflow_run_id=run.id, step_name="research", status="running", input={"trace_id": "t-x", "correlation_id": "c-x"}, output={})
        session.add(step)
        session.flush()
        call = ToolCall(tenant_id=tenant, workflow_run_id=run.id, workflow_step_id=step.id, tool_name="Apollo", status="completed", input={"trace_id": "t-x", "correlation_id": "c-x"}, output={})
        session.add(call)
        session.flush()
        session.commit()

        steps = repo.list_workflow_steps(tenant_id=tenant, workflow_run_id=run.id)
        calls = repo.list_tool_calls(tenant_id=tenant, workflow_run_id=run.id)
        assert len(steps) == 1
        assert steps[0].trace_id == "t-x"
        assert steps[0].correlation_id == "c-x"
        assert len(calls) == 1
        assert calls[0].trace_id == "t-x"
        assert calls[0].correlation_id == "c-x"
    finally:
        session.close()
