from __future__ import annotations

import time
from datetime import UTC, datetime

from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session

from app.contracts.integrations import (
    IntegrationConnectionCreate,
    IntegrationConnectionRecord,
    IntegrationConnectionStatus,
    IntegrationConnectionUpdate,
    IntegrationCredentials,
    IntegrationExecutionRecord,
    IntegrationExecutionRequest,
    IntegrationExecutionStatus,
    IntegrationOperationType,
    IntegrationSyncRecord,
    IntegrationSyncRequest,
    IntegrationSyncStatus,
)
from app.integrations.secrets import IntegrationCredentialCodec
from app.models.integrations import IntegrationConnection, IntegrationRun, SyncCursor
from app.observability.runtime import ObservabilityRuntime, get_observability_runtime


class SqlIntegrationRepository:
    def __init__(
        self,
        session: Session,
        observability: ObservabilityRuntime | None = None,
        credential_codec: IntegrationCredentialCodec | None = None,
    ) -> None:
        self._session = session
        self._obs = observability or get_observability_runtime()
        self._credentials = credential_codec or IntegrationCredentialCodec()

    @staticmethod
    def _connection_record(row: IntegrationConnection) -> IntegrationConnectionRecord:
        return IntegrationConnectionRecord(
            id=row.id,
            tenant_id=row.tenant_id,
            provider=row.provider,
            connection_name=row.connection_name,
            is_default=row.is_default,
            auth_type=row.auth_type,  # pydantic coerces the enum/string
            status=row.status,
            scopes=list(row.scopes or []),
            expires_at=row.expires_at,
            health=row.health or {},
            has_credentials=bool(row.encrypted_credentials),
            created_at=row.created_at if isinstance(row.created_at, datetime) else datetime.now(tz=UTC),
            updated_at=row.updated_at if isinstance(row.updated_at, datetime) else datetime.now(tz=UTC),
        )

    def _execution_payload(
        self,
        *,
        status: str,
        response_metadata: dict | None,
        counts: dict | None,
        started_at: datetime,
        finished_at: datetime,
    ) -> dict:
        duration_ms = max(1, int((finished_at - started_at).total_seconds() * 1000))
        return {
            "status": status,
            "counts": counts or {},
            "response_metadata": response_metadata or {},
            "timing": {
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "duration_ms": duration_ms,
            },
        }

    def _execution_record(self, row: IntegrationRun) -> IntegrationExecutionRecord:
        payload = row.counts or {}
        timing = payload.get("timing") if isinstance(payload.get("timing"), dict) else {}
        response_metadata = payload.get("response_metadata") if isinstance(payload.get("response_metadata"), dict) else {}
        counts = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
        started_at = datetime.fromisoformat(timing["started_at"]) if timing.get("started_at") else row.created_at
        finished_at = datetime.fromisoformat(timing["finished_at"]) if timing.get("finished_at") else row.updated_at
        return IntegrationExecutionRecord(
            run_id=row.id,
            tenant_id=row.tenant_id,
            connection_id=row.connection_id,
            provider=row.provider,
            operation=IntegrationOperationType(row.request_metadata.get("operation", "sync")),
            status=IntegrationExecutionStatus(row.status),
            request_metadata=row.request_metadata or {},
            response_metadata=response_metadata,
            counts=counts,
            error_message=row.error_message,
            trace_id=row.request_metadata.get("trace_id"),
            correlation_id=row.request_metadata.get("correlation_id"),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(1, int(timing.get("duration_ms", 0) or 0)),
        )

    def _sync_payload(
        self,
        *,
        request: IntegrationSyncRequest,
        status: str,
        response_metadata: dict | None,
        error_message: str | None,
        source_record_id: str | None,
        started_at: datetime,
        finished_at: datetime,
    ) -> dict:
        return {
            "status": status,
            "source_type": request.source_type,
            "source_record_id": source_record_id,
            "sync_cursor": request.sync_cursor,
            "request_metadata": request.request_metadata,
            "response_metadata": response_metadata or {},
            "source_provider": request.provider,
            "trace_id": request.trace_id,
            "correlation_id": request.correlation_id,
            "error_message": error_message,
            "ingestion_timestamp": finished_at.isoformat(),
            "timing": {
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "duration_ms": max(1, int((finished_at - started_at).total_seconds() * 1000)),
            },
        }

    def _sync_record(self, row: SyncCursor) -> IntegrationSyncRecord:
        payload = row.cursor_value or {}
        timing = payload.get("timing") if isinstance(payload.get("timing"), dict) else {}
        response_metadata = payload.get("response_metadata") if isinstance(payload.get("response_metadata"), dict) else {}
        request_metadata = payload.get("request_metadata") if isinstance(payload.get("request_metadata"), dict) else {}
        started_at = datetime.fromisoformat(timing["started_at"]) if timing.get("started_at") else row.created_at
        finished_at = datetime.fromisoformat(timing["finished_at"]) if timing.get("finished_at") else row.updated_at
        return IntegrationSyncRecord(
            sync_cursor_id=row.id,
            tenant_id=row.tenant_id,
            connection_id=row.connection_id,
            provider=row.provider,
            source_provider=payload.get("source_provider") or row.provider,
            source_type=payload.get("source_type", ""),
            source_record_id=payload.get("source_record_id"),
            ingestion_timestamp=_parse_datetime(payload.get("ingestion_timestamp")),
            status=IntegrationSyncStatus(payload.get("status", IntegrationSyncStatus.completed.value)),
            request_metadata=request_metadata,
            response_metadata=response_metadata,
            sync_cursor=payload.get("sync_cursor") if isinstance(payload.get("sync_cursor"), dict) else {},
            error_message=payload.get("error_message"),
            trace_id=payload.get("trace_id"),
            correlation_id=payload.get("correlation_id"),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(1, int(timing.get("duration_ms", 0) or 0)),
        )

    def list_connections(self, *, tenant_id: str, provider: str | None = None):
        started = time.perf_counter()
        stmt = select(IntegrationConnection).where(IntegrationConnection.tenant_id == tenant_id)
        if provider:
            stmt = stmt.where(IntegrationConnection.provider == provider)
        rows = self._session.execute(stmt.order_by(IntegrationConnection.created_at.desc())).scalars().all()
        self._obs.emit_operation(
            service="repositories.integrations.list_connections",
            status="ok",
            duration_ms=max(1, int((time.perf_counter() - started) * 1000)),
            tenant_id=tenant_id,
        )
        return [self._connection_record(row) for row in rows]

    def get_connection(self, *, tenant_id: str, connection_id: str) -> IntegrationConnectionRecord | None:
        started = time.perf_counter()
        row = self._session.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.tenant_id == tenant_id,
                IntegrationConnection.id == connection_id,
            )
        ).scalar_one_or_none()
        self._obs.emit_operation(
            service="repositories.integrations.get_connection",
            status="ok",
            duration_ms=max(1, int((time.perf_counter() - started) * 1000)),
            tenant_id=tenant_id,
        )
        return self._connection_record(row) if row else None

    def get_connection_credentials(self, *, tenant_id: str, connection_id: str) -> IntegrationCredentials | None:
        row = self._session.execute(
            select(IntegrationConnection.encrypted_credentials).where(
                IntegrationConnection.tenant_id == tenant_id,
                IntegrationConnection.id == connection_id,
            )
        ).scalar_one_or_none()
        return self._credentials.decrypt(row)

    def get_default_connection(self, *, tenant_id: str, provider: str) -> IntegrationConnectionRecord | None:
        started = time.perf_counter()
        row = self._session.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.tenant_id == tenant_id,
                IntegrationConnection.provider == provider,
                IntegrationConnection.is_default.is_(True),
                IntegrationConnection.status == IntegrationConnectionStatus.live.value,
            ).order_by(IntegrationConnection.updated_at.desc())
        ).scalar_one_or_none()
        self._obs.emit_operation(
            service="repositories.integrations.get_default_connection",
            status="ok",
            duration_ms=max(1, int((time.perf_counter() - started) * 1000)),
            tenant_id=tenant_id,
        )
        return self._connection_record(row) if row else None

    def save_connection(
        self,
        command: IntegrationConnectionCreate,
        *,
        encrypted_credentials: bytes | None = None,
        status: str | None = None,
    ) -> IntegrationConnectionRecord:
        started = time.perf_counter()
        existing = self._session.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.tenant_id == command.tenant_id,
                IntegrationConnection.provider == command.provider,
                IntegrationConnection.connection_name == command.connection_name,
            )
        ).scalar_one_or_none()

        resolved_status = status or IntegrationConnectionStatus.not_configured.value
        if command.is_default and resolved_status == IntegrationConnectionStatus.live.value:
            self._session.execute(
                update(IntegrationConnection)
                .where(
                    IntegrationConnection.tenant_id == command.tenant_id,
                    IntegrationConnection.provider == command.provider,
                    IntegrationConnection.id != (existing.id if existing else "__none__"),
                )
                .values(is_default=False, updated_at=datetime.now(tz=UTC))
            )

        if existing is None:
            row = IntegrationConnection(
                tenant_id=command.tenant_id,
                provider=command.provider,
                connection_name=command.connection_name,
                is_default=command.is_default,
                auth_type=command.auth_type.value,
                status=resolved_status,
                scopes=command.scopes or (command.credentials.scopes if command.credentials else []),
                encrypted_credentials=encrypted_credentials,
                expires_at=command.credentials.expires_at if command.credentials else None,
                health=command.health or {},
            )
            self._session.add(row)
            self._session.flush()
        else:
            existing.provider = command.provider
            existing.connection_name = command.connection_name
            existing.is_default = command.is_default
            existing.auth_type = command.auth_type.value
            existing.status = resolved_status
            existing.scopes = command.scopes or (command.credentials.scopes if command.credentials else existing.scopes)
            if encrypted_credentials is not None:
                existing.encrypted_credentials = encrypted_credentials
            if command.credentials and command.credentials.expires_at is not None:
                existing.expires_at = command.credentials.expires_at
            if command.health:
                existing.health = command.health
            existing.updated_at = datetime.now(tz=UTC)
            self._session.flush()
            row = existing

        self._obs.emit_operation(
            service="repositories.integrations.save_connection",
            status="ok",
            duration_ms=max(1, int((time.perf_counter() - started) * 1000)),
            tenant_id=command.tenant_id,
        )
        return self._connection_record(row)

    def update_connection(
        self,
        *,
        tenant_id: str,
        connection_id: str,
        update: IntegrationConnectionUpdate,
    ) -> IntegrationConnectionRecord:
        started = time.perf_counter()
        row = self._session.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.tenant_id == tenant_id,
                IntegrationConnection.id == connection_id,
            )
        ).scalar_one()
        if update.status is not None:
            row.status = update.status.value
        if update.is_default is not None:
            row.is_default = update.is_default
        if update.scopes is not None:
            row.scopes = update.scopes
        if update.expires_at is not None:
            row.expires_at = update.expires_at
        if update.health is not None:
            row.health = update.health
        if update.has_credentials is not None and not update.has_credentials:
            row.encrypted_credentials = None
        row.updated_at = datetime.now(tz=UTC)
        self._session.flush()
        self._obs.emit_operation(
            service="repositories.integrations.update_connection",
            status="ok",
            duration_ms=max(1, int((time.perf_counter() - started) * 1000)),
            tenant_id=tenant_id,
        )
        return self._connection_record(row)

    def create_execution_run(
        self,
        request: IntegrationExecutionRequest,
        *,
        status: str,
        response_metadata: dict | None = None,
        counts: dict | None = None,
        error_message: str | None = None,
        started_at=None,
        finished_at=None,
    ) -> IntegrationExecutionRecord:
        started = time.perf_counter()
        started_at = started_at or datetime.now(tz=UTC)
        finished_at = finished_at or datetime.now(tz=UTC)
        row = IntegrationRun(
            tenant_id=request.tenant_id,
            connection_id=request.connection_id,
            provider=request.provider,
            status=status,
            request_metadata={
                **request.request_metadata,
                "operation": request.operation.value,
                "trace_id": request.trace_id,
                "correlation_id": request.correlation_id,
            },
            error_message=error_message,
            counts=self._execution_payload(
                status=status,
                response_metadata=response_metadata,
                counts=counts,
                started_at=started_at,
                finished_at=finished_at,
            ),
        )
        self._session.add(row)
        self._session.flush()
        self._obs.emit_operation(
            service="repositories.integrations.create_execution_run",
            status="ok",
            duration_ms=max(1, int((time.perf_counter() - started) * 1000)),
            tenant_id=request.tenant_id,
            workflow_id=request.request_metadata.get("workflow_run_id"),
            trace_id=request.trace_id,
            correlation_id=request.correlation_id,
        )
        return self._execution_record(row)

    def update_execution_run(
        self,
        *,
        tenant_id: str,
        run_id: str,
        status: str,
        response_metadata: dict | None = None,
        counts: dict | None = None,
        error_message: str | None = None,
        started_at=None,
        finished_at=None,
    ) -> IntegrationExecutionRecord:
        started = time.perf_counter()
        row = self._session.execute(
            select(IntegrationRun).where(
                IntegrationRun.tenant_id == tenant_id,
                IntegrationRun.id == run_id,
            )
        ).scalar_one()
        row.status = status
        if error_message is not None:
            row.error_message = error_message
        if started_at is None:
            started_at = row.created_at if isinstance(row.created_at, datetime) else datetime.now(tz=UTC)
        if finished_at is None:
            finished_at = datetime.now(tz=UTC)
        row.counts = self._execution_payload(
            status=status,
            response_metadata=response_metadata,
            counts=counts,
            started_at=started_at,
            finished_at=finished_at,
        )
        self._session.flush()
        self._obs.emit_operation(
            service="repositories.integrations.update_execution_run",
            status="ok",
            duration_ms=max(1, int((time.perf_counter() - started) * 1000)),
            tenant_id=tenant_id,
            workflow_id=row.request_metadata.get("workflow_run_id"),
            trace_id=row.request_metadata.get("trace_id"),
            correlation_id=row.request_metadata.get("correlation_id"),
        )
        return self._execution_record(row)

    def get_sync_cursor(
        self,
        *,
        tenant_id: str,
        connection_id: str,
        cursor_name: str,
    ) -> IntegrationSyncRecord | None:
        started = time.perf_counter()
        row = self._session.execute(
            select(SyncCursor).where(
                SyncCursor.tenant_id == tenant_id,
                SyncCursor.connection_id == connection_id,
                SyncCursor.cursor_name == cursor_name,
            )
        ).scalar_one_or_none()
        self._obs.emit_operation(
            service="repositories.integrations.get_sync_cursor",
            status="ok",
            duration_ms=max(1, int((time.perf_counter() - started) * 1000)),
            tenant_id=tenant_id,
        )
        return self._sync_record(row) if row else None

    def save_sync_cursor(
        self,
        request: IntegrationSyncRequest,
        *,
        status: str,
        response_metadata: dict | None = None,
        error_message: str | None = None,
        source_record_id: str | None = None,
        started_at=None,
        finished_at=None,
    ) -> IntegrationSyncRecord:
        started = time.perf_counter()
        started_at = started_at or datetime.now(tz=UTC)
        finished_at = finished_at or datetime.now(tz=UTC)
        row = self._session.execute(
            select(SyncCursor).where(
                SyncCursor.tenant_id == request.tenant_id,
                SyncCursor.connection_id == request.connection_id,
                SyncCursor.cursor_name == request.cursor_name,
            )
        ).scalar_one_or_none()
        payload = self._sync_payload(
            request=request,
            status=status,
            response_metadata=response_metadata,
            error_message=error_message,
            source_record_id=source_record_id,
            started_at=started_at,
            finished_at=finished_at,
        )
        if row is None:
            row = SyncCursor(
                tenant_id=request.tenant_id,
                connection_id=request.connection_id,
                provider=request.provider,
                cursor_name=request.cursor_name,
                cursor_value=payload,
            )
            self._session.add(row)
        else:
            row.provider = request.provider
            row.cursor_value = payload
        self._session.flush()
        self._obs.emit_operation(
            service="repositories.integrations.save_sync_cursor",
            status="ok",
            duration_ms=max(1, int((time.perf_counter() - started) * 1000)),
            tenant_id=request.tenant_id,
            workflow_id=request.request_metadata.get("workflow_run_id"),
            trace_id=request.trace_id,
            correlation_id=request.correlation_id,
        )
        return self._sync_record(row)


def _parse_datetime(value: object) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None

