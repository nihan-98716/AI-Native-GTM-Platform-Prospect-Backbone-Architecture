from __future__ import annotations

from datetime import UTC, datetime, timedelta
import time

from app.audit.interfaces import AuditService
from app.contracts.api.auth import TokenClaims
from app.contracts.integrations import (
    IntegrationAccountRecord,
    IntegrationAuthType,
    IntegrationConnectionCreate,
    IntegrationConnectionRecord,
    IntegrationConnectionStatus,
    IntegrationConnectionUpdate,
    IntegrationCredentials,
    IntegrationContactRecord,
    IntegrationDiscoverSignalsOutput,
    IntegrationEnrichContactsOutput,
    IntegrationExecutionRequest,
    IntegrationExecutionStatus,
    IntegrationExecutionResult,
    IntegrationOperationType,
    IntegrationSearchAccountsOutput,
    IntegrationSignalRecord,
    IntegrationSyncOutput,
    IntegrationSyncRequest,
    IntegrationSyncResult,
    IntegrationSyncStatus,
)
from app.contracts.events.audit import AuditEventCreate
from app.core.config import Settings, get_settings
from app.core.rate_limit import FixedWindowRateLimiter
from app.core.tenancy import TenantContext
from app.integrations.errors import IntegrationError, IntegrationProviderUnavailableError, IntegrationRateLimitError
from app.integrations.registry import IntegrationProviderRegistry
from app.integrations.secrets import IntegrationCredentialCodec
from app.observability.runtime import ObservabilityRuntime, get_observability_runtime
from app.repositories.interfaces import IntegrationRepository


class IntegrationService:
    def __init__(
        self,
        repository: IntegrationRepository,
        registry: IntegrationProviderRegistry,
        audit_service: AuditService | None = None,
        observability: ObservabilityRuntime | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._repository = repository
        self._registry = registry
        self._audit_service = audit_service
        self._obs = observability or get_observability_runtime()
        self._settings = settings or get_settings()
        self._codec = IntegrationCredentialCodec(self._settings.jwt_secret)
        self._rate_limiter = FixedWindowRateLimiter(self._settings.integration_rate_limit_per_minute)
        self._retry_max_attempts = max(1, self._settings.integration_retry_max_attempts)
        self._retry_backoff_ms = max(0, self._settings.integration_retry_backoff_ms)
        self._circuit_breaker_threshold = max(1, self._settings.integration_circuit_breaker_threshold)
        self._circuit_breaker_open_seconds = max(1, self._settings.integration_circuit_breaker_open_seconds)

    def list_connections(self, context: TenantContext, provider: str | None = None) -> list[IntegrationConnectionRecord]:
        return list(self._repository.list_connections(tenant_id=context.tenant_id, provider=provider))

    def get_connection(self, context: TenantContext, connection_id: str) -> IntegrationConnectionRecord | None:
        return self._repository.get_connection(tenant_id=context.tenant_id, connection_id=connection_id)

    def connect(self, context: TenantContext, command: IntegrationConnectionCreate) -> IntegrationConnectionRecord:
        self._ensure_tenant(context, command.tenant_id)
        started = time.perf_counter()
        provider = self._registry.get(command.provider)
        credential_blob = self._codec.encrypt(command.credentials) if command.credentials else None
        try:
            validated = provider.connect(command)
        except IntegrationError as exc:
            failed = command.model_copy(update={"health": {**command.health, "error": str(exc)}})
            persisted = self._repository.save_connection(
                failed,
                encrypted_credentials=credential_blob,
                status=IntegrationConnectionStatus.failed.value,
            )
            self._emit_audit(
                context,
                action="integration.connection.failed",
                resource_id=persisted.id,
                metadata={"provider": command.provider, "connection_name": command.connection_name, "error": str(exc)},
            )
            self._obs.emit_operation(
                service="services.integrations.connect",
                status="error",
                duration_ms=int((time.perf_counter() - started) * 1000),
                tenant_id=context.tenant_id,
            )
            raise

        persisted = self._repository.save_connection(
            command.model_copy(update={"health": validated.health}),
            encrypted_credentials=credential_blob,
            status=validated.status.value,
        )
        updated = self._repository.update_connection(
            tenant_id=context.tenant_id,
            connection_id=persisted.id,
            update=IntegrationConnectionUpdate(
                status=validated.status,
                is_default=validated.is_default,
                scopes=validated.scopes,
                expires_at=validated.expires_at,
                health=validated.health,
                has_credentials=validated.has_credentials,
            ),
        )
        self._emit_audit(
            context,
            action="integration.connection.connected",
            resource_id=updated.id,
            metadata={"provider": command.provider, "connection_name": command.connection_name},
        )
        self._obs.emit_operation(
            service="services.integrations.connect",
            status="ok",
            duration_ms=int((time.perf_counter() - started) * 1000),
            tenant_id=context.tenant_id,
        )
        return updated

    def validate_connection(
        self,
        context: TenantContext,
        *,
        connection_id: str,
    ) -> IntegrationConnectionRecord:
        started = time.perf_counter()
        connection = self._require_connection(context, connection_id)
        provider = self._registry.get(connection.provider)
        credentials = self._repository.get_connection_credentials(tenant_id=context.tenant_id, connection_id=connection_id)
        validated = provider.validate(connection, credentials=credentials)
        updated = self._repository.update_connection(
            tenant_id=context.tenant_id,
            connection_id=connection_id,
            update=IntegrationConnectionUpdate(
                status=validated.status,
                scopes=validated.scopes,
                expires_at=validated.expires_at,
                health=validated.health,
            ),
        )
        self._emit_audit(
            context,
            action="integration.connection.validated",
            resource_id=connection_id,
            metadata={"provider": connection.provider, "status": updated.status.value},
        )
        self._obs.emit_operation(
            service="services.integrations.validate_connection",
            status="ok",
            duration_ms=int((time.perf_counter() - started) * 1000),
            tenant_id=context.tenant_id,
        )
        return updated

    def disconnect(self, context: TenantContext, *, connection_id: str) -> IntegrationConnectionRecord:
        started = time.perf_counter()
        connection = self._require_connection(context, connection_id)
        provider = self._registry.get(connection.provider)
        update = provider.disconnect(connection)
        updated = self._repository.update_connection(
            tenant_id=context.tenant_id,
            connection_id=connection_id,
            update=update,
        )
        self._emit_audit(
            context,
            action="integration.connection.disconnected",
            resource_id=connection_id,
            metadata={"provider": connection.provider},
        )
        self._obs.emit_operation(
            service="services.integrations.disconnect",
            status="ok",
            duration_ms=int((time.perf_counter() - started) * 1000),
            tenant_id=context.tenant_id,
        )
        return updated

    def health_check(self, context: TenantContext, *, connection_id: str) -> IntegrationConnectionRecord:
        started = time.perf_counter()
        connection = self._require_connection(context, connection_id)
        provider = self._registry.get(connection.provider)
        credentials = self._repository.get_connection_credentials(tenant_id=context.tenant_id, connection_id=connection_id)
        checked = provider.health_check(connection, credentials=credentials)
        updated = self._repository.update_connection(
            tenant_id=context.tenant_id,
            connection_id=connection_id,
            update=IntegrationConnectionUpdate(
                status=checked.status,
                expires_at=checked.expires_at,
                health=checked.health,
            ),
        )
        self._emit_audit(
            context,
            action="integration.connection.health_checked",
            resource_id=connection_id,
            metadata={"provider": connection.provider, "status": updated.status.value},
        )
        self._obs.emit_operation(
            service="services.integrations.health_check",
            status="ok",
            duration_ms=int((time.perf_counter() - started) * 1000),
            tenant_id=context.tenant_id,
        )
        return updated

    def search_accounts(
        self,
        context: TenantContext,
        *,
        provider: str | None = None,
        connection_id: str | None = None,
        query: str | None = None,
        limit: int = 10,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        workflow_run_id: str | None = None,
    ) -> IntegrationSearchAccountsOutput:
        execution = self._execute(
            context,
            operation=IntegrationOperationType.search_accounts,
            provider=provider,
            connection_id=connection_id,
            payload={"query": query, "limit": limit},
            trace_id=trace_id,
            correlation_id=correlation_id,
            workflow_run_id=workflow_run_id,
        )
        records = [IntegrationAccountRecord.model_validate(item) for item in execution.response_payload.get("records", [])]
        return IntegrationSearchAccountsOutput(
            status=execution.status,
            provider=execution.provider,
            source_provider=execution.source_provider,
            source_type=execution.source_type,
            source_record_id=execution.source_record_id,
            ingestion_timestamp=execution.ingestion_timestamp,
            records=records,
            response_metadata=execution.response_metadata,
            error_message=execution.error_message,
        )

    def enrich_contacts(
        self,
        context: TenantContext,
        *,
        provider: str | None = None,
        connection_id: str | None = None,
        account_ids: list[str],
        trace_id: str | None = None,
        correlation_id: str | None = None,
        workflow_run_id: str | None = None,
    ) -> IntegrationEnrichContactsOutput:
        execution = self._execute(
            context,
            operation=IntegrationOperationType.enrich_contacts,
            provider=provider,
            connection_id=connection_id,
            payload={"account_ids": account_ids, "limit": max(len(account_ids), 1)},
            trace_id=trace_id,
            correlation_id=correlation_id,
            workflow_run_id=workflow_run_id,
        )
        records = [IntegrationContactRecord.model_validate(item) for item in execution.response_payload.get("records", [])]
        return IntegrationEnrichContactsOutput(
            status=execution.status,
            provider=execution.provider,
            source_provider=execution.source_provider,
            source_type=execution.source_type,
            source_record_id=execution.source_record_id,
            ingestion_timestamp=execution.ingestion_timestamp,
            records=records,
            response_metadata=execution.response_metadata,
            error_message=execution.error_message,
        )

    def discover_signals(
        self,
        context: TenantContext,
        *,
        provider: str | None = None,
        connection_id: str | None = None,
        account_ids: list[str],
        trace_id: str | None = None,
        correlation_id: str | None = None,
        workflow_run_id: str | None = None,
    ) -> IntegrationDiscoverSignalsOutput:
        execution = self._execute(
            context,
            operation=IntegrationOperationType.discover_signals,
            provider=provider,
            connection_id=connection_id,
            payload={"account_ids": account_ids, "limit": max(len(account_ids), 1)},
            trace_id=trace_id,
            correlation_id=correlation_id,
            workflow_run_id=workflow_run_id,
        )
        records = [IntegrationSignalRecord.model_validate(item) for item in execution.response_payload.get("records", [])]
        return IntegrationDiscoverSignalsOutput(
            status=execution.status,
            provider=execution.provider,
            source_provider=execution.source_provider,
            source_type=execution.source_type,
            source_record_id=execution.source_record_id,
            ingestion_timestamp=execution.ingestion_timestamp,
            records=records,
            response_metadata=execution.response_metadata,
            error_message=execution.error_message,
        )

    def sync(
        self,
        context: TenantContext,
        *,
        provider: str | None = None,
        connection_id: str | None = None,
        source_type: str,
        cursor_name: str,
        sync_cursor: dict | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        workflow_run_id: str | None = None,
    ) -> IntegrationSyncOutput:
        started = datetime.now(tz=UTC)
        connection = self._resolve_connection(context, provider=provider, connection_id=connection_id)
        if connection is None:
            finished = datetime.now(tz=UTC)
            return IntegrationSyncOutput(
                status=IntegrationSyncStatus.failed,
                provider=provider or self._registry.default().name,
                sync_cursor=sync_cursor or {},
                error_message="No live integration connection is available.",
                response_metadata={"duration_ms": max(1, int((finished - started).total_seconds() * 1000))},
            )
        if not self._allow_request(context.tenant_id, connection.provider):
            updated = self._repository.update_connection(
                tenant_id=context.tenant_id,
                connection_id=connection.id,
                update=IntegrationConnectionUpdate(
                    status=IntegrationConnectionStatus.rate_limited,
                    health={**connection.health, "rate_limited_at": datetime.now(tz=UTC).isoformat()},
                ),
            )
            finished = datetime.now(tz=UTC)
            return IntegrationSyncOutput(
                status=IntegrationSyncStatus.rate_limited,
                provider=updated.provider,
                sync_cursor=sync_cursor or {},
                error_message="Integration rate limit exceeded.",
                response_metadata={"duration_ms": max(1, int((finished - started).total_seconds() * 1000))},
            )
        connection = self._prepare_circuit(context, connection)
        if connection is None:
            started = datetime.now(tz=UTC)
            finished = datetime.now(tz=UTC)
            return IntegrationSyncOutput(
                status=IntegrationSyncStatus.failed,
                provider=provider or self._registry.default().name,
                sync_cursor=sync_cursor or {},
                error_message="Integration circuit is open.",
                response_metadata={"duration_ms": max(1, int((finished - started).total_seconds() * 1000))},
            )
        credentials = self._repository.get_connection_credentials(tenant_id=context.tenant_id, connection_id=connection.id)
        provider_impl = self._registry.get(connection.provider)
        request = IntegrationSyncRequest(
            tenant_id=context.tenant_id,
            connection_id=connection.id,
            provider=connection.provider,
            source_type=source_type,
            cursor_name=cursor_name,
            sync_cursor=sync_cursor or {},
            request_metadata={"workflow_run_id": workflow_run_id, "trace_id": trace_id, "correlation_id": correlation_id},
            trace_id=trace_id,
            correlation_id=correlation_id,
        )
        started = datetime.now(tz=UTC)
        run_request = IntegrationExecutionRequest(
            tenant_id=context.tenant_id,
            connection_id=connection.id,
            provider=connection.provider,
            operation=IntegrationOperationType.sync,
            input={"source_type": source_type, "cursor_name": cursor_name, "sync_cursor": sync_cursor or {}},
            request_metadata={"workflow_run_id": workflow_run_id, "trace_id": trace_id, "correlation_id": correlation_id},
            trace_id=trace_id,
            correlation_id=correlation_id,
        )
        run = self._repository.create_execution_run(
            run_request,
            status=IntegrationExecutionStatus.running.value,
            response_metadata={},
            counts={"record_count": 0, "retry_attempts": 0},
            started_at=started,
            finished_at=started,
        )

        def call() -> IntegrationSyncResult:
            return provider_impl.sync(request, credentials=credentials)

        def on_success(result: IntegrationSyncResult, attempt: int) -> IntegrationSyncResult:
            finished = result.finished_at
            provenance = {
                "source_provider": result.source_provider or result.provider,
                "source_type": result.source_type or source_type,
                "source_record_id": result.source_record_id,
                "ingestion_timestamp": result.ingestion_timestamp.isoformat() if result.ingestion_timestamp else finished.isoformat(),
            }
            response_metadata = {**result.response_metadata, "retry_attempts": attempt - 1, "provenance": provenance}
            self._repository.update_execution_run(
                tenant_id=context.tenant_id,
                run_id=run.run_id,
                status=result.status.value,
                response_metadata=response_metadata,
                counts={"record_count": len(result.response_payload.get("records", [])), "retry_attempts": attempt - 1},
                error_message=result.error_message,
                started_at=result.started_at,
                finished_at=finished,
            )
            self._repository.save_sync_cursor(
                request,
                status=result.status.value,
                response_metadata=response_metadata,
                error_message=result.error_message,
                source_record_id=result.source_record_id,
                started_at=result.started_at,
                finished_at=finished,
            )
            if result.status == IntegrationSyncStatus.completed:
                self._record_connection_success(context, connection, response_metadata)
            elif result.status == IntegrationSyncStatus.rate_limited:
                self._record_connection_failure(context, connection, error=result.error_message or "rate_limited", rate_limited=True)
            else:
                self._record_connection_failure(context, connection, error=result.error_message or "failed")
            self._emit_audit(
                context,
                action="integration.provider.sync",
                resource_id=connection.id,
                metadata={
                    "provider": connection.provider,
                    "source_type": source_type,
                    "status": result.status.value,
                    "workflow_run_id": workflow_run_id,
                    "trace_id": trace_id,
                    "correlation_id": correlation_id,
                    "retry_attempts": attempt - 1,
                    "duration_ms": result.duration_ms,
                },
            )
            return result.model_copy(update={"response_metadata": response_metadata})

        def on_failure(exc: Exception, attempt: int) -> IntegrationSyncResult:
            finished = datetime.now(tz=UTC)
            status = IntegrationSyncStatus.rate_limited if isinstance(exc, IntegrationRateLimitError) else IntegrationSyncStatus.failed
            response_metadata = {
                "retry_attempts": attempt - 1,
                "failure_metadata": {"exception": exc.__class__.__name__},
                "provenance": {
                    "source_provider": connection.provider,
                    "source_type": source_type,
                    "source_record_id": None,
                    "ingestion_timestamp": finished.isoformat(),
                },
            }
            self._repository.update_execution_run(
                tenant_id=context.tenant_id,
                run_id=run.run_id,
                status=status.value,
                response_metadata=response_metadata,
                counts={"record_count": 0, "retry_attempts": attempt - 1},
                error_message=str(exc),
                started_at=started,
                finished_at=finished,
            )
            self._repository.save_sync_cursor(
                request,
                status=status.value,
                response_metadata=response_metadata,
                error_message=str(exc),
                source_record_id=None,
                started_at=started,
                finished_at=finished,
            )
            self._record_connection_failure(context, connection, error=str(exc), rate_limited=status == IntegrationSyncStatus.rate_limited)
            self._emit_audit(
                context,
                action="integration.provider.sync",
                resource_id=connection.id,
                metadata={
                    "provider": connection.provider,
                    "source_type": source_type,
                    "status": status.value,
                    "workflow_run_id": workflow_run_id,
                    "trace_id": trace_id,
                    "correlation_id": correlation_id,
                    "retry_attempts": attempt - 1,
                    "duration_ms": int((finished - started).total_seconds() * 1000),
                },
            )
            return IntegrationSyncResult(
                provider=connection.provider,
                status=status,
                sync_cursor=sync_cursor or {},
                source_provider=connection.provider,
                response_metadata=response_metadata,
                error_message=str(exc),
                trace_id=trace_id,
                correlation_id=correlation_id,
                started_at=started,
                finished_at=finished,
                duration_ms=int((finished - started).total_seconds() * 1000),
            )

        execution = self._invoke_with_retry(
            call=call,
            on_failure=on_failure,
            on_success=on_success,
            request_status=f"sync:{source_type}",
        )
        assert isinstance(execution, IntegrationSyncResult)
        return IntegrationSyncOutput(
            status=execution.status,
            provider=execution.provider,
            source_provider=execution.source_provider,
            sync_cursor=execution.sync_cursor,
            source_record_id=execution.source_record_id,
            ingestion_timestamp=execution.ingestion_timestamp,
            response_metadata=execution.response_metadata,
            error_message=execution.error_message,
        )

    def _execute(
        self,
        context: TenantContext,
        *,
        operation: IntegrationOperationType,
        provider: str | None,
        connection_id: str | None,
        payload: dict,
        trace_id: str | None,
        correlation_id: str | None,
        workflow_run_id: str | None,
    ) -> IntegrationExecutionResult:
        started = datetime.now(tz=UTC)
        connection = self._resolve_connection(context, provider=provider, connection_id=connection_id)
        if connection is None:
            finished = datetime.now(tz=UTC)
            return IntegrationExecutionResult(
                provider=provider or self._registry.default().name,
                operation=operation,
                status=IntegrationExecutionStatus.failed,
                response_payload={},
                response_metadata={},
                counts={"record_count": 0},
                error_message="No live integration connection is available.",
                trace_id=trace_id,
                correlation_id=correlation_id,
                started_at=started,
                finished_at=finished,
                duration_ms=max(1, int((finished - started).total_seconds() * 1000)),
            )

        if not self._allow_request(context.tenant_id, connection.provider):
            updated = self._repository.update_connection(
                tenant_id=context.tenant_id,
                connection_id=connection.id,
                update=IntegrationConnectionUpdate(
                    status=IntegrationConnectionStatus.rate_limited,
                    health={**connection.health, "rate_limited_at": datetime.now(tz=UTC).isoformat()},
                ),
            )
            started = datetime.now(tz=UTC)
            finished = datetime.now(tz=UTC)
            return IntegrationExecutionResult(
                provider=updated.provider,
                operation=operation,
                status=IntegrationExecutionStatus.rate_limited,
                response_payload={},
                response_metadata={},
                counts={"record_count": 0},
                error_message="Integration rate limit exceeded.",
                trace_id=trace_id,
                correlation_id=correlation_id,
                started_at=started,
                finished_at=finished,
                duration_ms=max(1, int((finished - started).total_seconds() * 1000)),
            )

        provider_impl = self._registry.get(connection.provider)
        connection = self._prepare_circuit(context, connection)
        if connection is None:
            started = datetime.now(tz=UTC)
            finished = started
            return IntegrationExecutionResult(
                provider=provider or self._registry.default().name,
                operation=operation,
                status=IntegrationExecutionStatus.failed,
                response_payload={},
                response_metadata={"circuit_state": "open"},
                counts={"record_count": 0},
                error_message="Integration circuit is open.",
                trace_id=trace_id,
                correlation_id=correlation_id,
                started_at=started,
                finished_at=finished,
                duration_ms=max(1, int((finished - started).total_seconds() * 1000)),
            )
        credentials = self._repository.get_connection_credentials(tenant_id=context.tenant_id, connection_id=connection.id)
        request = IntegrationExecutionRequest(
            tenant_id=context.tenant_id,
            connection_id=connection.id,
            provider=connection.provider,
            operation=operation,
            input=payload,
            request_metadata={"workflow_run_id": workflow_run_id, "trace_id": trace_id, "correlation_id": correlation_id},
            trace_id=trace_id,
            correlation_id=correlation_id,
        )
        started = datetime.now(tz=UTC)
        run = self._repository.create_execution_run(
            request,
            status=IntegrationExecutionStatus.running.value,
            response_metadata={},
            counts={"record_count": 0, "retry_attempts": 0},
            started_at=started,
            finished_at=started,
        )

        def call() -> IntegrationExecutionResult:
            return provider_impl.execute(request, credentials=credentials)

        def on_success(result: IntegrationExecutionResult, attempt: int) -> IntegrationExecutionResult:
            finished = result.finished_at
            provenance = {
                "source_provider": result.source_provider or result.provider,
                "source_type": result.source_type or operation.value,
                "source_record_id": result.source_record_id,
                "ingestion_timestamp": result.ingestion_timestamp.isoformat() if result.ingestion_timestamp else finished.isoformat(),
            }
            response_metadata = {**result.response_metadata, "retry_attempts": attempt - 1, "provenance": provenance}
            updated_run = self._repository.update_execution_run(
                tenant_id=context.tenant_id,
                run_id=run.run_id,
                status=result.status.value,
                response_metadata=response_metadata,
                counts={**result.counts, "retry_attempts": attempt - 1},
                error_message=result.error_message,
                started_at=result.started_at,
                finished_at=finished,
            )
            if result.status == IntegrationExecutionStatus.completed:
                self._record_connection_success(context, connection, response_metadata)
            elif result.status == IntegrationExecutionStatus.rate_limited:
                self._record_connection_failure(context, connection, error=result.error_message or "rate_limited", rate_limited=True)
            else:
                self._record_connection_failure(context, connection, error=result.error_message or "failed")
            self._emit_audit(
                context,
                action="integration.provider.request",
                resource_id=connection.id,
                metadata={
                    "provider": connection.provider,
                    "operation": operation.value,
                    "status": updated_run.status.value,
                    "workflow_run_id": workflow_run_id,
                    "trace_id": trace_id,
                    "correlation_id": correlation_id,
                    "retry_attempts": attempt - 1,
                    "duration_ms": result.duration_ms,
                },
            )
            return result.model_copy(update={"response_metadata": response_metadata})

        def on_failure(exc: Exception, attempt: int) -> IntegrationExecutionResult:
            finished = datetime.now(tz=UTC)
            status = IntegrationExecutionStatus.rate_limited if isinstance(exc, IntegrationRateLimitError) else IntegrationExecutionStatus.failed
            response_metadata = {
                "retry_attempts": attempt - 1,
                "failure_metadata": {"exception": exc.__class__.__name__},
                "provenance": {
                    "source_provider": connection.provider,
                    "source_type": operation.value,
                    "source_record_id": None,
                    "ingestion_timestamp": finished.isoformat(),
                },
            }
            self._repository.update_execution_run(
                tenant_id=context.tenant_id,
                run_id=run.run_id,
                status=status.value,
                response_metadata=response_metadata,
                counts={"record_count": 0, "retry_attempts": attempt - 1},
                error_message=str(exc),
                started_at=started,
                finished_at=finished,
            )
            self._record_connection_failure(context, connection, error=str(exc), rate_limited=status == IntegrationExecutionStatus.rate_limited)
            self._emit_audit(
                context,
                action="integration.provider.request",
                resource_id=connection.id,
                metadata={
                    "provider": connection.provider,
                    "operation": operation.value,
                    "status": status.value,
                    "workflow_run_id": workflow_run_id,
                    "trace_id": trace_id,
                    "correlation_id": correlation_id,
                    "retry_attempts": attempt - 1,
                    "duration_ms": int((finished - started).total_seconds() * 1000),
                },
            )
            return IntegrationExecutionResult(
                provider=connection.provider,
                operation=operation,
                status=status,
                response_payload={},
                response_metadata=response_metadata,
                counts={"record_count": 0, "retry_attempts": attempt - 1},
                error_message=str(exc),
                trace_id=trace_id,
                correlation_id=correlation_id,
                started_at=started,
                finished_at=finished,
                duration_ms=int((finished - started).total_seconds() * 1000),
            )

        result = self._invoke_with_retry(
            call=call,
            on_failure=on_failure,
            on_success=on_success,
            request_status=operation.value,
        )
        assert isinstance(result, IntegrationExecutionResult)
        return result

    def _resolve_connection(
        self,
        context: TenantContext,
        *,
        provider: str | None,
        connection_id: str | None,
    ) -> IntegrationConnectionRecord | None:
        if connection_id:
            return self._repository.get_connection(tenant_id=context.tenant_id, connection_id=connection_id)
        provider_name = provider or self._registry.default().name
        return self._repository.get_default_connection(tenant_id=context.tenant_id, provider=provider_name)

    def _allow_request(self, tenant_id: str, provider: str) -> bool:
        return self._rate_limiter.allow(f"{tenant_id}:{provider}")

    def _circuit_state(self, connection: IntegrationConnectionRecord) -> str:
        return str(connection.health.get("circuit_state") or "closed")

    def _circuit_open_until(self, connection: IntegrationConnectionRecord) -> datetime | None:
        value = connection.health.get("open_until")
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _is_retryable(self, exc: Exception) -> bool:
        return isinstance(exc, (IntegrationProviderUnavailableError, TimeoutError, ConnectionError))

    def _track_circuit(self, context: TenantContext, connection: IntegrationConnectionRecord, *, state: str, open_until: datetime | None = None, failure_count: int | None = None, error: str | None = None) -> IntegrationConnectionRecord:
        health = {**connection.health, "circuit_state": state}
        if open_until is not None:
            health["open_until"] = open_until.isoformat()
        if failure_count is not None:
            health["failure_count"] = failure_count
        if error is not None:
            health["last_error"] = error
        return self._repository.update_connection(
            tenant_id=context.tenant_id,
            connection_id=connection.id,
            update=IntegrationConnectionUpdate(
                status=IntegrationConnectionStatus.rate_limited if state == "open" else IntegrationConnectionStatus.live,
                health=health,
            ),
        )

    def _prepare_circuit(self, context: TenantContext, connection: IntegrationConnectionRecord) -> IntegrationConnectionRecord | None:
        state = self._circuit_state(connection)
        open_until = self._circuit_open_until(connection)
        now = datetime.now(tz=UTC)
        if state == "open" and open_until and open_until > now:
            return None
        if state == "open" and open_until and open_until <= now:
            return self._track_circuit(context, connection, state="half_open", failure_count=int(connection.health.get("failure_count", 0) or 0))
        return connection

    def _retry_delay_seconds(self, attempt: int) -> float:
        return (self._retry_backoff_ms * (2 ** max(0, attempt - 1))) / 1000.0

    def _invoke_with_retry(self, *, call, on_failure, on_success, request_status: str) -> object | None:
        last_exc: Exception | None = None
        for attempt in range(1, self._retry_max_attempts + 1):
            try:
                result = call()
                return on_success(result, attempt)
            except Exception as exc:  # noqa: BLE001 - narrow retry surface via _is_retryable
                last_exc = exc
                if attempt >= self._retry_max_attempts or not self._is_retryable(exc):
                    return on_failure(exc, attempt)
                time.sleep(self._retry_delay_seconds(attempt))
        if last_exc is not None:
            return on_failure(last_exc, self._retry_max_attempts)
        raise RuntimeError(f"Unhandled {request_status} retry flow.")

    def _record_connection_success(self, context: TenantContext, connection: IntegrationConnectionRecord, response_metadata: dict) -> None:
        health = {
            **connection.health,
            "failure_count": 0,
            "open_until": None,
            "circuit_state": "closed",
            "last_success_at": datetime.now(tz=UTC).isoformat(),
            "last_response": response_metadata,
        }
        self._repository.update_connection(
            tenant_id=context.tenant_id,
            connection_id=connection.id,
            update=IntegrationConnectionUpdate(status=IntegrationConnectionStatus.live, health=health),
        )

    def _record_connection_failure(self, context: TenantContext, connection: IntegrationConnectionRecord, *, error: str, rate_limited: bool = False) -> None:
        failure_count = int(connection.health.get("failure_count", 0) or 0) + 1
        open_until = connection.health.get("open_until")
        circuit_state = "closed"
        if failure_count >= self._circuit_breaker_threshold and not rate_limited:
            open_until = (datetime.now(tz=UTC) + timedelta(seconds=self._circuit_breaker_open_seconds)).isoformat()
            circuit_state = "open"
        health = {
            **connection.health,
            "failure_count": failure_count,
            "open_until": open_until,
            "circuit_state": circuit_state,
            "last_failure_at": datetime.now(tz=UTC).isoformat(),
            "last_error": error,
        }
        self._repository.update_connection(
            tenant_id=context.tenant_id,
            connection_id=connection.id,
            update=IntegrationConnectionUpdate(
                status=IntegrationConnectionStatus.rate_limited if rate_limited or circuit_state == "open" else IntegrationConnectionStatus.failed,
                health=health,
            ),
        )

    def _emit_audit(self, context: TenantContext, *, action: str, resource_id: str | None, metadata: dict) -> None:
        if self._audit_service is None:
            return
        self._audit_service.record(
            context,
            AuditEventCreate(
                actor_user_id=context.actor_user_id,
                action=action,
                resource_type="integration",
                resource_id=resource_id,
                metadata=metadata,
            ),
        )

    def _ensure_tenant(self, context: TenantContext, tenant_id: str) -> None:
        if context.tenant_id != tenant_id:
            raise PermissionError("Cross-tenant integration access is not allowed.")

    def _require_connection(self, context: TenantContext, connection_id: str) -> IntegrationConnectionRecord:
        connection = self._repository.get_connection(tenant_id=context.tenant_id, connection_id=connection_id)
        if connection is None:
            raise LookupError("Integration connection not found.")
        return connection
