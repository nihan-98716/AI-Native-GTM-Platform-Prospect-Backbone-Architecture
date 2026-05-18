from app.agents.base import AgentExecutionContext, execute_with_retry
from app.agents.costing import estimate_usage
from app.agents.llm import AgentLLM, LLMToolSpec
from app.agents.runtime import run_tool_planned_agent
from app.agents.prompt_loader import load_system_prompt
from app.agents.tools.interfaces import ProspectAgentTools
from app.contracts.agents import AgentEstimate, AgentRetryPolicy, ContactEnrichmentInput, ContactEnrichmentOutput, EnrichedContact
from app.contracts.common import JobStatus


class ContactEnrichmentAgent:
    name = "ContactEnrichmentAgent"
    model = "gpt-4.1-mini"
    retry_policy = AgentRetryPolicy(max_attempts=2, backoff_ms=50, fallback_enabled=True)
    system_prompt = load_system_prompt("contact_enrichment_system.txt")

    def __init__(self, tools: ProspectAgentTools, llm: AgentLLM) -> None:
        self._tools = tools
        self._llm = llm

    def run(
        self,
        payload: ContactEnrichmentInput,
        context: AgentExecutionContext | None = None,
    ) -> ContactEnrichmentOutput:
        def _run(_attempt: int) -> tuple[dict, str, list[str]]:
            plan = run_tool_planned_agent(
                agent_name=self.name,
                model=self.model,
                system_prompt=self.system_prompt,
                payload=payload,
                context=context,
                llm=self._llm,
                tool_specs=[
                    LLMToolSpec(
                        name="get_contacts",
                        description="Load contacts for the supplied account identifiers.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "account_ids": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "minItems": 1,
                                }
                            },
                            "required": ["account_ids"],
                            "additionalProperties": False,
                        },
                    ),
                    LLMToolSpec(
                        name="enrich_provider_contacts",
                        description="Ask the live integration provider to enrich contacts for the supplied account identifiers.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "account_ids": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "minItems": 1,
                                }
                            },
                            "required": ["account_ids"],
                            "additionalProperties": False,
                        },
                    ),
                ],
                tool_handlers={
                    "get_contacts": lambda arguments: [
                        item.model_dump(mode="json")
                        for item in self._tools.get_contacts(
                            tenant_id=payload.tenant_id,
                            account_ids=list(arguments.get("account_ids", payload.account_ids)),
                        )
                    ],
                    "enrich_provider_contacts": lambda arguments: self._tools.enrich_provider_contacts(
                        tenant_id=payload.tenant_id,
                        workflow_run_id=payload.workflow_run_id,
                        account_ids=list(arguments.get("account_ids", payload.account_ids)),
                        trace_id=context.trace_id if context else None,
                        correlation_id=context.correlation_id if context else None,
                    ),
                },
            )
            return plan.payload, plan.reasoning_summary, plan.tool_invocations

        def _fallback(error: Exception) -> tuple[dict, str, list[str]]:
            return {"enriched_contacts": []}, f"LLM agent failed ({error}).", ["fallback"]

        result_payload, trace = execute_with_retry(
            agent_name=self.name,
            retry_policy=self.retry_policy,
            run=_run,
            fallback=_fallback,
            context=context,
        )
        estimate = (
            estimate_usage(model=self.model, input_payload=payload.model_dump(), output_payload=result_payload)
            if trace.status == JobStatus.completed
            else AgentEstimate(model="llm-unavailable", estimated_input_tokens=0, estimated_output_tokens=0, estimated_cost_usd=0, estimated_latency_ms=0)
        )
        return ContactEnrichmentOutput(
            enriched_contacts=[EnrichedContact.model_validate(item) for item in result_payload["enriched_contacts"]],
            estimate=estimate,
            trace=trace,
        )

