from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json

from app.agents.llm import LLMCompletion, LLMToolCall, ScriptedLLM
from app.audit.interfaces import AuditService
from app.contracts.agents import (
    AgentEstimate,
    AgentTraceEntry,
    ContactEnrichmentInput,
    ContactEnrichmentOutput,
    EnrichedContact,
    IntentAssessment,
    IntentClass,
    IntentSignalInput,
    IntentSignalOutput,
    OutreachDraftProposal,
    OutreachInput,
    OutreachOutput,
    ProspectResearchInput,
    ProspectResearchOutput,
    RankedAccount,
    ValueHypothesisDraft,
    ValueHypothesisInput,
    ValueHypothesisOutput,
)
from app.contracts.api.prospect import ResumeProspectWorkflowRequest, StartProspectWorkflowRequest
from app.contracts.common import ApprovalStatus, JobStatus, OutreachDraftStatus, WorkflowStatus
from app.contracts.tools.prospect import (
    AccountToolRecord,
    ApprovalCheckpoint,
    ContactToolRecord,
    ICPToolRecord,
    SignalToolRecord,
    ToolCallRecord,
    WorkflowRunToolRecord,
    WorkflowStepRecord,
)
from app.contracts.workflows.lifecycle import WorkflowStartInput
from app.core.tenancy import TenantContext
from app.services.prospect import ProspectWorkflowService


def _estimate() -> AgentEstimate:
    return AgentEstimate(
        model="gpt-4.1-mini",
        estimated_input_tokens=12,
        estimated_output_tokens=8,
        estimated_cost_usd=0.01,
        estimated_latency_ms=10,
    )


def _trace(name: str) -> AgentTraceEntry:
    now = datetime.now(tz=UTC)
    return AgentTraceEntry(
        agent_name=name,
        attempt=1,
        status=JobStatus.completed,
        reasoning_summary=f"{name} completed",
        tool_invocations=["tool"],
        trace_id=f"trace-{name}",
        correlation_id=f"corr-{name}",
        started_at=now,
        finished_at=now,
    )


def _tool_completion(*calls: tuple[str, dict]) -> LLMCompletion:
    return LLMCompletion(
        tool_calls=[LLMToolCall(name=name, arguments=arguments, call_id=f"{name}-{index}") for index, (name, arguments) in enumerate(calls, start=1)]
    )


def _final_completion(output: dict, reasoning_summary: str) -> LLMCompletion:
    return LLMCompletion(content=json.dumps({"reasoning_summary": reasoning_summary, "output": output}))


def build_scripted_llm() -> ScriptedLLM:
    return ScriptedLLM(
        [
            _tool_completion(("get_icp", {"icp_id": "icp-1"}), ("get_accounts", {"limit": 10})),
            _final_completion(
                {
                    "ranked_accounts": [
                        RankedAccount(account_id="account-a", rank_score=98, reasoning_summary="Best software fit").model_dump(mode="json"),
                        RankedAccount(account_id="account-b", rank_score=54, reasoning_summary="Weaker services fit").model_dump(mode="json"),
                    ]
                },
                "Ranked accounts against ICP criteria after loading ICP and account data.",
            ),
            _tool_completion(("get_contacts", {"account_ids": ["account-a", "account-b"]})),
            _final_completion(
                {
                    "enriched_contacts": [
                        EnrichedContact(
                            contact_id="contact-a",
                            completeness_score=100,
                            confidence_score=97,
                            metadata={"account_id": "account-a", "has_email": True, "has_title": True},
                        ).model_dump(mode="json"),
                        EnrichedContact(
                            contact_id="contact-b",
                            completeness_score=100,
                            confidence_score=97,
                            metadata={"account_id": "account-b", "has_email": True, "has_title": True},
                        ).model_dump(mode="json"),
                    ]
                },
                "Enriched contacts after loading tenant contacts.",
            ),
            _tool_completion(("get_signals", {"account_ids": ["account-a", "account-b"]})),
            _final_completion(
                {
                    "assessments": [
                        IntentAssessment(
                            account_id="account-a",
                            intent_class=IntentClass.high,
                            intent_strength=82,
                            evidence_summary="1 strong signal",
                            evidence_items=["job_change:news"],
                        ).model_dump(mode="json"),
                        IntentAssessment(
                            account_id="account-b",
                            intent_class=IntentClass.low,
                            intent_strength=25,
                            evidence_summary="1 weak signal",
                            evidence_items=["funding:rss"],
                        ).model_dump(mode="json"),
                    ]
                },
                "Analyzed signal evidence and classified intent.",
            ),
            _tool_completion(("get_contacts", {"account_ids": ["account-a", "account-b"]})),
            _final_completion(
                {
                    "hypotheses": [
                        ValueHypothesisDraft(
                            account_id="account-a",
                            contact_id="contact-a",
                            title="High intent opportunity",
                            hypothesis="Account account-a shows high buying intent.",
                            supporting_evidence=["job_change:news"],
                            confidence_score=82,
                        ).model_dump(mode="json"),
                        ValueHypothesisDraft(
                            account_id="account-b",
                            contact_id="contact-b",
                            title="Low intent opportunity",
                            hypothesis="Account account-b shows low buying intent.",
                            supporting_evidence=["funding:rss"],
                            confidence_score=25,
                        ).model_dump(mode="json"),
                    ]
                },
                "Generated value hypotheses from intent assessments.",
            ),
            _tool_completion(("get_contacts", {"account_ids": ["account-a", "account-b"]})),
            _final_completion(
                {
                    "drafts": [
                        OutreachDraftProposal(
                            account_id="account-a",
                            contact_id="contact-a",
                            subject="High intent opportunity: outcomes for your GTM motion",
                            body="Hi there,\n\nBased on your current signal profile, we believe: Account account-a shows high buying intent.\nEvidence: job_change:news\n\nIf useful, I can share a concise plan tailored to your ICP.\n",
                            status=OutreachDraftStatus.pending_approval,
                            review_notes="Human approval required before send.",
                        ).model_dump(mode="json"),
                        OutreachDraftProposal(
                            account_id="account-b",
                            contact_id="contact-b",
                            subject="Low intent opportunity: outcomes for your GTM motion",
                            body="Hi there,\n\nBased on your current signal profile, we believe: Account account-b shows low buying intent.\nEvidence: funding:rss\n\nIf useful, I can share a concise plan tailored to your ICP.\n",
                            status=OutreachDraftStatus.pending_approval,
                            review_notes="Human approval required before send.",
                        ).model_dump(mode="json"),
                    ]
                },
                "Created outreach drafts after human-review-aware planning.",
            ),
        ]
    )


class FakeAuditService(AuditService):
    def __init__(self) -> None:
        self.records: list[tuple[str, str, str | None]] = []

    def record(self, context: TenantContext, event):
        self.records.append((context.tenant_id, event.action, event.resource_id))
        return event

    def record_scoped(self, context: TenantContext, event):
        self.records.append((context.tenant_id, event.action, event.resource_id))
        return event


@dataclass
class FakeWorkflowRun:
    tenant_id: str
    workflow_run_id: str
    status: WorkflowStatus
    workflow_type: str
    input: dict = field(default_factory=dict)
    output: dict = field(default_factory=dict)


class FakeProspectWorkflowRepository:
    def __init__(self) -> None:
        self.icps = {
            "icp-1": ICPToolRecord(icp_id="icp-1", name="ICP One", description="Test ICP", criteria={"industry": "software"}),
        }
        self.accounts = [
            AccountToolRecord(
                account_id="account-a",
                name="Alpha",
                domain="alpha.test",
                lifecycle_stage="prospect",
                firmographics={"industry": "software"},
            ),
            AccountToolRecord(
                account_id="account-b",
                name="Beta",
                domain="beta.test",
                lifecycle_stage="prospect",
                firmographics={"industry": "services"},
            ),
        ]
        self.contacts = [
            ContactToolRecord(contact_id="contact-a", account_id="account-a", full_name="A Person", email="a@alpha.test", title="VP Sales"),
            ContactToolRecord(contact_id="contact-b", account_id="account-b", full_name="B Person", email="b@beta.test", title="VP Revenue"),
        ]
        self.signals = [
            SignalToolRecord(signal_id="signal-a", account_id="account-a", signal_type="job_change", strength=82, source="news", payload={}, observed_at=datetime.now(tz=UTC)),
            SignalToolRecord(signal_id="signal-b", account_id="account-b", signal_type="funding", strength=25, source="rss", payload={}, observed_at=datetime.now(tz=UTC)),
        ]
        self.runs: dict[str, FakeWorkflowRun] = {}
        self.steps: list[WorkflowStepRecord] = []
        self.tool_calls: list[ToolCallRecord] = []
        self.approvals: dict[str, ApprovalCheckpoint] = {}
        self.hypotheses: list[dict] = []
        self.drafts: list[dict] = []
        self.usage: list[tuple[str, float, int]] = []
        self._step_counter = 0
        self._tool_counter = 0
        self._approval_counter = 0

    def get_icp(self, *, tenant_id: str, icp_id: str | None):
        return self.icps.get(icp_id or "icp-1")

    def list_accounts_for_research(self, *, tenant_id: str, limit: int):
        return self.accounts[:limit]

    def list_contacts_by_account_ids(self, *, tenant_id: str, account_ids: list[str]):
        return [item for item in self.contacts if item.account_id in account_ids]

    def list_signals_by_account_ids(self, *, tenant_id: str, account_ids: list[str]):
        return [item for item in self.signals if item.account_id in account_ids]

    def get_workflow_run(self, *, tenant_id: str, workflow_run_id: str):
        run = self.runs.get(workflow_run_id)
        if run is None or run.tenant_id != tenant_id:
            return None
        return WorkflowRunToolRecord(
            tenant_id=run.tenant_id,
            workflow_run_id=run.workflow_run_id,
            status=run.status,
            workflow_type=run.workflow_type,
            input=run.input,
            output=run.output,
            last_heartbeat_at=None,
        )

    def get_workflow_run_by_idempotency(self, *, tenant_id: str, idempotency_key: str):
        for run in self.runs.values():
            if run.tenant_id == tenant_id and run.input.get("metadata", {}).get("idempotency_key") == idempotency_key:
                return WorkflowRunToolRecord(
                    tenant_id=run.tenant_id,
                    workflow_run_id=run.workflow_run_id,
                    status=run.status,
                    workflow_type=run.workflow_type,
                    input=run.input,
                    output=run.output,
                    last_heartbeat_at=None,
                )
        return None

    def create_workflow_run(self, command):
        run_id = f"run-{len(self.runs) + 1}"
        run = FakeWorkflowRun(
            tenant_id=command.tenant_id,
            workflow_run_id=run_id,
            status=WorkflowStatus.queued,
            workflow_type=command.workflow_type,
            input=command.input.model_dump(mode="json"),
            output={},
        )
        self.runs[run_id] = run
        return WorkflowRunToolRecord(
            tenant_id=run.tenant_id,
            workflow_run_id=run.workflow_run_id,
            status=run.status,
            workflow_type=run.workflow_type,
            input=run.input,
            output=run.output,
            last_heartbeat_at=None,
        )

    def update_workflow_run_status(self, *, tenant_id: str, workflow_run_id: str, status: str, output: dict | None = None, heartbeat: bool = False):
        run = self.runs[workflow_run_id]
        run.status = WorkflowStatus(status)
        if output is not None:
            run.output = output
        return WorkflowRunToolRecord(
            tenant_id=run.tenant_id,
            workflow_run_id=run.workflow_run_id,
            status=run.status,
            workflow_type=run.workflow_type,
            input=run.input,
            output=run.output,
            last_heartbeat_at=None,
        )

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
    ):
        self._step_counter += 1
        record = WorkflowStepRecord(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            workflow_step_id=f"step-{self._step_counter}",
            step_name=step_name,
            status=JobStatus(status),
            trace_id=trace_id,
            correlation_id=correlation_id,
            input=input_payload,
            output=output_payload,
            error_message=error_message,
        )
        self.steps.append(record)
        return record

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
    ):
        self._tool_counter += 1
        record = ToolCallRecord(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            tool_call_id=f"tool-{self._tool_counter}",
            tool_name=tool_name,
            status=JobStatus(status),
            trace_id=trace_id,
            correlation_id=correlation_id,
            input=input_payload,
            output=output_payload,
            error_message=error_message,
        )
        self.tool_calls.append(record)
        return record

    def create_approval_checkpoint(self, *, tenant_id: str, workflow_run_id: str, workflow_step_id: str | None, reason: str):
        self._approval_counter += 1
        checkpoint = ApprovalCheckpoint(
            approval_request_id=f"approval-{self._approval_counter}",
            status=ApprovalStatus.pending,
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            workflow_step_id=workflow_step_id,
            reason=reason,
        )
        self.approvals[checkpoint.approval_request_id] = checkpoint
        return checkpoint

    def get_approval_checkpoint(self, *, tenant_id: str, approval_request_id: str):
        return self.approvals.get(approval_request_id)

    def update_approval_checkpoint(self, *, tenant_id: str, approval_request_id: str, status: str, reviewer_user_id: str | None = None, reason: str | None = None):
        checkpoint = self.approvals[approval_request_id]
        checkpoint.status = ApprovalStatus(status)
        checkpoint.reviewer_user_id = reviewer_user_id
        checkpoint.reason = reason or checkpoint.reason
        return checkpoint

    def persist_hypothesis(self, *, tenant_id: str, workflow_run_id: str, account_id: str, contact_id: str | None, title: str, hypothesis: str, confidence_score: float, metadata: dict, generated_by_agent: str):
        item_id = f"hypothesis-{len(self.hypotheses) + 1}"
        self.hypotheses.append({"id": item_id, "account_id": account_id, "workflow_run_id": workflow_run_id})
        return item_id

    def persist_outreach_draft(self, *, tenant_id: str, workflow_run_id: str, account_id: str, contact_id: str | None, subject: str, body: str, status: str, metadata: dict, generated_by_agent: str):
        item_id = f"draft-{len(self.drafts) + 1}"
        self.drafts.append({"id": item_id, "account_id": account_id, "workflow_run_id": workflow_run_id, "status": status})
        return item_id

    def record_llm_usage(self, *, tenant_id: str, workflow_run_id: str, model: str, token_input: int, token_output: int, estimated_cost: float, latency_ms: int):
        self.usage.append((workflow_run_id, estimated_cost, latency_ms))
        return f"usage-{len(self.usage)}"

    def count_value_hypotheses(self, *, tenant_id: str, workflow_run_id: str) -> int:
        return sum(1 for item in self.hypotheses if item["workflow_run_id"] == workflow_run_id)

    def count_outreach_drafts(self, *, tenant_id: str, workflow_run_id: str) -> int:
        return sum(1 for item in self.drafts if item["workflow_run_id"] == workflow_run_id)

    def count_workflow_steps(self, *, tenant_id: str, workflow_run_id: str) -> int:
        return sum(1 for item in self.steps if item.workflow_run_id == workflow_run_id)

    def count_tool_calls(self, *, tenant_id: str, workflow_run_id: str) -> int:
        return sum(1 for item in self.tool_calls if item.workflow_run_id == workflow_run_id)

    def count_llm_usage(self, *, tenant_id: str, workflow_run_id: str):
        total_cost = sum(cost for run_id, cost, _ in self.usage if run_id == workflow_run_id)
        total_latency = sum(latency for run_id, _, latency in self.usage if run_id == workflow_run_id)
        return total_cost, total_latency


def build_service() -> tuple[ProspectWorkflowService, FakeProspectWorkflowRepository, FakeAuditService]:
    repo = FakeProspectWorkflowRepository()
    audit = FakeAuditService()
    service = ProspectWorkflowService(repository=repo, audit_service=audit, llm=build_scripted_llm())
    return service, repo, audit


def test_start_workflow_pauses_for_approval_and_persists_evidence():
    service, repo, audit = build_service()
    context = TenantContext(tenant_id="tenant-1", actor_user_id="user-1", roles=("seller",), permissions=("prospect:write", "prospect:read"))
    request = StartProspectWorkflowRequest(
        icp_id="icp-1",
        idempotency_key="workflow-1",
        input=WorkflowStartInput(),
        require_human_approval=True,
    )

    response = service.start_workflow(context=context, request=request)

    assert response.status == WorkflowStatus.waiting_for_approval
    assert response.approval_request_id is not None
    assert response.evidence.step_ids
    assert len(repo.steps) == 4
    assert len(repo.tool_calls) == 4
    assert len(audit.records) >= 3


def test_resume_workflow_approved_generates_outreach():
    service, repo, _ = build_service()
    context = TenantContext(tenant_id="tenant-1", actor_user_id="user-1", roles=("seller",), permissions=("prospect:write", "prospect:read"))
    start = StartProspectWorkflowRequest(icp_id="icp-1", idempotency_key="workflow-2", input=WorkflowStartInput(), require_human_approval=True)
    started = service.start_workflow(context=context, request=start)

    resumed = service.resume_workflow(
        context=context,
        request=ResumeProspectWorkflowRequest(
            workflow_run_id=started.workflow_run_id,
            approval_request_id=started.approval_request_id or "",
            decision=ApprovalStatus.approved,
            reason="approved",
        ),
    )

    assert resumed.status == WorkflowStatus.succeeded
    assert resumed.approval_status == ApprovalStatus.approved
    assert repo.count_outreach_drafts(tenant_id="tenant-1", workflow_run_id=started.workflow_run_id) == 2
    assert repo.runs[started.workflow_run_id].status == WorkflowStatus.succeeded


def test_resume_workflow_rejected_cancels_run():
    service, repo, _ = build_service()
    context = TenantContext(tenant_id="tenant-1", actor_user_id="user-1", roles=("seller",), permissions=("prospect:write", "prospect:read"))
    start = StartProspectWorkflowRequest(icp_id="icp-1", idempotency_key="workflow-3", input=WorkflowStartInput(), require_human_approval=True)
    started = service.start_workflow(context=context, request=start)

    resumed = service.resume_workflow(
        context=context,
        request=ResumeProspectWorkflowRequest(
            workflow_run_id=started.workflow_run_id,
            approval_request_id=started.approval_request_id or "",
            decision=ApprovalStatus.rejected,
            reason="reject",
        ),
    )

    assert resumed.status == WorkflowStatus.cancelled
    assert resumed.approval_status == ApprovalStatus.rejected
    assert repo.count_outreach_drafts(tenant_id="tenant-1", workflow_run_id=started.workflow_run_id) == 0

