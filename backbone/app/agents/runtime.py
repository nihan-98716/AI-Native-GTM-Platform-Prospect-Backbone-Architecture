from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.agents.base import AgentExecutionContext
from app.agents.llm import AgentLLM, LLMCompletion, LLMToolCall, LLMToolSpec

TOutput = TypeVar("TOutput", bound=BaseModel)


@dataclass(frozen=True)
class AgentPlanResult:
    payload: dict
    reasoning_summary: str
    tool_invocations: list[str]


def _json_dump(value: Any) -> str:
    return json.dumps(value, default=str)


def _parse_json_document(content: str) -> dict:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError("LLM returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("LLM response must be a JSON object.")
    return parsed


def _messages_payload(payload: BaseModel | dict, context: AgentExecutionContext | None, prompt: str) -> list[dict]:
    normalized_payload = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    return [
        {
            "role": "system",
            "content": prompt
            + "\n\nUse tools when needed. Return a JSON object with keys `reasoning_summary` and `output`.",
        },
        {
            "role": "user",
            "content": _json_dump(
                {
                    "input": normalized_payload,
                    "context": {
                        "tenant_id": context.tenant_id if context else None,
                        "workflow_run_id": context.workflow_run_id if context else None,
                        "current_step": context.current_step if context else None,
                        "approval_status": context.approval_status.value if context and context.approval_status else None,
                        "prompt_name": context.prompt_name if context else None,
                        "trace_id": context.trace_id if context else None,
                        "correlation_id": context.correlation_id if context else None,
                    },
                }
            ),
        },
    ]


def run_tool_planned_agent(
    *,
    agent_name: str,
    model: str,
    system_prompt: str,
    payload: BaseModel | dict,
    context: AgentExecutionContext | None,
    llm: AgentLLM,
    tool_specs: list[LLMToolSpec],
    tool_handlers: dict[str, Callable[[dict], Any]],
    max_turns: int = 5,
) -> AgentPlanResult:
    messages = _messages_payload(payload, context, system_prompt)
    tool_invocations: list[str] = []
    for _ in range(max_turns):
        completion = llm.complete(model=model, messages=messages, tools=tool_specs)
        if completion.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": completion.content or "",
                    "tool_calls": [
                        {
                            "id": call.call_id or f"{call.name}-{index}",
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": _json_dump(call.arguments),
                            },
                        }
                        for index, call in enumerate(completion.tool_calls, start=1)
                    ],
                }
            )
            for call in completion.tool_calls:
                handler = tool_handlers.get(call.name)
                if handler is None:
                    raise RuntimeError(f"{agent_name} requested unknown tool: {call.name}")
                result = handler(call.arguments)
                tool_invocations.append(call.name)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.call_id or f"{call.name}-{len(tool_invocations)}",
                        "name": call.name,
                        "content": _json_dump(result),
                    }
                )
            continue

        if not completion.content:
            raise RuntimeError(f"{agent_name} returned no final content.")
        parsed = _parse_json_document(completion.content)
        reasoning_summary = str(parsed.get("reasoning_summary", "")).strip()
        output = parsed.get("output")
        if not reasoning_summary:
            raise RuntimeError(f"{agent_name} final response is missing reasoning_summary.")
        if not isinstance(output, dict):
            raise RuntimeError(f"{agent_name} final response is missing output.")
        return AgentPlanResult(payload=output, reasoning_summary=reasoning_summary, tool_invocations=tool_invocations)

    raise RuntimeError(f"{agent_name} exceeded {max_turns} planning turns.")

