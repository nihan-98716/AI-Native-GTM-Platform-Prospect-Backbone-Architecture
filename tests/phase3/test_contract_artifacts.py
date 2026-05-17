from app.contracts.common import (
    DecisionType,
    JobStatus,
    TerminalStatus,
    WorkflowEventType,
    WorkflowStatus,
    WorkflowTransitionPayload,
)
from app.contracts.agents import ProspectWorkflowState
from app.contracts.api import AccountSummary, TokenClaims
from app.contracts.events import AuditEventCreate, WorkflowEvent
from app.contracts.responses import ErrorEnvelope, SuccessEnvelope
from app.contracts.tools import ToolCallRequest, ToolCallResult
from app.contracts.workflows import WorkflowComplete, WorkflowResume, WorkflowStart


def test_contract_packages_are_importable():
    account = AccountSummary(
        id="a1",
        tenant_id="t1",
        name="Acme",
        domain="acme.test",
        lifecycle_stage="prospect",
    )
    assert account.name == "Acme"
    assert TokenClaims(sub="u1", tenant_id="t1").tenant_id == "t1"
    assert AuditEventCreate(action="a", resource_type="r").action == "a"
    assert (
        WorkflowEvent(
            tenant_id="t1",
            workflow_run_id="w1",
            event_type=WorkflowEventType.workflow_started,
            payload=WorkflowTransitionPayload(to_status=WorkflowStatus.queued),
        ).event_type
        == WorkflowEventType.workflow_started
    )
    assert ToolCallRequest(tenant_id="t1", workflow_run_id="w1", tool_name="search").tool_name == "search"
    assert WorkflowStart(tenant_id="t1", actor_user_id="u1", workflow_type="prospect", idempotency_key="k1").workflow_type == "prospect"
    assert WorkflowResume(
        tenant_id="t1",
        workflow_run_id="w1",
        approval_request_id="a1",
        reviewer_user_id="u1",
        decision=DecisionType.approved,
    ).decision == DecisionType.approved
    assert WorkflowComplete(tenant_id="t1", workflow_run_id="w1", terminal_status=TerminalStatus.succeeded).terminal_status == TerminalStatus.succeeded
    assert ToolCallResult(status=JobStatus.completed).status == JobStatus.completed
    assert ProspectWorkflowState(tenant_id="t1", workflow_run_id="w1").workflow_run_id == "w1"
    assert SuccessEnvelope(data={"ok": True}).success is True
    assert ErrorEnvelope(error="oops", code="x").success is False

