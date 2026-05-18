from typing import Protocol, Sequence

from app.contracts.api.accounts import AccountSummary
from app.contracts.events.audit import AuditEventRecord, AuditEventScoped
from app.contracts.integrations import (
    IntegrationConnectionCreate,
    IntegrationConnectionRecord,
    IntegrationConnectionUpdate,
    IntegrationCredentials,
    IntegrationExecutionRecord,
    IntegrationExecutionRequest,
    IntegrationSyncRecord,
    IntegrationSyncRequest,
)
from app.contracts.tools.prospect import (
    AccountToolRecord,
    ApprovalCheckpoint,
    ContactToolRecord,
    ICPToolRecord,
    SignalToolRecord,
    ToolCallRecord,
    WorkflowRunToolRecord,
    WorkflowRunSummary,
    WorkflowStepRecord,
)
from app.contracts.workflows.lifecycle import WorkflowStart


class AccountRepository(Protocol):
    def list_by_tenant(self, *, tenant_id: str, limit: int, offset: int) -> Sequence[AccountSummary]:
        ...


class AuditEventRepository(Protocol):
    def create(self, event: AuditEventScoped) -> AuditEventRecord:
        ...


class IntegrationRepository(Protocol):
    def list_connections(self, *, tenant_id: str, provider: str | None = None) -> Sequence[IntegrationConnectionRecord]:
        ...

    def get_connection(self, *, tenant_id: str, connection_id: str) -> IntegrationConnectionRecord | None:
        ...

    def get_connection_credentials(self, *, tenant_id: str, connection_id: str) -> IntegrationCredentials | None:
        ...

    def get_default_connection(self, *, tenant_id: str, provider: str) -> IntegrationConnectionRecord | None:
        ...

    def save_connection(
        self,
        command: IntegrationConnectionCreate,
        *,
        encrypted_credentials: bytes | None = None,
        status: str | None = None,
    ) -> IntegrationConnectionRecord:
        ...

    def update_connection(
        self,
        *,
        tenant_id: str,
        connection_id: str,
        update: IntegrationConnectionUpdate,
    ) -> IntegrationConnectionRecord:
        ...

    def create_execution_run(
        self,
        request: IntegrationExecutionRequest,
        *,
        status: str,
        response_metadata: dict | None = None,
        counts: dict | None = None,
        error_message: str | None = None,
        started_at=None,
        finished_at=None,
    ) -> IntegrationExecutionRecord:
        ...

    def update_execution_run(
        self,
        *,
        tenant_id: str,
        run_id: str,
        status: str,
        response_metadata: dict | None = None,
        counts: dict | None = None,
        error_message: str | None = None,
        started_at=None,
        finished_at=None,
    ) -> IntegrationExecutionRecord:
        ...

    def get_sync_cursor(
        self,
        *,
        tenant_id: str,
        connection_id: str,
        cursor_name: str,
    ) -> IntegrationSyncRecord | None:
        ...

    def save_sync_cursor(
        self,
        request: IntegrationSyncRequest,
        *,
        status: str,
        response_metadata: dict | None = None,
        error_message: str | None = None,
        source_record_id: str | None = None,
        started_at=None,
        finished_at=None,
    ) -> IntegrationSyncRecord:
        ...


class ProspectWorkflowRepository(Protocol):
    def get_icp(self, *, tenant_id: str, icp_id: str | None) -> ICPToolRecord | None:
        ...

    def list_accounts_for_research(self, *, tenant_id: str, limit: int) -> Sequence[AccountToolRecord]:
        ...

    def list_contacts_by_account_ids(self, *, tenant_id: str, account_ids: list[str]) -> Sequence[ContactToolRecord]:
        ...

    def list_signals_by_account_ids(self, *, tenant_id: str, account_ids: list[str]) -> Sequence[SignalToolRecord]:
        ...

    def get_workflow_run(self, *, tenant_id: str, workflow_run_id: str) -> WorkflowRunToolRecord | None:
        ...

    def get_workflow_run_by_idempotency(self, *, tenant_id: str, idempotency_key: str) -> WorkflowRunToolRecord | None:
        ...

    def create_workflow_run(self, command: WorkflowStart) -> WorkflowRunToolRecord:
        ...

    def update_workflow_run_status(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        status: str,
        output: dict | None = None,
        heartbeat: bool = False,
    ) -> WorkflowRunToolRecord:
        ...

    def record_workflow_step(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        step_name: str,
        status: str,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        input_payload: dict,
        output_payload: dict,
        error_message: str | None = None,
    ) -> WorkflowStepRecord:
        ...

    def record_tool_call(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        workflow_step_id: str | None,
        tool_name: str,
        status: str,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        input_payload: dict,
        output_payload: dict,
        error_message: str | None = None,
    ) -> ToolCallRecord:
        ...

    def create_approval_checkpoint(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        workflow_step_id: str | None,
        reason: str,
    ) -> ApprovalCheckpoint:
        ...

    def get_approval_checkpoint(
        self,
        *,
        tenant_id: str,
        approval_request_id: str,
    ) -> ApprovalCheckpoint | None:
        ...

    def update_approval_checkpoint(
        self,
        *,
        tenant_id: str,
        approval_request_id: str,
        status: str,
        reviewer_user_id: str | None = None,
        reason: str | None = None,
    ) -> ApprovalCheckpoint:
        ...

    def persist_hypothesis(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        account_id: str,
        contact_id: str | None,
        title: str,
        hypothesis: str,
        confidence_score: float,
        metadata: dict,
        generated_by_agent: str,
    ) -> str:
        ...

    def persist_outreach_draft(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        account_id: str,
        contact_id: str | None,
        subject: str,
        body: str,
        status: str,
        metadata: dict,
        generated_by_agent: str,
    ) -> str:
        ...

    def record_llm_usage(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        model: str,
        token_input: int,
        token_output: int,
        estimated_cost: float,
        latency_ms: int,
    ) -> str:
        ...

    def count_value_hypotheses(self, *, tenant_id: str, workflow_run_id: str) -> int:
        ...

    def count_outreach_drafts(self, *, tenant_id: str, workflow_run_id: str) -> int:
        ...

    def count_workflow_steps(self, *, tenant_id: str, workflow_run_id: str) -> int:
        ...

    def count_tool_calls(self, *, tenant_id: str, workflow_run_id: str) -> int:
        ...

    def count_llm_usage(self, *, tenant_id: str, workflow_run_id: str) -> tuple[float, int]:
        ...

    def list_workflow_runs(self, *, tenant_id: str, limit: int = 50, offset: int = 0) -> Sequence[WorkflowRunSummary]:
        ...

    def get_workflow_run_summary(self, *, tenant_id: str, workflow_run_id: str) -> WorkflowRunSummary | None:
        ...

    def list_workflow_steps(self, *, tenant_id: str, workflow_run_id: str) -> Sequence[WorkflowStepRecord]:
        ...

    def list_tool_calls(self, *, tenant_id: str, workflow_run_id: str) -> Sequence[ToolCallRecord]:
        ...

