from datetime import UTC, datetime

from app.agents.tools.interfaces import ProspectAgentTools
from app.audit.interfaces import AuditService
from app.contracts.agents import OutreachDraftProposal, ValueHypothesisDraft
from app.contracts.integrations import IntegrationAccountRecord, IntegrationContactRecord, IntegrationSignalRecord
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
from app.core.tenancy import TenantContext, get_tenant_context
from app.repositories.interfaces import ProspectWorkflowRepository
from typing import Any


class DefaultProspectAgentTools(ProspectAgentTools):
    def __init__(
        self,
        repository: ProspectWorkflowRepository,
        audit_service: AuditService | None = None,
        integration_service: Any | None = None,
    ) -> None:
        self._repository = repository
        self._audit_service = audit_service
        self._integration_service = integration_service

    def ensure_workflow_run(self, command: WorkflowStart) -> WorkflowRunToolRecord:
        existing = self._repository.get_workflow_run_by_idempotency(
            tenant_id=command.tenant_id,
            idempotency_key=command.idempotency_key,
        )
        if existing:
            return existing
        return self._repository.create_workflow_run(command)

    def get_workflow_run(self, *, tenant_id: str, workflow_run_id: str) -> WorkflowRunToolRecord | None:
        return self._repository.get_workflow_run(tenant_id=tenant_id, workflow_run_id=workflow_run_id)

    def update_workflow_status(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        status: str,
        output: dict | None = None,
        heartbeat: bool = False,
    ) -> WorkflowRunToolRecord:
        return self._repository.update_workflow_run_status(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            status=status,
            output=output,
            heartbeat=heartbeat,
        )

    def get_icp(self, *, tenant_id: str, icp_id: str | None) -> ICPToolRecord | None:
        return self._repository.get_icp(tenant_id=tenant_id, icp_id=icp_id)

    def get_accounts(self, *, tenant_id: str, limit: int) -> list[AccountToolRecord]:
        return list(self._repository.list_accounts_for_research(tenant_id=tenant_id, limit=limit))

    def get_contacts(self, *, tenant_id: str, account_ids: list[str]) -> list[ContactToolRecord]:
        return list(self._repository.list_contacts_by_account_ids(tenant_id=tenant_id, account_ids=account_ids))

    def get_signals(self, *, tenant_id: str, account_ids: list[str]) -> list[SignalToolRecord]:
        return list(self._repository.list_signals_by_account_ids(tenant_id=tenant_id, account_ids=account_ids))

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
        if self._integration_service is None:
            return {"status": "failed", "provider": None, "records": [], "error_message": "Integration service is not configured."}
        context = self._resolve_tenant_context(tenant_id)
        output = self._integration_service.search_accounts(
            context,
            query=query,
            limit=limit,
            trace_id=trace_id,
            correlation_id=correlation_id,
            workflow_run_id=workflow_run_id,
        )
        records = [
            AccountToolRecord(
                account_id=item.provider_account_id,
                name=item.name,
                domain=item.domain,
                lifecycle_stage="prospect",
                firmographics={"provider": output.provider, "confidence_score": item.confidence_score, **item.metadata},
            ).model_dump(mode="json")
            for item in output.records
        ]
        return {
            "status": output.status.value,
            "provider": output.provider,
            "records": records,
            "response_metadata": output.response_metadata,
            "error_message": output.error_message,
        }

    def enrich_provider_contacts(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        account_ids: list[str],
        trace_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        if self._integration_service is None:
            return {"status": "failed", "provider": None, "records": [], "error_message": "Integration service is not configured."}
        context = self._resolve_tenant_context(tenant_id)
        output = self._integration_service.enrich_contacts(
            context,
            account_ids=account_ids,
            trace_id=trace_id,
            correlation_id=correlation_id,
            workflow_run_id=workflow_run_id,
        )
        records = [
            ContactToolRecord(
                contact_id=item.provider_contact_id,
                account_id=item.provider_account_id or (account_ids[0] if account_ids else ""),
                full_name=item.full_name,
                email=item.email,
                title=item.title,
                custom_fields={"provider": output.provider, "confidence_score": item.confidence_score, **item.metadata},
            ).model_dump(mode="json")
            for item in output.records
        ]
        return {
            "status": output.status.value,
            "provider": output.provider,
            "records": records,
            "response_metadata": output.response_metadata,
            "error_message": output.error_message,
        }

    def discover_provider_signals(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        account_ids: list[str],
        trace_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        if self._integration_service is None:
            return {"status": "failed", "provider": None, "records": [], "error_message": "Integration service is not configured."}
        context = self._resolve_tenant_context(tenant_id)
        output = self._integration_service.discover_signals(
            context,
            account_ids=account_ids,
            trace_id=trace_id,
            correlation_id=correlation_id,
            workflow_run_id=workflow_run_id,
        )
        records = [
            SignalToolRecord(
                signal_id=item.provider_signal_id,
                account_id=item.provider_account_id or (account_ids[0] if account_ids else ""),
                signal_type=item.signal_type,
                strength=item.strength,
                source=item.source,
                payload=item.metadata,
                observed_at=item.observed_at,
            ).model_dump(mode="json")
            for item in output.records
        ]
        return {
            "status": output.status.value,
            "provider": output.provider,
            "records": records,
            "response_metadata": output.response_metadata,
            "error_message": output.error_message,
        }

    def save_hypotheses(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        drafts: list[ValueHypothesisDraft],
        generated_by_agent: str,
    ) -> list[str]:
        ids: list[str] = []
        for item in drafts:
            ids.append(
                self._repository.persist_hypothesis(
                    tenant_id=tenant_id,
                    workflow_run_id=workflow_run_id,
                    account_id=item.account_id,
                    contact_id=item.contact_id,
                    title=item.title,
                    hypothesis=item.hypothesis,
                    confidence_score=item.confidence_score,
                    metadata={
                        "supporting_evidence": item.supporting_evidence,
                        "source_provider": "prospect-workflow",
                        "source_type": "generated",
                        "source_record_id": workflow_run_id,
                        "ingestion_timestamp": datetime.now(tz=UTC).isoformat(),
                    },
                    generated_by_agent=generated_by_agent,
                )
            )
        return ids

    def _resolve_tenant_context(self, tenant_id: str) -> TenantContext:
        context = get_tenant_context()
        if context.tenant_id != tenant_id:
            raise PermissionError("Tenant context does not match the requested tenant.")
        return context

    def save_outreach_drafts(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        drafts: list[OutreachDraftProposal],
        generated_by_agent: str,
    ) -> list[str]:
        ids: list[str] = []
        for item in drafts:
            ids.append(
                self._repository.persist_outreach_draft(
                    tenant_id=tenant_id,
                    workflow_run_id=workflow_run_id,
                    account_id=item.account_id,
                    contact_id=item.contact_id,
                    subject=item.subject,
                    body=item.body,
                    status=item.status.value,
                    metadata={
                        "review_notes": item.review_notes,
                        "source_provider": "prospect-workflow",
                        "source_type": "generated",
                        "source_record_id": workflow_run_id,
                        "ingestion_timestamp": datetime.now(tz=UTC).isoformat(),
                    },
                    generated_by_agent=generated_by_agent,
                )
            )
        return ids

    def create_approval_checkpoint(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        workflow_step_id: str | None,
        reason: str,
    ) -> ApprovalCheckpoint:
        return self._repository.create_approval_checkpoint(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            workflow_step_id=workflow_step_id,
            reason=reason,
        )

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
        return self._repository.record_workflow_step(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            step_name=step_name,
            status=status,
            trace_id=trace_id,
            correlation_id=correlation_id,
            input_payload=input_payload,
            output_payload=output_payload,
            error_message=error_message,
        )

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
        return self._repository.record_tool_call(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            workflow_step_id=workflow_step_id,
            tool_name=tool_name,
            status=status,
            trace_id=trace_id,
            correlation_id=correlation_id,
            input_payload=input_payload,
            output_payload=output_payload,
            error_message=error_message,
        )

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
        return self._repository.record_llm_usage(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            model=model,
            token_input=token_input,
            token_output=token_output,
            estimated_cost=estimated_cost,
            latency_ms=latency_ms,
        )

    def add_audit_event(self, *, context: TenantContext, event: AuditEventCreate) -> None:
        if self._audit_service is None:
            return
        self._audit_service.record(context=context, event=event)

