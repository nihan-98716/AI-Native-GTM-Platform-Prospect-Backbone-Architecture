from datetime import UTC, datetime
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.contracts.common import ApprovalStatus, JobStatus, WorkflowStatus
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
from app.models.artifacts import OutreachDraft, ValueHypothesis
from app.models.gtm import Account, Contact, Signal
from app.models.prospect import ICPDefinition
from app.models.workflows import ApprovalRequest, LLMUsageRecord, ToolCall, WorkflowRun, WorkflowStep
from app.observability.runtime import ObservabilityRuntime, get_observability_runtime


class SqlProspectWorkflowRepository:
    def __init__(self, session: Session, observability: ObservabilityRuntime | None = None) -> None:
        self._session = session
        self._obs = observability or get_observability_runtime()

    def _emit(
        self,
        *,
        service: str,
        status: str,
        started: float,
        tenant_id: str | None = None,
        workflow_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self._obs.emit_operation(
            service=service,
            status=status,
            duration_ms=max(1, int((time.perf_counter() - started) * 1000)),
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
        )

    @staticmethod
    def _workflow_run_record(row: WorkflowRun) -> WorkflowRunToolRecord:
        return WorkflowRunToolRecord(
            tenant_id=row.tenant_id,
            workflow_run_id=row.id,
            status=WorkflowStatus(row.status),
            workflow_type=row.workflow_type,
            input=row.input,
            output=row.output,
            last_heartbeat_at=row.last_heartbeat_at,
        )

    def get_icp(self, *, tenant_id: str, icp_id: str | None) -> ICPToolRecord | None:
        started = time.perf_counter()
        stmt = select(ICPDefinition).where(ICPDefinition.tenant_id == tenant_id)
        if icp_id:
            stmt = stmt.where(ICPDefinition.id == icp_id)
        row = self._session.execute(stmt.order_by(ICPDefinition.created_at.desc())).scalars().first()
        self._emit(service="repositories.prospect.get_icp", status="ok", started=started, tenant_id=tenant_id)
        if row is None:
            return None
        return ICPToolRecord(
            icp_id=row.id,
            name=row.name,
            description=row.description,
            criteria=row.criteria,
        )

    def list_accounts_for_research(self, *, tenant_id: str, limit: int) -> list[AccountToolRecord]:
        started = time.perf_counter()
        rows = self._session.execute(
            select(Account)
            .where(Account.tenant_id == tenant_id)
            .order_by(Account.created_at.desc())
            .limit(limit)
        ).scalars().all()
        self._emit(service="repositories.prospect.list_accounts", status="ok", started=started, tenant_id=tenant_id)
        return [
            AccountToolRecord(
                account_id=row.id,
                name=row.name,
                domain=row.domain,
                lifecycle_stage=row.lifecycle_stage,
                firmographics=row.firmographics,
            )
            for row in rows
        ]

    def list_contacts_by_account_ids(self, *, tenant_id: str, account_ids: list[str]) -> list[ContactToolRecord]:
        if not account_ids:
            return []
        started = time.perf_counter()
        rows = self._session.execute(
            select(Contact)
            .where(Contact.tenant_id == tenant_id, Contact.account_id.in_(account_ids))
            .order_by(Contact.created_at.desc())
        ).scalars().all()
        self._emit(service="repositories.prospect.list_contacts", status="ok", started=started, tenant_id=tenant_id)
        return [
            ContactToolRecord(
                contact_id=row.id,
                account_id=row.account_id,
                full_name=row.full_name,
                email=row.email,
                title=row.title,
                custom_fields=row.custom_fields,
            )
            for row in rows
        ]

    def list_signals_by_account_ids(self, *, tenant_id: str, account_ids: list[str]) -> list[SignalToolRecord]:
        if not account_ids:
            return []
        started = time.perf_counter()
        rows = self._session.execute(
            select(Signal)
            .where(Signal.tenant_id == tenant_id, Signal.account_id.in_(account_ids))
            .order_by(Signal.observed_at.desc())
        ).scalars().all()
        self._emit(service="repositories.prospect.list_signals", status="ok", started=started, tenant_id=tenant_id)
        return [
            SignalToolRecord(
                signal_id=row.id,
                account_id=row.account_id,
                signal_type=row.signal_type,
                strength=float(row.strength) if row.strength is not None else None,
                source=row.source,
                payload=row.payload,
                observed_at=row.observed_at,
            )
            for row in rows
        ]

    def get_workflow_run(self, *, tenant_id: str, workflow_run_id: str) -> WorkflowRunToolRecord | None:
        started = time.perf_counter()
        row = self._session.execute(
            select(WorkflowRun).where(WorkflowRun.tenant_id == tenant_id, WorkflowRun.id == workflow_run_id)
        ).scalar_one_or_none()
        self._emit(service="repositories.prospect.get_workflow_run", status="ok", started=started, tenant_id=tenant_id, workflow_id=workflow_run_id)
        return self._workflow_run_record(row) if row else None

    def get_workflow_run_by_idempotency(self, *, tenant_id: str, idempotency_key: str) -> WorkflowRunToolRecord | None:
        started = time.perf_counter()
        row = self._session.execute(
            select(WorkflowRun).where(
                WorkflowRun.tenant_id == tenant_id,
                WorkflowRun.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none()
        self._emit(
            service="repositories.prospect.get_workflow_run_by_idempotency",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=row.id if row else None,
        )
        return self._workflow_run_record(row) if row else None

    def create_workflow_run(self, command: WorkflowStart) -> WorkflowRunToolRecord:
        started = time.perf_counter()
        row = WorkflowRun(
            tenant_id=command.tenant_id,
            workflow_type=command.workflow_type,
            status=WorkflowStatus.queued.value,
            icp_id=command.icp_id,
            account_id=command.account_id,
            idempotency_key=command.idempotency_key,
            input=command.input.model_dump(),
            output={},
        )
        self._session.add(row)
        self._session.flush()
        self._emit(
            service="repositories.prospect.create_workflow_run",
            status="ok",
            started=started,
            tenant_id=command.tenant_id,
            workflow_id=row.id,
        )
        return self._workflow_run_record(row)

    def update_workflow_run_status(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        status: str,
        output: dict | None = None,
        heartbeat: bool = False,
    ) -> WorkflowRunToolRecord:
        started = time.perf_counter()
        row = self._session.execute(
            select(WorkflowRun).where(WorkflowRun.tenant_id == tenant_id, WorkflowRun.id == workflow_run_id)
        ).scalar_one()
        row.status = status
        if output is not None:
            row.output = output
        if heartbeat:
            row.last_heartbeat_at = datetime.now(tz=UTC)
        self._session.flush()
        self._emit(
            service="repositories.prospect.update_workflow_run_status",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=workflow_run_id,
        )
        return self._workflow_run_record(row)

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
        started = time.perf_counter()
        stored_input = {**input_payload}
        stored_output = {**output_payload}
        if trace_id is not None:
            stored_input.setdefault("trace_id", trace_id)
            stored_output.setdefault("trace_id", trace_id)
        if correlation_id is not None:
            stored_input.setdefault("correlation_id", correlation_id)
            stored_output.setdefault("correlation_id", correlation_id)
        row = WorkflowStep(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            step_name=step_name,
            status=status,
            input=stored_input,
            output=stored_output,
            error_message=error_message,
        )
        self._session.add(row)
        self._session.flush()
        self._emit(
            service="repositories.prospect.record_workflow_step",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=workflow_run_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
        )
        return WorkflowStepRecord(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            workflow_step_id=row.id,
            step_name=row.step_name,
            status=JobStatus(row.status),
            trace_id=row.input.get("trace_id") or trace_id,
            correlation_id=row.input.get("correlation_id") or correlation_id,
            input=row.input,
            output=row.output,
            error_message=row.error_message,
        )

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
        started = time.perf_counter()
        stored_input = {**input_payload}
        stored_output = {**output_payload}
        if trace_id is not None:
            stored_input.setdefault("trace_id", trace_id)
            stored_output.setdefault("trace_id", trace_id)
        if correlation_id is not None:
            stored_input.setdefault("correlation_id", correlation_id)
            stored_output.setdefault("correlation_id", correlation_id)
        row = ToolCall(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            workflow_step_id=workflow_step_id,
            tool_name=tool_name,
            status=status,
            input=stored_input,
            output=stored_output,
            error_message=error_message,
        )
        self._session.add(row)
        self._session.flush()
        self._emit(
            service="repositories.prospect.record_tool_call",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=workflow_run_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
        )
        return ToolCallRecord(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            tool_call_id=row.id,
            tool_name=row.tool_name,
            status=JobStatus(row.status),
            trace_id=row.input.get("trace_id") or trace_id,
            correlation_id=row.input.get("correlation_id") or correlation_id,
            input=row.input,
            output=row.output,
            error_message=row.error_message,
        )

    def create_approval_checkpoint(
        self,
        *,
        tenant_id: str,
        workflow_run_id: str,
        workflow_step_id: str | None,
        reason: str,
    ) -> ApprovalCheckpoint:
        started = time.perf_counter()
        row = ApprovalRequest(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            workflow_step_id=workflow_step_id,
            status=ApprovalStatus.pending.value,
            reason=reason,
            decision_payload={},
        )
        self._session.add(row)
        self._session.flush()
        self._emit(
            service="repositories.prospect.create_approval_checkpoint",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=workflow_run_id,
        )
        return ApprovalCheckpoint(
            approval_request_id=row.id,
            status=ApprovalStatus.pending,
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            workflow_step_id=workflow_step_id,
            reason=row.reason,
        )

    def get_approval_checkpoint(
        self,
        *,
        tenant_id: str,
        approval_request_id: str,
    ) -> ApprovalCheckpoint | None:
        started = time.perf_counter()
        row = self._session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.id == approval_request_id,
            )
        ).scalar_one_or_none()
        self._emit(
            service="repositories.prospect.get_approval_checkpoint",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=row.workflow_run_id if row else None,
        )
        if row is None:
            return None
        return ApprovalCheckpoint(
            approval_request_id=row.id,
            status=ApprovalStatus(row.status),
            tenant_id=row.tenant_id,
            workflow_run_id=row.workflow_run_id,
            workflow_step_id=row.workflow_step_id,
            reviewer_user_id=row.reviewer_user_id,
            reviewed_at=row.reviewed_at,
            reason=row.reason,
        )

    def update_approval_checkpoint(
        self,
        *,
        tenant_id: str,
        approval_request_id: str,
        status: str,
        reviewer_user_id: str | None = None,
        reason: str | None = None,
    ) -> ApprovalCheckpoint:
        started = time.perf_counter()
        row = self._session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.id == approval_request_id,
            )
        ).scalar_one()
        row.status = status
        if reviewer_user_id is not None:
            row.reviewer_user_id = reviewer_user_id
        if reason is not None:
            row.reason = reason
        row.reviewed_at = datetime.now(tz=UTC)
        self._session.flush()
        self._emit(
            service="repositories.prospect.update_approval_checkpoint",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=row.workflow_run_id,
        )
        return ApprovalCheckpoint(
            approval_request_id=row.id,
            status=ApprovalStatus(row.status),
            tenant_id=row.tenant_id,
            workflow_run_id=row.workflow_run_id,
            workflow_step_id=row.workflow_step_id,
            reviewer_user_id=row.reviewer_user_id,
            reviewed_at=row.reviewed_at,
            reason=row.reason,
        )

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
        started = time.perf_counter()
        row = ValueHypothesis(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            account_id=account_id,
            contact_id=contact_id,
            generated_by_agent=generated_by_agent,
            generated_at=datetime.now(tz=UTC),
            confidence_score=confidence_score,
            title=title,
            hypothesis=hypothesis,
            metadata_=metadata,
        )
        self._session.add(row)
        self._session.flush()
        self._emit(
            service="repositories.prospect.persist_hypothesis",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=workflow_run_id,
        )
        return row.id

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
        started = time.perf_counter()
        row = OutreachDraft(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            account_id=account_id,
            contact_id=contact_id,
            generated_by_agent=generated_by_agent,
            generated_at=datetime.now(tz=UTC),
            confidence_score=metadata.get("confidence_score"),
            subject=subject,
            body=body,
            status=status,
            metadata_=metadata,
        )
        self._session.add(row)
        self._session.flush()
        self._emit(
            service="repositories.prospect.persist_outreach_draft",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=workflow_run_id,
        )
        return row.id

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
        started = time.perf_counter()
        row = LLMUsageRecord(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            model=model,
            token_input=token_input,
            token_output=token_output,
            estimated_cost=estimated_cost,
            latency_ms=latency_ms,
        )
        self._session.add(row)
        self._session.flush()
        self._emit(
            service="repositories.prospect.record_llm_usage",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=workflow_run_id,
        )
        return row.id

    def count_value_hypotheses(self, *, tenant_id: str, workflow_run_id: str) -> int:
        started = time.perf_counter()
        count = self._session.execute(
            select(func.count(ValueHypothesis.id)).where(
                ValueHypothesis.tenant_id == tenant_id,
                ValueHypothesis.workflow_run_id == workflow_run_id,
            )
        ).scalar_one()
        self._emit(
            service="repositories.prospect.count_value_hypotheses",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=workflow_run_id,
        )
        return int(count or 0)

    def count_outreach_drafts(self, *, tenant_id: str, workflow_run_id: str) -> int:
        started = time.perf_counter()
        count = self._session.execute(
            select(func.count(OutreachDraft.id)).where(
                OutreachDraft.tenant_id == tenant_id,
                OutreachDraft.workflow_run_id == workflow_run_id,
            )
        ).scalar_one()
        self._emit(
            service="repositories.prospect.count_outreach_drafts",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=workflow_run_id,
        )
        return int(count or 0)

    def count_workflow_steps(self, *, tenant_id: str, workflow_run_id: str) -> int:
        started = time.perf_counter()
        count = self._session.execute(
            select(func.count(WorkflowStep.id)).where(
                WorkflowStep.tenant_id == tenant_id,
                WorkflowStep.workflow_run_id == workflow_run_id,
            )
        ).scalar_one()
        self._emit(
            service="repositories.prospect.count_workflow_steps",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=workflow_run_id,
        )
        return int(count or 0)

    def count_tool_calls(self, *, tenant_id: str, workflow_run_id: str) -> int:
        started = time.perf_counter()
        count = self._session.execute(
            select(func.count(ToolCall.id)).where(
                ToolCall.tenant_id == tenant_id,
                ToolCall.workflow_run_id == workflow_run_id,
            )
        ).scalar_one()
        self._emit(
            service="repositories.prospect.count_tool_calls",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=workflow_run_id,
        )
        return int(count or 0)

    def count_llm_usage(self, *, tenant_id: str, workflow_run_id: str) -> tuple[float, int]:
        started = time.perf_counter()
        rows = self._session.execute(
            select(LLMUsageRecord.estimated_cost, LLMUsageRecord.latency_ms).where(
                LLMUsageRecord.tenant_id == tenant_id,
                LLMUsageRecord.workflow_run_id == workflow_run_id,
            )
        ).all()
        total_cost = 0.0
        total_latency = 0
        for cost, latency in rows:
            total_cost += float(cost or 0)
            total_latency += int(latency or 0)
        self._emit(
            service="repositories.prospect.count_llm_usage",
            status="ok",
            started=started,
            tenant_id=tenant_id,
            workflow_id=workflow_run_id,
        )
        return round(total_cost, 6), total_latency

    def list_workflow_runs(self, *, tenant_id: str, limit: int = 50, offset: int = 0) -> list[WorkflowRunSummary]:
        started = time.perf_counter()
        rows = (
            self._session.execute(
                select(WorkflowRun)
                .where(WorkflowRun.tenant_id == tenant_id)
                .order_by(WorkflowRun.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        self._emit(service="repositories.prospect.list_workflow_runs", status="ok", started=started, tenant_id=tenant_id)
        results: list[WorkflowRunSummary] = []
        for row in rows:
            created_at = row.created_at
            updated_at = row.updated_at
            duration = 0
            try:
                if created_at and updated_at:
                    duration = int((updated_at - created_at).total_seconds() * 1000)
            except Exception:
                duration = 0
            trace_id = None
            try:
                out = row.output or {}
                if isinstance(out, dict):
                    trace_id = out.get("trace_id")
                    traces = out.get("traces")
                    if not trace_id and isinstance(traces, list) and traces:
                        first = traces[0]
                        if isinstance(first, dict):
                            trace_id = first.get("trace_id")
            except Exception:
                trace_id = None
            results.append(
                WorkflowRunSummary(
                    tenant_id=row.tenant_id,
                    workflow_run_id=row.id,
                    status=WorkflowStatus(row.status),
                    workflow_type=row.workflow_type,
                    created_at=created_at,
                    updated_at=updated_at,
                    duration_ms=duration,
                    trace_id=trace_id,
                )
            )
        return results

    def get_workflow_run_summary(self, *, tenant_id: str, workflow_run_id: str) -> WorkflowRunSummary | None:
        started = time.perf_counter()
        row = self._session.execute(
            select(WorkflowRun).where(WorkflowRun.tenant_id == tenant_id, WorkflowRun.id == workflow_run_id)
        ).scalar_one_or_none()
        self._emit(service="repositories.prospect.get_workflow_run_summary", status="ok", started=started, tenant_id=tenant_id)
        if row is None:
            return None
        created_at = row.created_at
        updated_at = row.updated_at
        duration = 0
        try:
            if created_at and updated_at:
                duration = int((updated_at - created_at).total_seconds() * 1000)
        except Exception:
            duration = 0
        trace_id = None
        try:
            out = row.output or {}
            if isinstance(out, dict):
                trace_id = out.get("trace_id")
                traces = out.get("traces")
                if not trace_id and isinstance(traces, list) and traces:
                    first = traces[0]
                    if isinstance(first, dict):
                        trace_id = first.get("trace_id")
        except Exception:
            trace_id = None
        return WorkflowRunSummary(
            tenant_id=row.tenant_id,
            workflow_run_id=row.id,
            status=WorkflowStatus(row.status),
            workflow_type=row.workflow_type,
            created_at=created_at,
            updated_at=updated_at,
            duration_ms=duration,
            trace_id=trace_id,
        )

    def list_workflow_steps(self, *, tenant_id: str, workflow_run_id: str) -> list[WorkflowStepRecord]:
        started = time.perf_counter()
        rows = (
            self._session.execute(
                select(WorkflowStep)
                .where(WorkflowStep.tenant_id == tenant_id, WorkflowStep.workflow_run_id == workflow_run_id)
                .order_by(WorkflowStep.created_at.asc())
            )
            .scalars()
            .all()
        )
        self._emit(service="repositories.prospect.list_workflow_steps", status="ok", started=started, tenant_id=tenant_id)
        results: list[WorkflowStepRecord] = []
        for row in rows:
            results.append(
                WorkflowStepRecord(
                    tenant_id=row.tenant_id,
                    workflow_run_id=row.workflow_run_id,
                    workflow_step_id=row.id,
                    step_name=row.step_name,
                    status=JobStatus(row.status),
                    trace_id=row.input.get("trace_id") if isinstance(row.input, dict) else None,
                    correlation_id=row.input.get("correlation_id") if isinstance(row.input, dict) else None,
                    input=row.input,
                    output=row.output,
                    error_message=row.error_message,
                )
            )
        return results

    def list_tool_calls(self, *, tenant_id: str, workflow_run_id: str) -> list[ToolCallRecord]:
        started = time.perf_counter()
        rows = (
            self._session.execute(
                select(ToolCall)
                .where(ToolCall.tenant_id == tenant_id, ToolCall.workflow_run_id == workflow_run_id)
                .order_by(ToolCall.created_at.asc())
            )
            .scalars()
            .all()
        )
        self._emit(service="repositories.prospect.list_tool_calls", status="ok", started=started, tenant_id=tenant_id)
        results: list[ToolCallRecord] = []
        for row in rows:
            results.append(
                ToolCallRecord(
                    tenant_id=row.tenant_id,
                    workflow_run_id=row.workflow_run_id,
                    tool_call_id=row.id,
                    tool_name=row.tool_name,
                    status=JobStatus(row.status),
                    trace_id=row.input.get("trace_id") if isinstance(row.input, dict) else None,
                    correlation_id=row.input.get("correlation_id") if isinstance(row.input, dict) else None,
                    input=row.input,
                    output=row.output,
                    error_message=row.error_message,
                )
            )
        return results
