from app.agents.base import AgentExecutionContext, execute_with_retry
from app.agents.costing import estimate_usage
from app.agents.llm import AgentLLM, LLMToolSpec
from app.agents.runtime import run_tool_planned_agent
from app.agents.prompt_loader import load_system_prompt
from app.agents.tools.interfaces import ProspectAgentTools
from app.contracts.agents import AgentEstimate, AgentRetryPolicy, OutreachDraftProposal, OutreachInput, OutreachOutput
from app.contracts.common import ApprovalStatus, JobStatus, OutreachDraftStatus


class OutreachAgent:
    name = "OutreachAgent"
    model = "gpt-4.1"
    retry_policy = AgentRetryPolicy(max_attempts=2, backoff_ms=50, fallback_enabled=True)
    system_prompt = load_system_prompt("outreach_system.txt")

    def __init__(self, tools: ProspectAgentTools, llm: AgentLLM) -> None:
        self._tools = tools
        self._llm = llm

    def run(
        self,
        payload: OutreachInput,
        context: AgentExecutionContext | None = None,
    ) -> OutreachOutput:
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
                        description="Load contacts for the hypothesis account identifiers to personalize outreach.",
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
                    )
                ],
                tool_handlers={
                    "get_contacts": lambda arguments: [
                        item.model_dump(mode="json")
                        for item in self._tools.get_contacts(
                            tenant_id=payload.tenant_id,
                            account_ids=list(arguments.get("account_ids", [item.account_id for item in payload.hypotheses])),
                        )
                    ]
                },
            )
            return plan.payload, plan.reasoning_summary, plan.tool_invocations

        def _fallback(error: Exception) -> tuple[dict, str, list[str]]:
            return {"drafts": []}, f"LLM agent failed ({error}).", ["fallback"]

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
        return OutreachOutput(
            drafts=[OutreachDraftProposal.model_validate(item) for item in result_payload["drafts"]],
            estimate=estimate,
            trace=trace,
        )

