from __future__ import annotations

import json
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.common import WorkflowStatus
from app.contracts.workflows.execution import ProspectWorkflowExecutionState
from app.core.config import Settings, get_settings
from app.core.tenancy import TenantContext
from app.observability.runtime import ObservabilityRuntime, get_observability_runtime
from app.repositories.interfaces import ProspectWorkflowRepository


class WorkflowQueueFullError(RuntimeError):
    pass


class WorkflowJobCancelledError(RuntimeError):
    pass


class WorkflowJobTimeoutError(RuntimeError):
    pass


class WorkflowJobState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    tenant_id: str
    workflow_run_id: str
    status: WorkflowStatus = WorkflowStatus.queued
    retry_count: int = 0
    attempt_metadata: list[dict] = Field(default_factory=list)
    status_transitions: list[dict] = Field(default_factory=list)
    cancellation_requested: bool = False
    queued_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    workflow_state: dict = Field(default_factory=dict)
    trace_id: str | None = None
    correlation_id: str | None = None
    error_message: str | None = None


class WorkflowQueueBackend(Protocol):
    def enqueue(self, job: WorkflowJobState) -> None:
        ...

    def pop(self) -> WorkflowJobState | None:
        ...

    def get(self, job_id: str) -> WorkflowJobState | None:
        ...

    def update(self, job: WorkflowJobState) -> None:
        ...

    def cancel(self, job_id: str) -> WorkflowJobState | None:
        ...

    def pending_count(self) -> int:
        ...

    def active_count(self) -> int:
        ...

    def active_jobs(self) -> list[WorkflowJobState]:
        ...


class InMemoryWorkflowQueueBackend:
    def __init__(self) -> None:
        self._pending: deque[str] = deque()
        self._jobs: dict[str, WorkflowJobState] = {}
        self._active: set[str] = set()

    def enqueue(self, job: WorkflowJobState) -> None:
        self._jobs[job.job_id] = job
        if job.job_id not in self._pending:
            self._pending.append(job.job_id)

    def pop(self) -> WorkflowJobState | None:
        while self._pending:
            job_id = self._pending.popleft()
            job = self._jobs.get(job_id)
            if job is None:
                continue
            if job.cancellation_requested:
                return job
            self._active.add(job_id)
            return job
        return None

    def get(self, job_id: str) -> WorkflowJobState | None:
        return self._jobs.get(job_id)

    def update(self, job: WorkflowJobState) -> None:
        self._jobs[job.job_id] = job
        if job.status != WorkflowStatus.running:
            self._active.discard(job.job_id)

    def cancel(self, job_id: str) -> WorkflowJobState | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        job.cancellation_requested = True
        self._jobs[job_id] = job
        self._pending = deque(item for item in self._pending if item != job_id)
        return job

    def pending_count(self) -> int:
        return len(self._pending)

    def active_count(self) -> int:
        return len(self._active)

    def active_jobs(self) -> list[WorkflowJobState]:
        return [self._jobs[job_id] for job_id in self._active if job_id in self._jobs]


class RedisWorkflowQueueBackend:
    def __init__(self, client: Any, *, prefix: str = "workflow") -> None:
        self._client = client
        self._prefix = prefix

    @classmethod
    def from_settings(cls, settings: Settings) -> "RedisWorkflowQueueBackend | InMemoryWorkflowQueueBackend":
        if not settings.workflow_redis_url:
            return InMemoryWorkflowQueueBackend()
        import redis

        return cls(redis.Redis.from_url(settings.workflow_redis_url))

    def _queue_key(self) -> str:
        return f"{self._prefix}:pending"

    def _active_key(self) -> str:
        return f"{self._prefix}:active"

    def _job_key(self, job_id: str) -> str:
        return f"{self._prefix}:job:{job_id}"

    @staticmethod
    def _dump(job: WorkflowJobState) -> str:
        return job.model_dump_json()

    @staticmethod
    def _load(data: Any) -> WorkflowJobState | None:
        if not data:
            return None
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return WorkflowJobState.model_validate_json(data)

    def enqueue(self, job: WorkflowJobState) -> None:
        self._client.set(self._job_key(job.job_id), self._dump(job))
        self._client.rpush(self._queue_key(), job.job_id)

    def pop(self) -> WorkflowJobState | None:
        job_id = self._client.lpop(self._queue_key())
        if not job_id:
            return None
        if isinstance(job_id, bytes):
            job_id = job_id.decode("utf-8")
        job = self.get(job_id)
        if job is None:
            return None
        self._client.sadd(self._active_key(), job_id)
        return job

    def get(self, job_id: str) -> WorkflowJobState | None:
        return self._load(self._client.get(self._job_key(job_id)))

    def update(self, job: WorkflowJobState) -> None:
        self._client.set(self._job_key(job.job_id), self._dump(job))
        if job.status != WorkflowStatus.running:
            self._client.srem(self._active_key(), job.job_id)

    def cancel(self, job_id: str) -> WorkflowJobState | None:
        job = self.get(job_id)
        if job is None:
            return None
        job.cancellation_requested = True
        self.update(job)
        self._client.lrem(self._queue_key(), 0, job_id)
        return job

    def pending_count(self) -> int:
        return int(self._client.llen(self._queue_key()) or 0)

    def active_count(self) -> int:
        return int(self._client.scard(self._active_key()) or 0)

    def active_jobs(self) -> list[WorkflowJobState]:
        members = self._client.smembers(self._active_key()) or []
        jobs: list[WorkflowJobState] = []
        for member in members:
            job_id = member.decode("utf-8") if isinstance(member, bytes) else str(member)
            job = self.get(job_id)
            if job is not None:
                jobs.append(job)
        return jobs


class ProspectWorkflowWorker:
    def __init__(
        self,
        repository: ProspectWorkflowRepository,
        *,
        backend: WorkflowQueueBackend | None = None,
        observability: ObservabilityRuntime | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings or get_settings()
        self._backend = backend or RedisWorkflowQueueBackend.from_settings(self._settings)
        self._obs = observability or get_observability_runtime()

    def submit(self, state: ProspectWorkflowExecutionState, context: TenantContext) -> WorkflowJobState:
        if self._backend.pending_count() >= self._settings.workflow_queue_threshold:
            raise WorkflowQueueFullError("Workflow queue threshold reached.")
        job = WorkflowJobState(
            job_id=state.workflow_run_id,
            tenant_id=state.tenant_id,
            workflow_run_id=state.workflow_run_id,
            workflow_state=state.model_dump(mode="json"),
            trace_id=state.traces[-1].trace_id if state.traces else None,
            correlation_id=state.traces[-1].correlation_id if state.traces else None,
        )
        self._transition(job, WorkflowStatus.queued, reason="submitted")
        self._backend.enqueue(job)
        self._persist_state(job, context, state)
        return job

    def run_pending(
        self,
        *,
        context: TenantContext,
        execute: Callable[[ProspectWorkflowExecutionState, TenantContext], ProspectWorkflowExecutionState],
        max_jobs: int | None = None,
    ) -> list[ProspectWorkflowExecutionState]:
        results: list[ProspectWorkflowExecutionState] = []
        while self._backend.active_count() < self._settings.workflow_concurrent_limit:
            if max_jobs is not None and len(results) >= max_jobs:
                break
            job = self._backend.pop()
            if job is None:
                break
            outcome = self._process_job(job, context=context, execute=execute, requeue_on_retry=True)
            if outcome is not None:
                results.append(outcome)
        return results

    def run_inline(
        self,
        state: ProspectWorkflowExecutionState,
        *,
        context: TenantContext,
        execute: Callable[[ProspectWorkflowExecutionState, TenantContext], ProspectWorkflowExecutionState],
    ) -> ProspectWorkflowExecutionState:
        job = self.submit(state, context)
        if not self._settings.workflow_inline_execution:
            return ProspectWorkflowExecutionState.model_validate(job.workflow_state)
        return self.process_job(job.job_id, context=context, execute=execute)

    def process_job(
        self,
        job_id: str,
        *,
        context: TenantContext,
        execute: Callable[[ProspectWorkflowExecutionState, TenantContext], ProspectWorkflowExecutionState],
    ) -> ProspectWorkflowExecutionState:
        result: ProspectWorkflowExecutionState | None = None
        while True:
            job = self._backend.get(job_id)
            if job is None:
                raise LookupError("Workflow job not found.")
            result = self._process_job(job, context=context, execute=execute, requeue_on_retry=False)
            if result.status != WorkflowStatus.queued:
                return result
            queued_job = self._backend.get(job_id)
            if queued_job is None or queued_job.status != WorkflowStatus.queued:
                return result

    def cancel(self, *, tenant_id: str, workflow_run_id: str) -> WorkflowJobState | None:
        job = self._backend.get(workflow_run_id)
        if job is None or job.tenant_id != tenant_id:
            return None
        job = self._backend.cancel(workflow_run_id)
        if job is None:
            return None
        state = ProspectWorkflowExecutionState.model_validate(job.workflow_state)
        state.status = WorkflowStatus.cancelled
        state.current_step = state.current_step or "cancelled"
        self._transition(job, WorkflowStatus.cancelled, reason="cancel_requested")
        job.workflow_state = state.model_dump(mode="json")
        job.finished_at = datetime.now(tz=UTC)
        self._backend.update(job)
        self._repository.update_workflow_run_status(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run_id,
            status=WorkflowStatus.cancelled.value,
            output=state.model_dump(mode="json"),
            heartbeat=True,
        )
        return job

    def watchdog(self, *, timeout_seconds: int | None = None) -> list[WorkflowJobState]:
        timeout_seconds = timeout_seconds or self._settings.workflow_job_timeout_seconds
        now = datetime.now(tz=UTC)
        timed_out: list[WorkflowJobState] = []
        for job in self._backend.active_jobs():
            heartbeat = job.last_heartbeat_at or job.started_at or job.queued_at
            if now - heartbeat < timedelta(seconds=timeout_seconds):
                continue
            state = ProspectWorkflowExecutionState.model_validate(job.workflow_state)
            state.status = WorkflowStatus.timed_out
            state.last_error = "Workflow watchdog timed out the job."
            self._transition(job, WorkflowStatus.timed_out, reason="watchdog_timeout")
            job.workflow_state = state.model_dump(mode="json")
            job.finished_at = now
            self._backend.update(job)
            self._repository.update_workflow_run_status(
                tenant_id=job.tenant_id,
                workflow_run_id=job.workflow_run_id,
                status=WorkflowStatus.timed_out.value,
                output=state.model_dump(mode="json"),
                heartbeat=True,
            )
            timed_out.append(job)
        return timed_out

    def _process_job(
        self,
        job: WorkflowJobState,
        *,
        context: TenantContext,
        execute: Callable[[ProspectWorkflowExecutionState, TenantContext], ProspectWorkflowExecutionState],
        requeue_on_retry: bool,
    ) -> ProspectWorkflowExecutionState | None:
        if job.cancellation_requested:
            return self._finalize(job, WorkflowStatus.cancelled, reason="cancelled_before_start")

        job.started_at = job.started_at or datetime.now(tz=UTC)
        job.last_heartbeat_at = datetime.now(tz=UTC)
        self._transition(job, WorkflowStatus.running, reason="worker_started")
        self._backend.update(job)

        state = ProspectWorkflowExecutionState.model_validate(job.workflow_state)
        state.status = WorkflowStatus.running
        state.retry_count = job.retry_count
        state.attempt_metadata = list(state.attempt_metadata)
        state.evidence.status_transitions = list(state.evidence.status_transitions)

        try:
            updated = execute(state, context=context)
        except Exception as exc:  # noqa: BLE001 - worker retry boundary
            job.retry_count += 1
            job.attempt_metadata.append(
                {
                    "attempt": job.retry_count,
                    "error": exc.__class__.__name__,
                    "message": str(exc),
                    "occurred_at": datetime.now(tz=UTC).isoformat(),
                }
            )
            state.retry_count = job.retry_count
            state.attempt_metadata = job.attempt_metadata
            state.last_error = str(exc)
            if job.retry_count < self._settings.workflow_retry_max_attempts and not job.cancellation_requested:
                self._transition(job, WorkflowStatus.queued, reason="retry_scheduled")
                state.status = WorkflowStatus.queued
                job.workflow_state = state.model_dump(mode="json")
                job.last_heartbeat_at = datetime.now(tz=UTC)
                self._backend.update(job)
                if requeue_on_retry:
                    self._backend.enqueue(job)
                self._persist_state(job, context, state)
                return state
            return self._finalize(job, WorkflowStatus.failed, reason="worker_failed", error_message=str(exc), state=state)

        updated.retry_count = job.retry_count
        updated.attempt_metadata = job.attempt_metadata
        updated.evidence.status_transitions = [*updated.evidence.status_transitions, *job.status_transitions]
        if updated.status == WorkflowStatus.cancelled:
            return self._finalize(job, WorkflowStatus.cancelled, reason="workflow_cancelled", state=updated)
        if updated.status == WorkflowStatus.timed_out:
            return self._finalize(job, WorkflowStatus.timed_out, reason="workflow_timed_out", state=updated)
        return self._finalize(job, updated.status, reason="worker_completed", state=updated)

    def _finalize(
        self,
        job: WorkflowJobState,
        status: WorkflowStatus,
        *,
        reason: str,
        state: ProspectWorkflowExecutionState | None = None,
        error_message: str | None = None,
    ) -> ProspectWorkflowExecutionState:
        state = state or ProspectWorkflowExecutionState.model_validate(job.workflow_state)
        state.status = status
        state.last_error = error_message
        if status == WorkflowStatus.succeeded and state.current_step is None:
            state.current_step = "completed"
        self._transition(job, status, reason=reason, error_message=error_message)
        now = datetime.now(tz=UTC)
        job.finished_at = now
        job.last_heartbeat_at = now
        job.workflow_state = state.model_dump(mode="json")
        self._backend.update(job)
        self._persist_state(job, self._context_from_job(job), state)
        return state

    def _transition(
        self,
        job: WorkflowJobState,
        to_status: WorkflowStatus,
        *,
        reason: str,
        error_message: str | None = None,
    ) -> None:
        transition = {
            "from_status": job.status.value if isinstance(job.status, WorkflowStatus) else str(job.status),
            "to_status": to_status.value,
            "reason": reason,
            "retry_count": job.retry_count,
            "occurred_at": datetime.now(tz=UTC).isoformat(),
        }
        if error_message is not None:
            transition["error_message"] = error_message
        job.status_transitions.append(transition)
        job.status = to_status

    def _persist_state(self, job: WorkflowJobState, context: TenantContext, state: ProspectWorkflowExecutionState) -> None:
        started = time.perf_counter()
        state.evidence.status_transitions = list(job.status_transitions)
        state.retry_count = job.retry_count
        state.attempt_metadata = list(job.attempt_metadata)
        self._repository.update_workflow_run_status(
            tenant_id=context.tenant_id,
            workflow_run_id=job.workflow_run_id,
            status=state.status.value,
            output=state.model_dump(mode="json"),
            heartbeat=True,
        )
        self._obs.emit_operation(
            service="workers.workflow.persist_state",
            status=state.status.value,
            duration_ms=max(1, int((time.perf_counter() - started) * 1000)),
            tenant_id=context.tenant_id,
            workflow_id=job.workflow_run_id,
            trace_id=job.trace_id,
            correlation_id=job.correlation_id,
        )

    def _context_from_job(self, job: WorkflowJobState) -> TenantContext:
        return TenantContext(
            tenant_id=job.tenant_id,
            actor_user_id="system",
            roles=(),
            permissions=(),
        )
