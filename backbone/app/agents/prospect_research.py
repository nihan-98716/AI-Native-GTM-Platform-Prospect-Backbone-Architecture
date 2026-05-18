from app.agents.base import AgentExecutionContext, execute_with_retry
from app.agents.costing import estimate_usage
from app.agents.llm import AgentLLM, LLMToolSpec
from app.agents.runtime import run_tool_planned_agent
from app.agents.prompt_loader import load_system_prompt
from app.agents.tools.interfaces import ProspectAgentTools
from app.contracts.agents import AgentEstimate, AgentRetryPolicy, ProspectResearchInput, ProspectResearchOutput, RankedAccount
from app.contracts.common import JobStatus


class ProspectResearchAgent:
    name = "ProspectResearchAgent"
    model = "gpt-4.1-mini"
    retry_policy = AgentRetryPolicy(max_attempts=2, backoff_ms=50, fallback_enabled=True)
    system_prompt = load_system_prompt("prospect_research_system.txt")

    def __init__(self, tools: ProspectAgentTools, llm: AgentLLM) -> None:
        self._tools = tools
        self._llm = llm

    def run(
        self,
        payload: ProspectResearchInput,
        context: AgentExecutionContext | None = None,
    ) -> ProspectResearchOutput:
        def _run(_attempt: int) -> tuple[dict, str, list[str]]:
            def fetch_icp(arguments: dict):
                icp = self._tools.get_icp(tenant_id=payload.tenant_id, icp_id=arguments.get("icp_id") or payload.icp_id)
                return icp.model_dump(mode="json") if icp else None

            def fetch_accounts(arguments: dict):
                accounts = self._tools.get_accounts(
                    tenant_id=payload.tenant_id,
                    limit=int(arguments.get("limit", payload.account_limit)),
                )
                return [item.model_dump(mode="json") for item in accounts]

            plan = run_tool_planned_agent(
                agent_name=self.name,
                model=self.model,
                system_prompt=self.system_prompt,
                payload=payload,
                context=context,
                llm=self._llm,
                tool_specs=[
                    LLMToolSpec(
                        name="get_icp",
                        description="Load the tenant ICP and any matching criteria for ranking.",
                        parameters={
                            "type": "object",
                            "properties": {"icp_id": {"type": "string"}},
                            "required": [],
                            "additionalProperties": False,
                        },
                    ),
                    LLMToolSpec(
                        name="get_accounts",
                        description="Load candidate accounts for ranking within the tenant.",
                        parameters={
                            "type": "object",
                            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}},
                            "required": ["limit"],
                            "additionalProperties": False,
                        },
                    ),
                    LLMToolSpec(
                        name="search_provider_accounts",
                        description="Ask the live integration provider to source additional accounts for the tenant.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                            },
                            "required": ["limit"],
                            "additionalProperties": False,
                        },
                    ),
                ],
                tool_handlers={
                    "get_icp": fetch_icp,
                    "get_accounts": fetch_accounts,
                    "search_provider_accounts": lambda arguments: self._tools.search_provider_accounts(
                        tenant_id=payload.tenant_id,
                        workflow_run_id=payload.workflow_run_id,
                        query=arguments.get("query") or None,
                        limit=int(arguments.get("limit", payload.account_limit)),
                        trace_id=context.trace_id if context else None,
                        correlation_id=context.correlation_id if context else None,
                    ),
                },
            )
            return plan.payload, plan.reasoning_summary, plan.tool_invocations

        def _fallback(error: Exception) -> tuple[dict, str, list[str]]:
            return {"ranked_accounts": []}, f"LLM agent failed ({error}).", ["fallback"]

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
        return ProspectResearchOutput(
            ranked_accounts=[RankedAccount.model_validate(item) for item in result_payload["ranked_accounts"]],
            estimate=estimate,
            trace=trace,
        )

