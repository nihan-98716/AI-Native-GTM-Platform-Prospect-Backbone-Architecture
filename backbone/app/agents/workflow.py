from uuid import uuid4

import time

from langgraph.graph import END, StateGraph

from app.agents.base import AgentExecutionContext
from app.agents.contact_enrichment import ContactEnrichmentAgent
from app.agents.intent_signal import IntentSignalAgent
from app.agents.llm import AgentLLM
from app.agents.outreach import OutreachAgent
from app.agents.prospect_research import ProspectResearchAgent
from app.agents.tools.interfaces import ProspectAgentTools
from app.agents.value_hypothesis import ValueHypothesisAgent
from app.contracts.agents import (
    ContactEnrichmentInput,
    IntentSignalInput,
    OutreachInput,
    ProspectResearchInput,
    ValueHypothesisInput,
)
from app.contracts.common import ApprovalStatus, JobStatus, WorkflowEventType, WorkflowStatus
from app.contracts.events.audit import AuditEventCreate
from app.contracts.workflows.execution import ProspectWorkflowExecutionState
from app.core.tenancy import TenantContext
from app.observability.runtime import ObservabilityRuntime, get_observability_runtime


_STEP_ORDER = {
    "research": 0,
    "contact_enrichment": 1,
    "intent_signal": 2,
    "value_hypothesis": 3,
    "approval_gate": 4,
    "outreach": 5,
    "completed": 6,
}


class ProspectWorkflowEngine:
    def __init__(self, tools: ProspectAgentTools, llm: AgentLLM, observability: ObservabilityRuntime | None = None) -> None:
        self._tools = tools
        self._llm = llm
        self._obs = observability or get_observability_runtime()

    def execute(self, state: ProspectWorkflowExecutionState, *, context: TenantContext) -> ProspectWorkflowExecutionState:
        research_agent = ProspectResearchAgent(self._tools, self._llm)
        contact_agent = ContactEnrichmentAgent(self._tools, self._llm)
        intent_agent = IntentSignalAgent(self._tools, self._llm)
        hypothesis_agent = ValueHypothesisAgent(self._tools, self._llm)
        outreach_agent = OutreachAgent(self._tools, self._llm)

        def should_skip(current_step: str | None, step_name: str) -> bool:
            if current_step is None:
                return False
            return _STEP_ORDER.get(current_step, 0) > _STEP_ORDER[step_name]

        def emit_audit(
            action: WorkflowEventType,
            workflow_step_id: str | None = None,
            metadata: dict | None = None,
            trace_id: str | None = None,
            correlation_id: str | None = None,
        ) -> None:
            self._tools.add_audit_event(
                context=context,
                event=AuditEventCreate(
                    actor_user_id=context.actor_user_id,
                    action=action.value,
                    resource_type="workflow_run",
                    resource_id=state.workflow_run_id,
                    metadata={
                        **(metadata or {}),
                        "workflow_step_id": workflow_step_id,
                        "trace_id": trace_id,
                        "correlation_id": correlation_id,
                    },
                ),
            )

        def agent_context(current: ProspectWorkflowExecutionState, prompt_name: str) -> AgentExecutionContext:
            trace_id = current.traces[-1].trace_id if current.traces and current.traces[-1].trace_id else str(uuid4())
            correlation_id = current.traces[-1].correlation_id if current.traces and current.traces[-1].correlation_id else str(uuid4())
            return AgentExecutionContext(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                current_step=current.current_step or "",
                approval_status=current.approval_status,
                prompt_name=prompt_name,
                trace_id=trace_id,
                correlation_id=correlation_id,
            )

        def persist_state(updated_state: ProspectWorkflowExecutionState) -> None:
            started = time.perf_counter()
            self._tools.update_workflow_status(
                tenant_id=context.tenant_id,
                workflow_run_id=updated_state.workflow_run_id,
                status=updated_state.status.value,
                output=updated_state.model_dump(mode="json"),
                heartbeat=True,
            )
            self._obs.emit_operation(
                service="workflow.prospect.persist_state",
                status=updated_state.status.value,
                duration_ms=int((time.perf_counter() - started) * 1000),
                tenant_id=context.tenant_id,
                workflow_id=updated_state.workflow_run_id,
            )

        graph = StateGraph(dict)

        def research_node(raw_state: dict) -> dict:
            current = ProspectWorkflowExecutionState.model_validate(raw_state)
            if should_skip(current.current_step, "research") or current.ranked_accounts:
                return current.model_dump(mode="json")
            payload = ProspectResearchInput(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                icp_id=current.icp_id,
            )
            output = research_agent.run(payload, context=agent_context(current, "prospect_research_system.txt"))
            step = self._tools.add_workflow_step(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                step_name="research",
                status=JobStatus.completed.value,
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
                input_payload=payload.model_dump(mode="json"),
                output_payload=output.model_dump(mode="json"),
            )
            self._tools.add_llm_usage(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                model=research_agent.model,
                token_input=output.estimate.estimated_input_tokens,
                token_output=output.estimate.estimated_output_tokens,
                estimated_cost=output.estimate.estimated_cost_usd,
                latency_ms=output.estimate.estimated_latency_ms,
            )
            tool_call = self._tools.add_tool_call(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                workflow_step_id=step.workflow_step_id,
                tool_name=research_agent.name,
                status=output.trace.status.value,
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
                input_payload=payload.model_dump(mode="json"),
                output_payload=output.model_dump(mode="json"),
            )
            updated = current.model_copy(
                update={
                    "status": WorkflowStatus.running,
                    "current_step": "contact_enrichment",
                    "ranked_accounts": output.ranked_accounts,
                    "estimated_cost_usd": round(current.estimated_cost_usd + output.estimate.estimated_cost_usd, 6),
                    "estimated_latency_ms": current.estimated_latency_ms + output.estimate.estimated_latency_ms,
                    "traces": [*current.traces, output.trace],
                    "trace_summary": [*current.trace_summary, output.trace.reasoning_summary],
                    "evidence": current.evidence.model_copy(
                        update={
                            "step_ids": [*current.evidence.step_ids, step.workflow_step_id],
                            "tool_call_ids": [*current.evidence.tool_call_ids, tool_call.tool_call_id],
                            "trace_ids": [*current.evidence.trace_ids, output.trace.trace_id or step.workflow_step_id],
                        }
                    ),
                }
            )
            persist_state(updated)
            emit_audit(
                WorkflowEventType.workflow_started,
                step.workflow_step_id,
                {"step": "research"},
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
            )
            return updated.model_dump(mode="json")

        def contact_node(raw_state: dict) -> dict:
            current = ProspectWorkflowExecutionState.model_validate(raw_state)
            if should_skip(current.current_step, "contact_enrichment") or current.enriched_contacts:
                return current.model_dump(mode="json")
            account_ids = [item.account_id for item in current.ranked_accounts[:5]]
            payload = ContactEnrichmentInput(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                account_ids=account_ids,
            )
            output = contact_agent.run(payload, context=agent_context(current, "contact_enrichment_system.txt"))
            step = self._tools.add_workflow_step(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                step_name="contact_enrichment",
                status=JobStatus.completed.value,
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
                input_payload=payload.model_dump(mode="json"),
                output_payload=output.model_dump(mode="json"),
            )
            self._tools.add_llm_usage(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                model=contact_agent.model,
                token_input=output.estimate.estimated_input_tokens,
                token_output=output.estimate.estimated_output_tokens,
                estimated_cost=output.estimate.estimated_cost_usd,
                latency_ms=output.estimate.estimated_latency_ms,
            )
            tool_call = self._tools.add_tool_call(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                workflow_step_id=step.workflow_step_id,
                tool_name=contact_agent.name,
                status=output.trace.status.value,
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
                input_payload=payload.model_dump(mode="json"),
                output_payload=output.model_dump(mode="json"),
            )
            updated = current.model_copy(
                update={
                    "current_step": "intent_signal",
                    "enriched_contacts": output.enriched_contacts,
                    "estimated_cost_usd": round(current.estimated_cost_usd + output.estimate.estimated_cost_usd, 6),
                    "estimated_latency_ms": current.estimated_latency_ms + output.estimate.estimated_latency_ms,
                    "traces": [*current.traces, output.trace],
                    "trace_summary": [*current.trace_summary, output.trace.reasoning_summary],
                    "evidence": current.evidence.model_copy(
                        update={
                            "step_ids": [*current.evidence.step_ids, step.workflow_step_id],
                            "tool_call_ids": [*current.evidence.tool_call_ids, tool_call.tool_call_id],
                            "trace_ids": [*current.evidence.trace_ids, output.trace.trace_id or step.workflow_step_id],
                        }
                    ),
                }
            )
            persist_state(updated)
            emit_audit(
                WorkflowEventType.workflow_paused,
                step.workflow_step_id,
                {"step": "contact_enrichment"},
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
            )
            return updated.model_dump(mode="json")

        def signal_node(raw_state: dict) -> dict:
            current = ProspectWorkflowExecutionState.model_validate(raw_state)
            if should_skip(current.current_step, "intent_signal") or current.intent_assessments:
                return current.model_dump(mode="json")
            account_ids = [item.account_id for item in current.ranked_accounts[:5]]
            payload = IntentSignalInput(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                account_ids=account_ids,
            )
            output = intent_agent.run(payload, context=agent_context(current, "intent_signal_system.txt"))
            step = self._tools.add_workflow_step(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                step_name="intent_signal",
                status=JobStatus.completed.value,
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
                input_payload=payload.model_dump(mode="json"),
                output_payload=output.model_dump(mode="json"),
            )
            self._tools.add_llm_usage(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                model=intent_agent.model,
                token_input=output.estimate.estimated_input_tokens,
                token_output=output.estimate.estimated_output_tokens,
                estimated_cost=output.estimate.estimated_cost_usd,
                latency_ms=output.estimate.estimated_latency_ms,
            )
            tool_call = self._tools.add_tool_call(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                workflow_step_id=step.workflow_step_id,
                tool_name=intent_agent.name,
                status=output.trace.status.value,
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
                input_payload=payload.model_dump(mode="json"),
                output_payload=output.model_dump(mode="json"),
            )
            updated = current.model_copy(
                update={
                    "current_step": "value_hypothesis",
                    "intent_assessments": output.assessments,
                    "estimated_cost_usd": round(current.estimated_cost_usd + output.estimate.estimated_cost_usd, 6),
                    "estimated_latency_ms": current.estimated_latency_ms + output.estimate.estimated_latency_ms,
                    "traces": [*current.traces, output.trace],
                    "trace_summary": [*current.trace_summary, output.trace.reasoning_summary],
                    "evidence": current.evidence.model_copy(
                        update={
                            "step_ids": [*current.evidence.step_ids, step.workflow_step_id],
                            "tool_call_ids": [*current.evidence.tool_call_ids, tool_call.tool_call_id],
                            "trace_ids": [*current.evidence.trace_ids, output.trace.trace_id or step.workflow_step_id],
                        }
                    ),
                }
            )
            persist_state(updated)
            emit_audit(
                WorkflowEventType.workflow_paused,
                step.workflow_step_id,
                {"step": "intent_signal"},
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
            )
            return updated.model_dump(mode="json")

        def hypothesis_node(raw_state: dict) -> dict:
            current = ProspectWorkflowExecutionState.model_validate(raw_state)
            if should_skip(current.current_step, "value_hypothesis") or current.hypotheses:
                return current.model_dump(mode="json")
            account_ids = [item.account_id for item in current.ranked_accounts[:5]]
            contact_ids = [item.contact_id for item in current.enriched_contacts[:10]]
            payload = ValueHypothesisInput(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                account_ids=account_ids,
                contact_ids=contact_ids,
                assessments=[item for item in current.intent_assessments],
            )
            output = hypothesis_agent.run(payload, context=agent_context(current, "value_hypothesis_system.txt"))
            step = self._tools.add_workflow_step(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                step_name="value_hypothesis",
                status=JobStatus.completed.value,
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
                input_payload=payload.model_dump(mode="json"),
                output_payload=output.model_dump(mode="json"),
            )
            hypothesis_ids = self._tools.save_hypotheses(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                drafts=output.hypotheses,
                generated_by_agent=hypothesis_agent.name,
            )
            self._tools.add_llm_usage(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                model=hypothesis_agent.model,
                token_input=output.estimate.estimated_input_tokens,
                token_output=output.estimate.estimated_output_tokens,
                estimated_cost=output.estimate.estimated_cost_usd,
                latency_ms=output.estimate.estimated_latency_ms,
            )
            tool_call = self._tools.add_tool_call(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                workflow_step_id=step.workflow_step_id,
                tool_name=hypothesis_agent.name,
                status=output.trace.status.value,
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
                input_payload=payload.model_dump(mode="json"),
                output_payload={"hypothesis_ids": hypothesis_ids, **output.model_dump(mode="json")},
            )
            updated = current.model_copy(
                update={
                    "current_step": "approval_gate",
                    "status": WorkflowStatus.waiting_for_approval,
                    "hypotheses": output.hypotheses,
                    "estimated_cost_usd": round(current.estimated_cost_usd + output.estimate.estimated_cost_usd, 6),
                    "estimated_latency_ms": current.estimated_latency_ms + output.estimate.estimated_latency_ms,
                    "traces": [*current.traces, output.trace],
                    "trace_summary": [*current.trace_summary, output.trace.reasoning_summary],
                    "evidence": current.evidence.model_copy(
                        update={
                            "step_ids": [*current.evidence.step_ids, step.workflow_step_id],
                            "tool_call_ids": [*current.evidence.tool_call_ids, tool_call.tool_call_id],
                            "trace_ids": [*current.evidence.trace_ids, output.trace.trace_id or step.workflow_step_id],
                            "notes": [*current.evidence.notes, f"hypothesis_ids={','.join(hypothesis_ids)}"],
                        }
                    ),
                }
            )
            persist_state(updated)
            emit_audit(
                WorkflowEventType.workflow_paused,
                step.workflow_step_id,
                {"step": "value_hypothesis"},
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
            )
            return updated.model_dump(mode="json")

        def approval_node(raw_state: dict) -> dict:
            current = ProspectWorkflowExecutionState.model_validate(raw_state)
            if current.approval_status == ApprovalStatus.approved:
                emit_audit(
                    WorkflowEventType.workflow_resumed,
                    current.approval_request_id,
                    {"step": "approval_gate"},
                    trace_id=current.traces[-1].trace_id if current.traces else None,
                    correlation_id=current.traces[-1].correlation_id if current.traces else None,
                )
                updated = current.model_copy(
                    update={
                        "current_step": "outreach",
                        "status": WorkflowStatus.running,
                    }
                )
                return updated.model_dump(mode="json")
            if current.approval_request_id:
                return current.model_dump(mode="json")
            checkpoint = self._tools.create_approval_checkpoint(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                workflow_step_id=current.evidence.step_ids[-1] if current.evidence.step_ids else None,
                reason="Human approval required before outreach.",
            )
            updated = current.model_copy(
                update={
                    "status": WorkflowStatus.waiting_for_approval,
                    "current_step": "approval_gate",
                    "approval_status": ApprovalStatus.pending,
                    "approval_request_id": checkpoint.approval_request_id,
                    "evidence": current.evidence.model_copy(
                        update={
                            "approval_request_ids": [*current.evidence.approval_request_ids, checkpoint.approval_request_id],
                        }
                    ),
                }
            )
            persist_state(updated)
            emit_audit(WorkflowEventType.workflow_paused, current.evidence.step_ids[-1] if current.evidence.step_ids else None, {"step": "approval_gate"})
            return updated.model_dump(mode="json")

        def approval_route(raw_state: dict) -> str:
            current = ProspectWorkflowExecutionState.model_validate(raw_state)
            if current.approval_status == ApprovalStatus.approved:
                return "outreach"
            return "end"

        def outreach_node(raw_state: dict) -> dict:
            current = ProspectWorkflowExecutionState.model_validate(raw_state)
            if should_skip(current.current_step, "outreach") or current.outreach_drafts:
                return current.model_dump(mode="json")
            payload = OutreachInput(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                hypotheses=[item for item in current.hypotheses],
                approval_status=current.approval_status or ApprovalStatus.pending,
            )
            output = outreach_agent.run(payload, context=agent_context(current, "outreach_system.txt"))
            step = self._tools.add_workflow_step(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                step_name="outreach",
                status=JobStatus.completed.value,
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
                input_payload=payload.model_dump(mode="json"),
                output_payload=output.model_dump(mode="json"),
            )
            draft_ids = self._tools.save_outreach_drafts(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                drafts=output.drafts,
                generated_by_agent=outreach_agent.name,
            )
            self._tools.add_llm_usage(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                model=outreach_agent.model,
                token_input=output.estimate.estimated_input_tokens,
                token_output=output.estimate.estimated_output_tokens,
                estimated_cost=output.estimate.estimated_cost_usd,
                latency_ms=output.estimate.estimated_latency_ms,
            )
            tool_call = self._tools.add_tool_call(
                tenant_id=current.tenant_id,
                workflow_run_id=current.workflow_run_id,
                workflow_step_id=step.workflow_step_id,
                tool_name=outreach_agent.name,
                status=output.trace.status.value,
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
                input_payload=payload.model_dump(mode="json"),
                output_payload={"draft_ids": draft_ids, **output.model_dump(mode="json")},
            )
            updated = current.model_copy(
                update={
                    "current_step": "completed",
                    "status": WorkflowStatus.succeeded,
                    "outreach_drafts": output.drafts,
                    "estimated_cost_usd": round(current.estimated_cost_usd + output.estimate.estimated_cost_usd, 6),
                    "estimated_latency_ms": current.estimated_latency_ms + output.estimate.estimated_latency_ms,
                    "traces": [*current.traces, output.trace],
                    "trace_summary": [*current.trace_summary, output.trace.reasoning_summary],
                    "evidence": current.evidence.model_copy(
                        update={
                            "step_ids": [*current.evidence.step_ids, step.workflow_step_id],
                            "tool_call_ids": [*current.evidence.tool_call_ids, tool_call.tool_call_id],
                            "trace_ids": [*current.evidence.trace_ids, output.trace.trace_id or step.workflow_step_id],
                            "notes": [*current.evidence.notes, f"draft_ids={','.join(draft_ids)}"],
                        }
                    ),
                }
            )
            persist_state(updated)
            emit_audit(
                WorkflowEventType.workflow_completed,
                step.workflow_step_id,
                {"step": "outreach"},
                trace_id=output.trace.trace_id,
                correlation_id=output.trace.correlation_id,
            )
            return updated.model_dump(mode="json")

        graph.add_node("research", research_node)
        graph.add_node("contact_enrichment", contact_node)
        graph.add_node("intent_signal", signal_node)
        graph.add_node("value_hypothesis", hypothesis_node)
        graph.add_node("approval_gate", approval_node)
        graph.add_node("outreach", outreach_node)

        graph.set_entry_point("research")
        graph.add_edge("research", "contact_enrichment")
        graph.add_edge("contact_enrichment", "intent_signal")
        graph.add_edge("intent_signal", "value_hypothesis")
        graph.add_conditional_edges("approval_gate", approval_route, {"outreach": "outreach", "end": END})
        graph.add_edge("value_hypothesis", "approval_gate")
        graph.add_edge("outreach", END)

        compiled = graph.compile()
        result = compiled.invoke(state.model_dump(mode="json"))
        return ProspectWorkflowExecutionState.model_validate(result)

