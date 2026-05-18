from typing import Protocol

from app.contracts.agents import OutreachDraftProposal, ValueHypothesisDraft
from app.contracts.events.audit import AuditEventCreate
from app.contracts.tools import (
    AccountToolRecord,
    ApprovalCheckpoint,
    ContactToolRecord,
    ICPToolRecord,
    SignalToolRecord,
    ToolCallRecord,
    WorkflowRunToolRecord,
    WorkflowStepRecord,
)
from app.contracts.workflows.lifecycle import WorkflowStart
from app.core.tenancy import TenantContext
from app.contracts.integrations import IntegrationSearchAccountsOutput, IntegrationEnrichContactsOutput, IntegrationDiscoverSignalsOutput


class ProspectAgentTools(Protocol):
    def ensure_workflow_run(self, command: WorkflowStart) -> WorkflowRunToolRecord:
        ...

    def get_workflow_run(self, *, tenant_id: str, workflow_run_id: str) -> WorkflowRunToolRecord | None:
        ...

    def update_workflow_status(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        status: str,
        output: dict | None = None,
        heartbeat: bool = False,
    ) -> WorkflowRunToolRecord:
        ...

    def get_icp(self, *, tenant_id: str, icp_id: str | None) -> ICPToolRecord | None:
        ...

    def get_accounts(self, *, tenant_id: str, limit: int) -> list[AccountToolRecord]:
        ...

    def get_contacts(self, *, tenant_id: str, account_ids: list[str]) -> list[ContactToolRecord]:
        ...

    def get_signals(self, *, tenant_id: str, account_ids: list[str]) -> list[SignalToolRecord]:
        ...

    def search_provider_accounts(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        query: str | None,
        limit: int,
        trace_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        ...

    def enrich_provider_contacts(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        account_ids: list[str],
        trace_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        ...

    def discover_provider_signals(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        account_ids: list[str],
        trace_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        ...

    def save_hypotheses(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        drafts: list[ValueHypothesisDraft],
        generated_by_agent: str,
    ) -> list[str]:
        ...

    def save_outreach_drafts(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        drafts: list[OutreachDraftProposal],
        generated_by_agent: str,
    ) -> list[str]:
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

    def add_workflow_step(
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

    def add_tool_call(
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

    def add_llm_usage(
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

    def add_audit_event(self, *, context: TenantContext, event: AuditEventCreate) -> None:
        ...

