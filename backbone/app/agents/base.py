from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import time
from uuid import uuid4

from app.contracts.common import ApprovalStatus
from app.contracts.agents import AgentRetryPolicy, AgentTraceEntry
from app.contracts.common import JobStatus


@dataclass(frozen=True)
class AgentExecutionContext:
    tenant_id: str
    workflow_run_id: str
    current_step: str
    approval_status: ApprovalStatus | None = None
    prompt_name: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None


def execute_with_retry(
    *,
    agent_name: str,
    retry_policy: AgentRetryPolicy,
    run: Callable[[int], tuple[dict, str, list[str]]],
    fallback: Callable[[Exception], tuple[dict, str, list[str]]],
    context: AgentExecutionContext | None = None,
) -> tuple[dict, AgentTraceEntry]:
    last_error: Exception | None = None
    trace_id = context.trace_id if context and context.trace_id else str(uuid4())
    correlation_id = context.correlation_id if context and context.correlation_id else str(uuid4())
    for attempt in range(1, retry_policy.max_attempts + 1):
        started = datetime.now(tz=UTC)
        try:
            payload, reasoning_summary, tool_invocations = run(attempt)
            finished = datetime.now(tz=UTC)
            return (
                payload,
                AgentTraceEntry(
                    agent_name=agent_name,
                    attempt=attempt,
                    status=JobStatus.completed,
                    reasoning_summary=reasoning_summary,
                    tool_invocations=tool_invocations,
                    tenant_id=context.tenant_id if context else None,
                    workflow_run_id=context.workflow_run_id if context else None,
                    current_step=context.current_step if context else None,
                    approval_status=context.approval_status if context else None,
                    prompt_name=context.prompt_name if context else None,
                    trace_id=trace_id,
                    correlation_id=correlation_id,
                    started_at=started,
                    finished_at=finished,
                ),
            )
        except Exception as exc:  # noqa: PERF203 - retry path
            last_error = exc
            if attempt < retry_policy.max_attempts:
                if retry_policy.backoff_ms > 0:
                    time.sleep(retry_policy.backoff_ms / 1000)
                continue
            break

    started = datetime.now(tz=UTC)
    if not retry_policy.fallback_enabled or last_error is None:
        raise RuntimeError(f"{agent_name} failed without fallback") from last_error
    payload, reasoning_summary, tool_invocations = fallback(last_error)
    finished = datetime.now(tz=UTC)
    return (
        payload,
        AgentTraceEntry(
            agent_name=agent_name,
            attempt=retry_policy.max_attempts,
            status=JobStatus.failed,
            reasoning_summary=reasoning_summary,
            tool_invocations=tool_invocations,
            tenant_id=context.tenant_id if context else None,
            workflow_run_id=context.workflow_run_id if context else None,
            current_step=context.current_step if context else None,
            approval_status=context.approval_status if context else None,
            prompt_name=context.prompt_name if context else None,
            trace_id=trace_id,
            correlation_id=correlation_id,
            started_at=started,
            finished_at=finished,
            error_message=str(last_error),
        ),
    )

