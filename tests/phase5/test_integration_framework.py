from __future__ import annotations

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.agents.base import AgentExecutionContext
from app.agents.llm import LLMCompletion, LLMToolCall, ScriptedLLM
from app.agents.prospect_research import ProspectResearchAgent
from app.agents.tools.runtime import DefaultProspectAgentTools
from app.contracts.agents import OutreachDraftProposal, ProspectResearchInput, RankedAccount, ValueHypothesisDraft
from app.contracts.common import JobStatus, OutreachDraftStatus, WorkflowStatus
from app.contracts.integrations import (
    IntegrationAccountRecord,
    IntegrationAuthType,
    IntegrationConnectionCreate,
    IntegrationConnectionRecord,
    IntegrationConnectionStatus,
    IntegrationConnectionUpdate,
    IntegrationCredentials,
    IntegrationDiscoverSignalsOutput,
    IntegrationEnrichContactsOutput,
    IntegrationExecutionRequest,
    IntegrationExecutionResult,
    IntegrationExecutionStatus,
    IntegrationOperationType,
    IntegrationSearchAccountsOutput,
    IntegrationSignalRecord,
    IntegrationSyncResult,
    IntegrationSyncStatus,
)
from app.contracts.workflows.execution import ProspectWorkflowExecutionState
from app.core.config import Settings
from app.core.tenancy import TenantContext, set_tenant_context, tenant_context_var
from app.integrations.errors import IntegrationAuthenticationError, IntegrationProviderUnavailableError, IntegrationValidationError
from app.integrations.providers import ApolloIntegrationProvider
from app.integrations.registry import IntegrationProviderRegistry
from app.observability.runtime import ObservabilityRuntime
from app.repositories.integration_repository import SqlIntegrationRepository
from app.services.integrations import IntegrationService
from app.workers.workflow import InMemoryWorkflowQueueBackend, ProspectWorkflowWorker, WorkflowQueueFullError


DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.fixture()
def engine():
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL is required for DB-backed phase 5 tests")
    created = create_engine(DATABASE_URL)
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture()
def db(engine):
    with engine.begin() as connection:
        for table_name in ["integration_runs", "sync_cursors", "integration_connections", "accounts", "users", "tenants"]:
            connection.execute(text(f"delete from {table_name}"))
    yield engine


def create_tenant(connection, slug: str) -> str:
    return connection.execute(
        text("insert into tenants (name, slug) values (:name, :slug) returning id"),
        {"name": slug, "slug": slug},
    ).scalar_one()


class FakeApolloProvider:
    name = "apollo"

    @staticmethod
    def _record(command: IntegrationConnectionCreate, *, status: IntegrationConnectionStatus, health: dict | None = None) -> IntegrationConnectionRecord:
        now = datetime.now(tz=UTC)
        return IntegrationConnectionRecord(
            id=str(uuid4()),
            tenant_id=command.tenant_id,
            provider=command.provider,
            connection_name=command.connection_name,
            is_default=command.is_default,
            auth_type=command.auth_type,
            status=status,
            scopes=list(command.scopes),
            expires_at=command.credentials.expires_at if command.credentials else None,
            health=health or {},
            has_credentials=True,
            created_at=now,
            updated_at=now,
        )

    def connect(self, command: IntegrationConnectionCreate):
        return self._record(command, status=IntegrationConnectionStatus.live, health={"connected": True})

    def authenticate(self, command: IntegrationConnectionCreate):
        return self._record(command, status=IntegrationConnectionStatus.live, health={"authenticated": True})

    def validate(self, connection, *, credentials=None):
        return connection.model_copy(update={"status": IntegrationConnectionStatus.live, "health": {**connection.health, "validated": True}})

    def execute(self, request: IntegrationExecutionRequest, *, credentials=None) -> IntegrationExecutionResult:
        now = datetime.now(tz=UTC)
        if request.operation == IntegrationOperationType.search_accounts:
            payload = {
                "records": [
                    IntegrationAccountRecord(
                        provider_account_id="acct-1",
                        name="Acme",
                        domain="acme.test",
                        website="https://acme.test",
                        confidence_score=95,
                        metadata={"source": "fake"},
                    ).model_dump(mode="json")
                ]
            }
            status = IntegrationExecutionStatus.completed
        elif request.operation == IntegrationOperationType.enrich_contacts:
            payload = {
                "records": [
                    {
                        "provider_contact_id": "contact-1",
                        "provider_account_id": "acct-1",
                        "full_name": "Ada Lovelace",
                        "email": "ada@acme.test",
                        "title": "VP Sales",
                        "confidence_score": 90,
                        "metadata": {"source": "fake"},
                    }
                ]
            }
            status = IntegrationExecutionStatus.completed
        else:
            payload = {}
            status = IntegrationExecutionStatus.completed
        return IntegrationExecutionResult(
            provider=self.name,
            operation=request.operation,
            status=status,
            response_payload=payload,
            response_metadata={"provider": self.name, "operation": request.operation.value},
            counts={"record_count": len(payload.get("records", []))},
            error_message=None,
            trace_id=request.trace_id,
            correlation_id=request.correlation_id,
            started_at=now,
            finished_at=now,
            duration_ms=0,
        )

    def sync(self, request, *, credentials=None) -> IntegrationSyncResult:
        now = datetime.now(tz=UTC)
        return IntegrationSyncResult(
            provider=self.name,
            source_provider=self.name,
            status=IntegrationSyncStatus.completed,
            sync_cursor=request.sync_cursor,
            source_record_id="sync-1",
            ingestion_timestamp=now,
            response_payload={"source_record_id": "sync-1", "records": []},
            response_metadata={"provider": self.name},
            error_message=None,
            trace_id=request.trace_id,
            correlation_id=request.correlation_id,
            started_at=now,
            finished_at=now,
            duration_ms=0,
        )

    def disconnect(self, connection):
        return connection.model_copy(update={"status": IntegrationConnectionStatus.not_configured, "has_credentials": False})

    def health_check(self, connection, *, credentials=None):
        return connection.model_copy(update={"status": IntegrationConnectionStatus.live, "health": {**connection.health, "health_check": "ok"}})


class FlakyProvider(FakeApolloProvider):
    def __init__(self, *, failures_before_success: int = 1):
        self.failures_before_success = failures_before_success
        self.calls = 0

    def execute(self, request: IntegrationExecutionRequest, *, credentials=None) -> IntegrationExecutionResult:
        self.calls += 1
        if self.calls <= self.failures_before_success:
            raise IntegrationProviderUnavailableError("temporary provider outage")
        return super().execute(request, credentials=credentials)


class SyncPagingProvider(FakeApolloProvider):
    def sync(self, request, *, credentials=None) -> IntegrationSyncResult:
        now = datetime.now(tz=UTC)
        page = int(request.sync_cursor.get("page", 1))
        if page == 99:
            return IntegrationSyncResult(
                provider=self.name,
                source_provider=self.name,
                status=IntegrationSyncStatus.failed,
                sync_cursor=request.sync_cursor,
                response_payload={},
                response_metadata={"provider": self.name, "page": page},
                error_message="sync failed",
                trace_id=request.trace_id,
                correlation_id=request.correlation_id,
                started_at=now,
                finished_at=now,
                duration_ms=0,
            )
        next_page = page + 1
        source_id = f"acct-{page}"
        return IntegrationSyncResult(
            provider=self.name,
            source_provider=self.name,
            status=IntegrationSyncStatus.completed,
            sync_cursor={"page": next_page},
            source_record_id=source_id,
            ingestion_timestamp=now,
            response_payload={
                "source_record_id": source_id,
                "records": [
                    {
                        "provider_account_id": source_id,
                        "name": f"Account {page}",
                        "confidence_score": 90,
                    }
                ],
                "next_cursor": {"page": next_page},
            },
            response_metadata={"provider": self.name, "page": page},
            error_message=None,
            trace_id=request.trace_id,
            correlation_id=request.correlation_id,
            started_at=now,
            finished_at=now,
            duration_ms=0,
        )


class CaptureAuditService:
    def __init__(self) -> None:
        self.records: list[tuple[TenantContext, object]] = []

    def record(self, context, event):
        self.records.append((context, event))


class AlternateProvider(FakeApolloProvider):
    name = "alternate"


class WorkflowWorkerRepo:
    def __init__(self) -> None:
        self.updates: list[dict] = []

    def update_workflow_run_status(self, *, tenant_id: str, workflow_run_id: str, status: str, output: dict | None = None, heartbeat: bool = False):
        self.updates.append({
            "tenant_id": tenant_id,
            "workflow_run_id": workflow_run_id,
            "status": status,
            "output": output or {},
            "heartbeat": heartbeat,
        })
        return None


class ProvenanceCaptureRepo:
    def __init__(self) -> None:
        self.hypotheses: list[dict] = []
        self.drafts: list[dict] = []

    def persist_hypothesis(self, *, tenant_id: str, workflow_run_id: str, account_id: str, contact_id: str | None, title: str, hypothesis: str, confidence_score: float, metadata: dict, generated_by_agent: str):
        self.hypotheses.append({"tenant_id": tenant_id, "workflow_run_id": workflow_run_id, "metadata": metadata})
        return f"hyp-{len(self.hypotheses)}"

    def persist_outreach_draft(self, *, tenant_id: str, workflow_run_id: str, account_id: str, contact_id: str | None, subject: str, body: str, status: str, metadata: dict, generated_by_agent: str):
        self.drafts.append({"tenant_id": tenant_id, "workflow_run_id": workflow_run_id, "metadata": metadata})
        return f"draft-{len(self.drafts)}"


class AlternateProvider(FakeApolloProvider):
    name = "alternate"


class FakeIntegrationService:
    def search_accounts(self, context, **kwargs):
        return IntegrationSearchAccountsOutput(
            status=IntegrationExecutionStatus.completed,
            provider="apollo",
            records=[
                IntegrationAccountRecord(
                    provider_account_id="acct-1",
                    name="Acme",
                    domain="acme.test",
                    website="https://acme.test",
                    confidence_score=95,
                    metadata={"source": "fake"},
                )
            ],
            response_metadata={"provider": "apollo"},
        )

    def enrich_contacts(self, context, **kwargs):
        return IntegrationEnrichContactsOutput(
            status=IntegrationExecutionStatus.completed,
            provider="apollo",
            records=[],
            response_metadata={"provider": "apollo"},
        )

    def discover_signals(self, context, **kwargs):
        return IntegrationDiscoverSignalsOutput(
            status=IntegrationExecutionStatus.completed,
            provider="apollo",
            records=[
                IntegrationSignalRecord(
                    provider_signal_id="sig-1",
                    provider_account_id="acct-1",
                    signal_type="job_change",
                    strength=88,
                    source="apollo",
                    observed_at=datetime.now(tz=UTC).isoformat(),
                    metadata={"source": "fake"},
                )
            ],
            response_metadata={"provider": "apollo"},
        )


def build_service(session: Session, *, registry: IntegrationProviderRegistry | None = None, audit_service=None) -> IntegrationService:
    registry = registry or IntegrationProviderRegistry([FakeApolloProvider()])
    settings = Settings.from_env()
    return IntegrationService(repository=SqlIntegrationRepository(session), registry=registry, audit_service=audit_service, settings=settings)


def test_provider_registry_uses_first_registered_provider():
    registry = IntegrationProviderRegistry([AlternateProvider(), FakeApolloProvider()])
    assert registry.default().name == "alternate"
    assert registry.get("apollo").name == "apollo"


def test_integration_service_persists_connection_runs_and_scopes_tenant(db):
    with db.begin() as connection:
        tenant_a = create_tenant(connection, "tenant-a")
        tenant_b = create_tenant(connection, "tenant-b")

    session = Session(db)
    try:
        service = build_service(session)
        context = TenantContext(tenant_id=tenant_a, actor_user_id="user-a", roles=("seller",), permissions=("prospect:write",))
        connection_record = service.connect(
            context,
            IntegrationConnectionCreate(
                tenant_id=tenant_a,
                provider="apollo",
                connection_name="default",
                is_default=True,
                auth_type=IntegrationAuthType.api_key,
                credentials=IntegrationCredentials(auth_type=IntegrationAuthType.api_key, api_key="secret-key"),
            ),
        )
        assert connection_record.tenant_id == tenant_a
        assert connection_record.status == IntegrationConnectionStatus.live

        response = service.search_accounts(context, query="acme", limit=5, workflow_run_id="wf-1")
        assert response.status == IntegrationExecutionStatus.completed
        assert response.source_provider == "apollo"
        assert response.source_type == "imported"
        assert response.source_record_id == "acct-1"
        assert response.ingestion_timestamp is not None
        assert response.records[0].name == "Acme"

        sync = service.sync(context, source_type="accounts", cursor_name="accounts", sync_cursor={"page": 1}, workflow_run_id="wf-1")
        assert sync.status == IntegrationSyncStatus.completed
        assert sync.source_provider == "apollo"
        assert sync.source_record_id == "acct-1"
        assert sync.ingestion_timestamp is not None
        cursor = service._repository.get_sync_cursor(tenant_id=tenant_a, connection_id=connection_record.id, cursor_name="accounts")
        assert cursor is not None
        assert cursor.source_provider == "apollo"
        assert cursor.source_record_id == "sync-1"
        assert cursor.ingestion_timestamp is not None

        assert service.list_connections(context)
        assert service.list_connections(TenantContext(tenant_id=tenant_b, actor_user_id="user-b", roles=(), permissions=())) == []

        session.commit()
        with db.connect() as connection:
            run_count = connection.execute(
                text("select count(*) from integration_runs where tenant_id = :tenant_id"),
                {"tenant_id": tenant_a},
            ).scalar_one()
            assert run_count >= 2
    finally:
        session.close()


def test_apollo_provider_parses_transport_and_rate_limits():
    def transport(method: str, url: str, headers: dict[str, str], payload: dict | None, timeout: int):
        if url.endswith("/v1/auth/health"):
            return 200, {"ok": True}
        if url.endswith("/v1/mixed_companies/search"):
            return 200, {
                "organizations": [
                    {
                        "id": "org-1",
                        "name": "Acme",
                        "domain": "acme.test",
                        "website_url": "https://acme.test",
                        "relevance_score": 99,
                    }
                ]
            }
        if url.endswith("/v1/mixed_people/search"):
            return 429, {"error": "rate limited"}
        return 200, {}

    provider = ApolloIntegrationProvider(
        api_key="secret",
        base_url="https://api.apollo.io",
        allowed_hosts=("api.apollo.io",),
        transport=transport,
    )
    connection = provider.connect(
        IntegrationConnectionCreate(
            tenant_id="tenant-a",
            provider="apollo",
            connection_name="default",
            is_default=True,
            auth_type=IntegrationAuthType.api_key,
            credentials=IntegrationCredentials(auth_type=IntegrationAuthType.api_key, api_key="secret"),
        )
    )
    assert connection.status == IntegrationConnectionStatus.live

    result = provider.execute(
        IntegrationExecutionRequest(
            tenant_id="tenant-a",
            connection_id="conn-1",
            provider="apollo",
            operation=IntegrationOperationType.search_accounts,
            input={"query": "acme", "limit": 1},
        ),
        credentials=IntegrationCredentials(auth_type=IntegrationAuthType.api_key, api_key="secret"),
    )
    assert result.status == IntegrationExecutionStatus.completed
    assert result.response_payload["records"][0]["name"] == "Acme"

    rate_limited = provider.execute(
        IntegrationExecutionRequest(
            tenant_id="tenant-a",
            connection_id="conn-1",
            provider="apollo",
            operation=IntegrationOperationType.enrich_contacts,
            input={"account_ids": ["org-1"], "limit": 1},
        ),
        credentials=IntegrationCredentials(auth_type=IntegrationAuthType.api_key, api_key="secret"),
    )
    assert rate_limited.status == IntegrationExecutionStatus.rate_limited


def test_apollo_provider_auth_handlers_and_scope_validation():
    def transport(method: str, url: str, headers: dict[str, str], payload: dict | None, timeout: int):
        return 200, {"ok": True}

    provider = ApolloIntegrationProvider(
        api_key="secret",
        base_url="https://api.apollo.io",
        allowed_hosts=("api.apollo.io",),
        transport=transport,
    )
    expired = IntegrationConnectionCreate(
        tenant_id="tenant-a",
        provider="apollo",
        connection_name="oauth",
        is_default=True,
        auth_type=IntegrationAuthType.oauth2,
        credentials=IntegrationCredentials(
            auth_type=IntegrationAuthType.oauth2,
            access_token="old-token",
            refresh_token="refresh-token",
            scopes=["accounts.read", "contacts.read"],
            expires_at=datetime.now(tz=UTC) - timedelta(minutes=5),
        ),
    )
    connection = provider.authenticate(expired)
    assert connection.status == IntegrationConnectionStatus.live

    manual = provider.authenticate(
        IntegrationConnectionCreate(
            tenant_id="tenant-a",
            provider="apollo",
            connection_name="manual",
            is_default=False,
            auth_type=IntegrationAuthType.manual_config,
            credentials=IntegrationCredentials(auth_type=IntegrationAuthType.manual_config, api_key="manual-key"),
        )
    )
    assert manual.status == IntegrationConnectionStatus.live

    with pytest.raises(IntegrationValidationError):
        provider.authenticate(
            IntegrationConnectionCreate(
                tenant_id="tenant-a",
                provider="apollo",
                connection_name="missing-scope",
                is_default=False,
                auth_type=IntegrationAuthType.oauth2,
                credentials=IntegrationCredentials(
                    auth_type=IntegrationAuthType.oauth2,
                    access_token="token",
                    refresh_token="refresh-token",
                    scopes=["accounts.read"],
                ),
            )
        )

    with pytest.raises(IntegrationAuthenticationError):
        provider.authenticate(
            IntegrationConnectionCreate(
                tenant_id="tenant-a",
                provider="apollo",
                connection_name="missing-token",
                is_default=False,
                auth_type=IntegrationAuthType.oauth2,
                credentials=IntegrationCredentials(
                    auth_type=IntegrationAuthType.oauth2,
                    refresh_token="refresh-token",
                    scopes=["accounts.read", "contacts.read"],
                ),
            )
        )


def test_integration_service_retries_then_succeeds_and_opens_circuit(db):
    with db.begin() as connection:
        tenant_id = create_tenant(connection, "tenant-c")

    session = Session(db)
    try:
        provider = FlakyProvider(failures_before_success=1)
        service = build_service(session, registry=IntegrationProviderRegistry([provider]))
        service._retry_max_attempts = 2
        service._retry_backoff_ms = 0
        service._circuit_breaker_threshold = 1
        service._circuit_breaker_open_seconds = 30
        context = TenantContext(tenant_id=tenant_id, actor_user_id="user-c", roles=("seller",), permissions=("prospect:write",))
        service.connect(
            context,
            IntegrationConnectionCreate(
                tenant_id=tenant_id,
                provider="apollo",
                connection_name="default",
                is_default=True,
                auth_type=IntegrationAuthType.api_key,
                credentials=IntegrationCredentials(auth_type=IntegrationAuthType.api_key, api_key="secret-key"),
            ),
        )

        result = service.search_accounts(context, query="acme", limit=1, trace_id="trace-1", correlation_id="corr-1", workflow_run_id="wf-2")
        assert result.status == IntegrationExecutionStatus.completed
        assert provider.calls == 2
        connection_record = service.get_connection(context, service.list_connections(context)[0].id)
        assert connection_record is not None
        assert connection_record.health.get("circuit_state") == "closed"

        failing_provider = FlakyProvider(failures_before_success=10)
        service = build_service(session, registry=IntegrationProviderRegistry([failing_provider]))
        service._retry_max_attempts = 1
        service._retry_backoff_ms = 0
        service._circuit_breaker_threshold = 1
        service._circuit_breaker_open_seconds = 30
        service.connect(
            context,
            IntegrationConnectionCreate(
                tenant_id=tenant_id,
                provider="apollo",
                connection_name="secondary",
                is_default=True,
                auth_type=IntegrationAuthType.api_key,
                credentials=IntegrationCredentials(auth_type=IntegrationAuthType.api_key, api_key="secret-key"),
            ),
        )
        first_failure = service.search_accounts(context, query="acme", limit=1)
        assert first_failure.status == IntegrationExecutionStatus.failed
        failed_connection = service.list_connections(context)[0]
        assert failed_connection.health.get("circuit_state") == "open"
        service._repository.update_connection(
            tenant_id=tenant_id,
            connection_id=failed_connection.id,
            update=IntegrationConnectionUpdate(health={**failed_connection.health, "open_until": (datetime.now(tz=UTC) - timedelta(seconds=1)).isoformat()}),
        )
        failing_provider.failures_before_success = 0
        half_open = service.search_accounts(context, query="acme", limit=1)
        assert half_open.status == IntegrationExecutionStatus.completed
    finally:
        session.close()


def test_sync_success_resume_and_failure(db):
    with db.begin() as connection:
        tenant_id = create_tenant(connection, "tenant-d")

    session = Session(db)
    try:
        service = build_service(session, registry=IntegrationProviderRegistry([SyncPagingProvider()]))
        context = TenantContext(tenant_id=tenant_id, actor_user_id="user-d", roles=("seller",), permissions=("prospect:write",))
        connection_record = service.connect(
            context,
            IntegrationConnectionCreate(
                tenant_id=tenant_id,
                provider="apollo",
                connection_name="default",
                is_default=True,
                auth_type=IntegrationAuthType.api_key,
                credentials=IntegrationCredentials(auth_type=IntegrationAuthType.api_key, api_key="secret-key"),
            ),
        )
        first = service.sync(context, connection_id=connection_record.id, source_type="accounts", cursor_name="accounts", sync_cursor={"page": 1}, workflow_run_id="wf-sync")
        assert first.status == IntegrationSyncStatus.completed
        assert first.sync_cursor == {"page": 2}
        cursor = service._repository.get_sync_cursor(tenant_id=tenant_id, connection_id=connection_record.id, cursor_name="accounts")
        assert cursor is not None
        assert cursor.source_record_id == "acct-1"
        assert cursor.source_provider == "apollo"
        assert cursor.ingestion_timestamp is not None

        resumed = service.sync(context, connection_id=connection_record.id, source_type="accounts", cursor_name="accounts", sync_cursor=first.sync_cursor, workflow_run_id="wf-sync")
        assert resumed.status == IntegrationSyncStatus.completed
        assert resumed.sync_cursor == {"page": 3}

        failed = service.sync(context, connection_id=connection_record.id, source_type="accounts", cursor_name="accounts", sync_cursor={"page": 99}, workflow_run_id="wf-sync")
        assert failed.status == IntegrationSyncStatus.failed
    finally:
        session.close()


def test_integration_service_emits_trace_and_actor_metadata(db):
    with db.begin() as connection:
        tenant_id = create_tenant(connection, "tenant-e")

    session = Session(db)
    audit = CaptureAuditService()
    try:
        service = build_service(session, audit_service=audit)
        context = TenantContext(tenant_id=tenant_id, actor_user_id="agent-user", roles=("seller",), permissions=("prospect:write",))
        set_tenant_context(context)
        service.connect(
            context,
            IntegrationConnectionCreate(
                tenant_id=tenant_id,
                provider="apollo",
                connection_name="default",
                is_default=True,
                auth_type=IntegrationAuthType.api_key,
                credentials=IntegrationCredentials(auth_type=IntegrationAuthType.api_key, api_key="secret-key"),
            ),
        )
        service.search_accounts(context, query="acme", limit=1, trace_id="trace-abc", correlation_id="corr-xyz", workflow_run_id="wf-99")
        assert audit.records
        recorded_context, event = audit.records[-1]
        assert recorded_context.actor_user_id == "agent-user"
        assert event.metadata["trace_id"] == "trace-abc"
        assert event.metadata["correlation_id"] == "corr-xyz"
        assert event.metadata["workflow_run_id"] == "wf-99"
    finally:
        session.close()


def test_prospect_research_uses_provider_accounts_tool():
    class FakeResearchRepo:
        def get_icp(self, *, tenant_id: str, icp_id: str | None):
            return None

        def list_accounts_for_research(self, *, tenant_id: str, limit: int):
            return []

        def list_contacts_by_account_ids(self, *, tenant_id: str, account_ids: list[str]):
            return []

        def list_signals_by_account_ids(self, *, tenant_id: str, account_ids: list[str]):
            return []

        def get_workflow_run(self, *, tenant_id: str, workflow_run_id: str):
            return None

        def get_workflow_run_by_idempotency(self, *, tenant_id: str, idempotency_key: str):
            return None

        def create_workflow_run(self, command):
            raise NotImplementedError

        def update_workflow_run_status(self, **kwargs):
            raise NotImplementedError

        def record_workflow_step(self, **kwargs):
            raise NotImplementedError

        def record_tool_call(self, **kwargs):
            raise NotImplementedError

        def create_approval_checkpoint(self, **kwargs):
            raise NotImplementedError

        def get_approval_checkpoint(self, **kwargs):
            raise NotImplementedError

        def update_approval_checkpoint(self, **kwargs):
            raise NotImplementedError

        def persist_hypothesis(self, **kwargs):
            raise NotImplementedError

        def persist_outreach_draft(self, **kwargs):
            raise NotImplementedError

        def record_llm_usage(self, **kwargs):
            raise NotImplementedError

        def count_value_hypotheses(self, **kwargs):
            return 0

        def count_outreach_drafts(self, **kwargs):
            return 0

        def count_workflow_steps(self, **kwargs):
            return 0

        def count_tool_calls(self, **kwargs):
            return 0

        def count_llm_usage(self, **kwargs):
            return 0.0, 0

    tools = DefaultProspectAgentTools(FakeResearchRepo(), integration_service=FakeIntegrationService())
    llm = ScriptedLLM(
        [
            LLMCompletion(tool_calls=[LLMToolCall(name="search_provider_accounts", arguments={"limit": 1, "query": "acme"})]),
            LLMCompletion(content='{"reasoning_summary":"Used provider accounts for ranking.","output":{"ranked_accounts":[{"account_id":"acct-1","rank_score":95,"reasoning_summary":"Provider-backed fit"}]}}'),
        ]
    )
    agent = ProspectResearchAgent(tools, llm)
    set_tenant_context(TenantContext(tenant_id="tenant-a", actor_user_id="user-a", roles=("seller",), permissions=("prospect:write",)))
    output = agent.run(
        ProspectResearchInput(tenant_id="tenant-a", workflow_run_id="wf-1", account_limit=5),
        context=AgentExecutionContext(tenant_id="tenant-a", workflow_run_id="wf-1", current_step="research"),
    )
    assert output.trace.status == JobStatus.completed
    assert output.ranked_accounts[0].account_id == "acct-1"


def test_workflow_worker_retry_cancellation_queue_limits_and_watchdog():
    settings = replace(
        Settings.from_env(),
        workflow_queue_threshold=1,
        workflow_concurrent_limit=1,
        workflow_retry_max_attempts=2,
        workflow_inline_execution=True,
        workflow_job_timeout_seconds=1,
        workflow_redis_url=None,
    )
    context = TenantContext(tenant_id="tenant-worker", actor_user_id="worker-user", roles=("seller",), permissions=("prospect:write",))
    repo = WorkflowWorkerRepo()
    worker = ProspectWorkflowWorker(repo, backend=InMemoryWorkflowQueueBackend(), settings=settings)
    state = ProspectWorkflowExecutionState(
        tenant_id="tenant-worker",
        workflow_run_id="wf-worker-1",
        workflow_type="prospect",
        idempotency_key="wf-worker-1",
        status=WorkflowStatus.queued,
        current_step="research",
        source_provider="prospect-workflow",
        source_type="generated",
        source_record_id="wf-worker-1",
        ingestion_timestamp=datetime.now(tz=UTC),
    )

    attempts = {"count": 0}

    def flaky(execution_state, *, context):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient")
        return execution_state.model_copy(update={"status": WorkflowStatus.succeeded, "current_step": "completed"})

    result = worker.run_inline(state, context=context, execute=flaky)
    assert result.status == WorkflowStatus.succeeded
    assert result.retry_count == 1
    assert len(result.attempt_metadata) == 1

    cancel_worker = ProspectWorkflowWorker(
        repo,
        backend=InMemoryWorkflowQueueBackend(),
        settings=replace(settings, workflow_inline_execution=False),
    )
    cancel_state = state.model_copy(update={"workflow_run_id": "wf-worker-cancel", "idempotency_key": "wf-worker-cancel"})
    cancel_worker.submit(cancel_state, context)
    cancelled = cancel_worker.cancel(tenant_id="tenant-worker", workflow_run_id="wf-worker-cancel")
    assert cancelled is not None
    assert cancelled.status == WorkflowStatus.cancelled

    queue_limit_worker = ProspectWorkflowWorker(
        repo,
        backend=InMemoryWorkflowQueueBackend(),
        settings=replace(settings, workflow_inline_execution=False, workflow_queue_threshold=1),
    )
    queue_limit_worker.submit(state.model_copy(update={"workflow_run_id": "wf-worker-q1", "idempotency_key": "wf-worker-q1"}), context)
    with pytest.raises(WorkflowQueueFullError):
        queue_limit_worker.submit(state.model_copy(update={"workflow_run_id": "wf-worker-q2", "idempotency_key": "wf-worker-q2"}), context)

    watchdog_worker = ProspectWorkflowWorker(
        repo,
        backend=InMemoryWorkflowQueueBackend(),
        settings=replace(settings, workflow_inline_execution=False, workflow_job_timeout_seconds=1),
    )
    watchdog_worker.submit(state.model_copy(update={"workflow_run_id": "wf-worker-timeout", "idempotency_key": "wf-worker-timeout"}), context)
    job = watchdog_worker._backend.pop()
    assert job is not None
    job.status = WorkflowStatus.running
    old = datetime.now(tz=UTC) - timedelta(seconds=10)
    job.started_at = old
    job.last_heartbeat_at = old
    watchdog_worker._backend.update(job)
    timed_out = watchdog_worker.watchdog(timeout_seconds=1)
    assert len(timed_out) == 1
    assert timed_out[0].status == WorkflowStatus.timed_out
    assert repo.updates[-1]["status"] == WorkflowStatus.timed_out.value


def test_provenance_persists_in_workflow_and_generated_artifacts():
    settings = replace(Settings.from_env(), workflow_inline_execution=True, workflow_retry_max_attempts=1, workflow_redis_url=None)
    repo = WorkflowWorkerRepo()
    worker = ProspectWorkflowWorker(repo, backend=InMemoryWorkflowQueueBackend(), settings=settings)
    context = TenantContext(tenant_id="tenant-provenance", actor_user_id="prov-user", roles=("seller",), permissions=("prospect:write",))
    state = ProspectWorkflowExecutionState(
        tenant_id="tenant-provenance",
        workflow_run_id="wf-provenance",
        workflow_type="prospect",
        idempotency_key="wf-provenance",
        status=WorkflowStatus.queued,
        current_step="research",
        source_provider="prospect-workflow",
        source_type="generated",
        source_record_id="wf-provenance",
        ingestion_timestamp=datetime.now(tz=UTC),
    )

    def succeed(execution_state, *, context):
        return execution_state.model_copy(update={"status": WorkflowStatus.succeeded, "current_step": "completed"})

    result = worker.run_inline(state, context=context, execute=succeed)
    assert result.source_provider == "prospect-workflow"
    assert result.source_type == "generated"
    assert result.source_record_id == "wf-provenance"
    assert result.ingestion_timestamp is not None
    persisted = repo.updates[-1]["output"]
    assert persisted["source_provider"] == "prospect-workflow"
    assert persisted["source_type"] == "generated"
    assert persisted["source_record_id"] == "wf-provenance"
    assert persisted["ingestion_timestamp"] is not None
    assert persisted["retry_count"] == 0

    artifact_repo = ProvenanceCaptureRepo()
    tools = DefaultProspectAgentTools(artifact_repo, integration_service=FakeIntegrationService())
    tools.save_hypotheses(
        tenant_id="tenant-provenance",
        workflow_run_id="wf-provenance",
        drafts=[
            ValueHypothesisDraft(
                account_id="acct-1",
                title="Example hypothesis",
                hypothesis="The account is a fit.",
                supporting_evidence=["signal-1"],
                confidence_score=88,
            )
        ],
        generated_by_agent="value_hypothesis",
    )
    tools.save_outreach_drafts(
        tenant_id="tenant-provenance",
        workflow_run_id="wf-provenance",
        drafts=[
            OutreachDraftProposal(
                account_id="acct-1",
                subject="Example outreach",
                body="Hi there",
                status=OutreachDraftStatus.pending_approval,
                review_notes="review before send",
            )
        ],
        generated_by_agent="outreach",
    )
    assert artifact_repo.hypotheses[0]["metadata"]["source_provider"] == "prospect-workflow"
    assert artifact_repo.hypotheses[0]["metadata"]["source_type"] == "generated"
    assert artifact_repo.hypotheses[0]["metadata"]["source_record_id"] == "wf-provenance"
    assert artifact_repo.drafts[0]["metadata"]["source_provider"] == "prospect-workflow"
    assert artifact_repo.drafts[0]["metadata"]["source_type"] == "generated"


def test_provider_registry_is_settings_driven_and_swappable(db):
    with db.begin() as connection:
        tenant_id = create_tenant(connection, "tenant-swappable")

    session = Session(db)
    try:
        registry = IntegrationProviderRegistry([AlternateProvider()])
        assert registry.default().name == "alternate"
        service = build_service(session, registry=registry)
        context = TenantContext(tenant_id=tenant_id, actor_user_id="swap-user", roles=("seller",), permissions=("prospect:write",))
        service.connect(
            context,
            IntegrationConnectionCreate(
                tenant_id=tenant_id,
                provider="alternate",
                connection_name="default",
                is_default=True,
                auth_type=IntegrationAuthType.api_key,
                credentials=IntegrationCredentials(auth_type=IntegrationAuthType.api_key, api_key="secret-key"),
            ),
        )
        result = service.search_accounts(context, provider="alternate", query="acme", limit=1, workflow_run_id="wf-swap")
        assert result.provider == "alternate"
        assert result.source_provider == "alternate"
    finally:
        session.close()


def test_negative_tenant_and_context_and_trace_regressions(db):
    with db.begin() as connection:
        tenant_id = create_tenant(connection, "tenant-negative")
        other_tenant_id = create_tenant(connection, "tenant-negative-2")

    session = Session(db)
    try:
        service = build_service(session)
        context = TenantContext(tenant_id=tenant_id, actor_user_id="neg-user", roles=("seller",), permissions=("prospect:write",))
        other_context = TenantContext(tenant_id=other_tenant_id, actor_user_id="other-user", roles=("seller",), permissions=("prospect:write",))
        with pytest.raises(PermissionError):
            service.connect(
                other_context,
                IntegrationConnectionCreate(
                    tenant_id=tenant_id,
                    provider="apollo",
                    connection_name="default",
                    is_default=True,
                    auth_type=IntegrationAuthType.api_key,
                    credentials=IntegrationCredentials(auth_type=IntegrationAuthType.api_key, api_key="secret-key"),
                ),
            )

        tools = DefaultProspectAgentTools(ProvenanceCaptureRepo(), integration_service=FakeIntegrationService())
        token = tenant_context_var.set(None)
        try:
            with pytest.raises(RuntimeError):
                tools.search_provider_accounts(tenant_id=tenant_id, workflow_run_id="wf-negative", query="acme", limit=1)
        finally:
            tenant_context_var.reset(token)

        runtime = ObservabilityRuntime()
        payload = runtime.emit_operation(service="test.service", status="ok", duration_ms=0, tenant_id=tenant_id, workflow_id="wf-negative")
        assert payload["trace_id"]
        assert payload["correlation_id"]
        assert payload["duration_ms"] >= 1

        audit = CaptureAuditService()
        service = build_service(session, audit_service=audit)
        service.connect(
            context,
            IntegrationConnectionCreate(
                tenant_id=tenant_id,
                provider="apollo",
                connection_name="default",
                is_default=True,
                auth_type=IntegrationAuthType.api_key,
                credentials=IntegrationCredentials(auth_type=IntegrationAuthType.api_key, api_key="secret-key"),
            ),
        )
        service.search_accounts(context, query="acme", limit=1, trace_id="trace-neg", correlation_id="corr-neg", workflow_run_id="wf-neg")
        assert audit.records
        recorded_context, event = audit.records[-1]
        assert recorded_context.tenant_id == tenant_id
        assert event.resource_type == "integration"
        assert event.actor_user_id == "neg-user"
        assert event.metadata["trace_id"] == "trace-neg"
        assert event.metadata["correlation_id"] == "corr-neg"
        assert event.metadata["workflow_run_id"] == "wf-neg"
    finally:
        session.close()

