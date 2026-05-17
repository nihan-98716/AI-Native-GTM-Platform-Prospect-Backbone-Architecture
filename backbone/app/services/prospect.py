from app.agents.llm import AgentLLM, OpenAIChatLLM
from app.agents.tools.runtime import DefaultProspectAgentTools
from app.agents.workflow import ProspectWorkflowEngine
from app.audit.interfaces import AuditService
from app.contracts.api.prospect import (
    ProspectWorkflowActionResponse,
    ProspectWorkflowStatusResponse,
    ResumeProspectWorkflowRequest,
    StartProspectWorkflowRequest,
)
from app.contracts.common import ApprovalStatus, WorkflowEventType, WorkflowStatus
from app.contracts.events.audit import AuditEventCreate
from app.contracts.workflows.execution import WorkflowEvidence, ProspectWorkflowExecutionState
from app.contracts.workflows.lifecycle import WorkflowStart, WorkflowStartInput
from app.core.tenancy import TenantContext
from app.repositories.interfaces import ProspectWorkflowRepository


class ProspectWorkflowService:
    def __init__(
        self,
        repository: ProspectWorkflowRepository,
        audit_service: AuditService | None = None,
        llm: AgentLLM | None = None,
    ) -> None:
        self._repository = repository
        self._tools = DefaultProspectAgentTools(repository, audit_service=audit_service)
        self._llm = llm or OpenAIChatLLM.from_settings()
        self._engine = ProspectWorkflowEngine(self._tools, self._llm)

    def start_workflow(self, context: TenantContext, request: StartProspectWorkflowRequest) -> ProspectWorkflowActionResponse:
        existing = self._repository.get_workflow_run_by_idempotency(
            tenant_id=context.tenant_id,
            idempotency_key=request.idempotency_key,
        )
        if existing and existing.output:
            state = ProspectWorkflowExecutionState.model_validate(existing.output)
            return self._action_response(state)

        command = WorkflowStart(
            tenant_id=context.tenant_id,
            actor_user_id=context.actor_user_id,
            workflow_type=request.workflow_type,
            icp_id=request.icp_id,
            account_id=request.account_id,
            idempotency_key=request.idempotency_key,
            input=WorkflowStartInput(
                target_scope=request.input.target_scope,
                metadata={
                    **request.input.metadata,
                    "require_human_approval": request.require_human_approval,
                    "idempotency_key": request.idempotency_key,
                },
            ),
        )
        run = existing or self._repository.create_workflow_run(command)
        initial_state = ProspectWorkflowExecutionState(
            tenant_id=context.tenant_id,
            workflow_run_id=run.workflow_run_id,
            workflow_type=request.workflow_type,
            icp_id=request.icp_id,
            account_id=request.account_id,
            idempotency_key=request.idempotency_key,
            require_human_approval=request.require_human_approval,
            status=WorkflowStatus.running,
            current_step="research",
            evidence=WorkflowEvidence(),
        )
        self._repository.update_workflow_run_status(
            tenant_id=context.tenant_id,
            workflow_run_id=run.workflow_run_id,
            status=WorkflowStatus.running.value,
            output=initial_state.model_dump(mode="json"),
            heartbeat=True,
        )
        state = self._engine.execute(initial_state, context=context)
        return self._action_response(state)

    def resume_workflow(self, context: TenantContext, request: ResumeProspectWorkflowRequest) -> ProspectWorkflowActionResponse:
        run = self._repository.get_workflow_run(tenant_id=context.tenant_id, workflow_run_id=request.workflow_run_id)
        if run is None:
            raise LookupError("Workflow run not found.")
        checkpoint = self._repository.get_approval_checkpoint(
            tenant_id=context.tenant_id,
            approval_request_id=request.approval_request_id,
        )
        if checkpoint is None:
            raise LookupError("Approval checkpoint not found.")
        checkpoint = self._repository.update_approval_checkpoint(
            tenant_id=context.tenant_id,
            approval_request_id=request.approval_request_id,
            status=request.decision.value,
            reviewer_user_id=context.actor_user_id,
            reason=request.reason,
        )
        if request.decision == ApprovalStatus.rejected:
            state = self._state_from_run(run, approval_status=ApprovalStatus.rejected, approval_request_id=checkpoint.approval_request_id)
            state.status = WorkflowStatus.cancelled
            self._tools.add_audit_event(
                context=context,
                event=AuditEventCreate(
                    actor_user_id=context.actor_user_id,
                    action=WorkflowEventType.workflow_cancelled.value,
                    resource_type="workflow_run",
                    resource_id=request.workflow_run_id,
                    metadata={"approval_request_id": checkpoint.approval_request_id, "reason": request.reason},
                ),
            )
            self._repository.update_workflow_run_status(
                tenant_id=context.tenant_id,
                workflow_run_id=request.workflow_run_id,
                status=WorkflowStatus.cancelled.value,
                output=state.model_dump(mode="json"),
                heartbeat=True,
            )
            return self._action_response(state)

        state = self._state_from_run(run, approval_status=ApprovalStatus.approved, approval_request_id=checkpoint.approval_request_id)
        state.status = WorkflowStatus.running
        state.current_step = "approval_gate"
        self._repository.update_workflow_run_status(
            tenant_id=context.tenant_id,
            workflow_run_id=request.workflow_run_id,
            status=WorkflowStatus.running.value,
            output=state.model_dump(mode="json"),
            heartbeat=True,
        )
        resumed = self._engine.execute(state, context=context)
        return self._action_response(resumed)

    def get_status(self, context: TenantContext, workflow_run_id: str) -> ProspectWorkflowStatusResponse:
        run = self._repository.get_workflow_run(tenant_id=context.tenant_id, workflow_run_id=workflow_run_id)
        if run is None:
            raise LookupError("Workflow run not found.")
        state = self._state_from_run(run)
        hypothesis_count = self._repository.count_value_hypotheses(tenant_id=context.tenant_id, workflow_run_id=workflow_run_id)
        outreach_count = self._repository.count_outreach_drafts(tenant_id=context.tenant_id, workflow_run_id=workflow_run_id)
        trace_count = len(state.traces)
        return ProspectWorkflowStatusResponse(
            workflow_run_id=workflow_run_id,
            status=state.status,
            current_step=state.current_step,
            approval_status=state.approval_status,
            approval_request_id=state.approval_request_id,
            hypothesis_count=hypothesis_count,
            outreach_count=outreach_count,
            trace_count=trace_count,
            estimated_cost_usd=state.estimated_cost_usd,
            estimated_latency_ms=state.estimated_latency_ms,
        )

    def _state_from_run(
        self,
        run,
        *,
        approval_status: ApprovalStatus | None = None,
        approval_request_id: str | None = None,
    ) -> ProspectWorkflowExecutionState:
        payload = run.output or {}
        payload.setdefault("tenant_id", run.tenant_id)
        payload.setdefault("workflow_run_id", run.workflow_run_id)
        payload.setdefault("workflow_type", run.workflow_type)
        payload.setdefault("idempotency_key", run.input.get("metadata", {}).get("idempotency_key", ""))
        payload.setdefault("require_human_approval", run.input.get("metadata", {}).get("require_human_approval", True))
        state = ProspectWorkflowExecutionState.model_validate(payload)
        if approval_status is not None:
            state.approval_status = approval_status
        if approval_request_id is not None:
            state.approval_request_id = approval_request_id
        return state

    @staticmethod
    def _action_response(state: ProspectWorkflowExecutionState) -> ProspectWorkflowActionResponse:
        return ProspectWorkflowActionResponse(
            workflow_run_id=state.workflow_run_id,
            status=state.status,
            current_step=state.current_step,
            approval_status=state.approval_status,
            approval_request_id=state.approval_request_id,
            evidence=state.evidence,
            estimated_cost_usd=state.estimated_cost_usd,
            estimated_latency_ms=state.estimated_latency_ms,
        )

