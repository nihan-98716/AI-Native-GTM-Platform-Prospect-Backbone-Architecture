from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

from openai import OpenAI

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class LLMToolSpec:
    name: str
    description: str
    parameters: dict


@dataclass(frozen=True)
class LLMToolCall:
    name: str
    arguments: dict
    call_id: str | None = None


@dataclass(frozen=True)
class LLMCompletion:
    content: str | None = None
    tool_calls: list[LLMToolCall] = field(default_factory=list)


class AgentLLM(Protocol):
    def complete(self, *, model: str, messages: list[dict], tools: list[LLMToolSpec]) -> LLMCompletion:
        ...


class OpenAIChatLLM:
    def __init__(self, *, api_key: str | None = None, base_url: str | None = None) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "OpenAIChatLLM":
        resolved = settings or get_settings()
        api_key = resolved.llm_api_key or None
        if not api_key:
            raise RuntimeError("LLM API key is not configured.")
        return cls(api_key=api_key, base_url=resolved.llm_base_url or None)

    def complete(self, *, model: str, messages: list[dict], tools: list[LLMToolSpec]) -> LLMCompletion:
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in tools
            ],
            tool_choice="auto",
            temperature=0,
        )
        message = response.choices[0].message
        tool_calls: list[LLMToolCall] = []
        for call in message.tool_calls or []:
            tool_calls.append(
                LLMToolCall(
                    name=call.function.name,
                    arguments=json.loads(call.function.arguments or "{}"),
                    call_id=call.id,
                )
            )
        return LLMCompletion(content=message.content, tool_calls=tool_calls)


class ScriptedLLM:
    def __init__(self, completions: Iterable[LLMCompletion]) -> None:
        self._completions = list(completions)
        self._cursor = 0

    def complete(self, *, model: str, messages: list[dict], tools: list[LLMToolSpec]) -> LLMCompletion:
        if self._cursor >= len(self._completions):
            raise RuntimeError("ScriptedLLM ran out of scripted completions.")
        completion = self._completions[self._cursor]
        self._cursor += 1
        return completion

