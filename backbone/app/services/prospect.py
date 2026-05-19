from datetime import UTC, datetime

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
from app.services.integrations import IntegrationService
from app.workers.workflow import ProspectWorkflowWorker


class ProspectWorkflowService:
    def __init__(
        self,
        repository: ProspectWorkflowRepository,
        audit_service: AuditService | None = None,
        integration_service: IntegrationService | None = None,
        llm: AgentLLM | None = None,
    ) -> None:
        self._repository = repository
        self._tools = DefaultProspectAgentTools(repository, audit_service=audit_service, integration_service=integration_service)
        self._llm = llm
        self._engine = ProspectWorkflowEngine(self._tools, llm) if llm is not None else None
        self._worker = ProspectWorkflowWorker(repository)

    def _workflow_engine(self) -> ProspectWorkflowEngine:
        if self._engine is None:
            self._llm = OpenAIChatLLM.from_settings()
            self._engine = ProspectWorkflowEngine(self._tools, self._llm)
        return self._engine

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
            source_provider="prospect-workflow",
            source_type="generated",
            ingestion_timestamp=datetime.now(tz=UTC),
            source_record_id=run.workflow_run_id,
            evidence=WorkflowEvidence(),
        )
        state = self._worker.run_inline(initial_state, context=context, execute=self._workflow_engine().execute)
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
        state.source_provider = state.source_provider or "prospect-workflow"
        state.source_type = state.source_type or "generated"
        state.source_record_id = state.source_record_id or request.workflow_run_id
        state.ingestion_timestamp = state.ingestion_timestamp or datetime.now(tz=UTC)
        resumed = self._worker.run_inline(state, context=context, execute=self._workflow_engine().execute)
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
        payload.setdefault("source_provider", run.output.get("source_provider") or "prospect-workflow")
        payload.setdefault("source_type", run.output.get("source_type") or "generated")
        payload.setdefault("source_record_id", run.output.get("source_record_id") or run.workflow_run_id)
        payload.setdefault("ingestion_timestamp", run.output.get("ingestion_timestamp"))
        payload.setdefault("retry_count", run.output.get("retry_count", 0))
        payload.setdefault("attempt_metadata", run.output.get("attempt_metadata", []))
        payload.setdefault("evidence", run.output.get("evidence", {}))
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

    def list_workflows(self, context: TenantContext, limit: int = 50, offset: int = 0) -> list:
        """Return workflow summaries for the tenant."""
        runs = self._repository.list_workflow_runs(tenant_id=context.tenant_id, limit=limit, offset=offset)
        # runs are WorkflowRunSummary pydantic objects from the repository
        return runs

    def get_workflow_detail(self, context: TenantContext, workflow_run_id: str) -> dict:
        """Return detailed workflow data including timeline and tool calls."""
        summary = self._repository.get_workflow_run_summary(tenant_id=context.tenant_id, workflow_run_id=workflow_run_id)
        if summary is None:
            raise LookupError("Workflow run not found.")
        steps = self._repository.list_workflow_steps(tenant_id=context.tenant_id, workflow_run_id=workflow_run_id)
        tool_calls = self._repository.list_tool_calls(tenant_id=context.tenant_id, workflow_run_id=workflow_run_id)
        run = self._repository.get_workflow_run(tenant_id=context.tenant_id, workflow_run_id=workflow_run_id)
        audit_refs: list[str] = []
        if run and isinstance(run.output, dict):
            evidence = run.output.get("evidence") or {}
            if isinstance(evidence, dict):
                audit_refs = evidence.get("approval_request_ids") or []
        return {
            "metadata": {
                "workflow_run_id": summary.workflow_run_id,
                "tenant_id": summary.tenant_id,
                "workflow_type": summary.workflow_type,
                "status": summary.status,
                "created_at": summary.created_at,
                "updated_at": summary.updated_at,
                "duration": summary.duration_ms,
                "trace_id": summary.trace_id,
            },
            "timeline": [s.model_dump(mode="json") if hasattr(s, "model_dump") else s for s in steps],
            "tool_calls": [t.model_dump(mode="json") if hasattr(t, "model_dump") else t for t in tool_calls],
            "audit_references": audit_refs,
        }
