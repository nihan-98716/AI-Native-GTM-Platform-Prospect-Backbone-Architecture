from datetime import UTC, datetime, timedelta

import jwt

from app.audit.service import AuditTenantMismatchError, SqlAuditService
from app.auth.jwt import Hs256TokenVerifier
from app.auth.rbac import AuthorizationError, RbacAuthorizer
from app.contracts.api.accounts import ListAccountsQuery
from app.contracts.api.auth import TokenClaims
from app.contracts.events.audit import AuditEventCreate, AuditEventRecord, AuditEventScoped
from app.core.config import Settings
from app.core.tenancy import TenantContext
from app.observability.runtime import ObservabilityRuntime
from app.repositories.account_repository import SqlAccountRepository
from app.services.accounts import AccountsService


class RecordingTracer:
    def next_ids(self) -> tuple[str, str]:
        return ("trace-fixed", "corr-fixed")


class RecordingMeter:
    def __init__(self) -> None:
        self.increments: list[tuple[str, int, dict[str, str] | None]] = []
        self.timings: list[tuple[str, int, dict[str, str] | None]] = []

    def increment(self, name: str, *, value: int = 1, tags: dict[str, str] | None = None) -> None:
        self.increments.append((name, value, tags))

    def timing(self, name: str, duration_ms: int, *, tags: dict[str, str] | None = None) -> None:
        self.timings.append((name, duration_ms, tags))


class RecordingLogger:
    def __init__(self) -> None:
        self.info_logs: list[dict] = []
        self.error_logs: list[dict] = []

    def info(self, payload: dict) -> None:
        self.info_logs.append(payload)

    def error(self, payload: dict) -> None:
        self.error_logs.append(payload)


def make_runtime() -> tuple[ObservabilityRuntime, RecordingLogger]:
    logger = RecordingLogger()
    runtime = ObservabilityRuntime(tracer=RecordingTracer(), meter=RecordingMeter(), logger=logger)
    return runtime, logger


def build_settings() -> Settings:
    return Settings(
        app_name="gtm-backbone",
        environment="test",
        database_url="postgresql+psycopg://gtm:gtm@localhost:5432/gtm",
        jwt_secret="unit-test-secret-with-32-byte-minimum",
        jwt_audience="gtm-api",
        jwt_issuer="gtm-local",
        cors_origins=["http://localhost:3000"],
        rate_limit_per_minute=120,
        auto_seed_on_startup=False,
        seed_dir="..\\data",
    )


def build_token(settings: Settings) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "sub": "user-1",
        "tenant_id": "tenant-1",
        "roles": ["seller"],
        "permissions": ["accounts:read"],
        "aud": settings.jwt_audience,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeAccount:
    def __init__(self, *, id: str, tenant_id: str, name: str, domain: str, lifecycle_stage: str):
        self.id = id
        self.tenant_id = tenant_id
        self.name = name
        self.domain = domain
        self.lifecycle_stage = lifecycle_stage


class FakeAccountSession:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, _):
        return FakeResult(self._rows)


class FakeAuditRepository:
    def create(self, event: AuditEventScoped) -> AuditEventRecord:
        now = datetime.now(tz=UTC)
        return AuditEventRecord(
            id="audit-1",
            tenant_id=event.tenant_id,
            actor_user_id=event.actor_user_id,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            metadata=event.metadata,
            created_at=now,
        )


def test_observability_runtime_emits_required_fields():
    runtime, logger = make_runtime()
    payload = runtime.emit_operation(service="test.service", status="ok", duration_ms=4, tenant_id="t1")
    assert payload["trace_id"] == "trace-fixed"
    assert payload["correlation_id"] == "corr-fixed"
    assert payload["duration_ms"] == 4
    assert logger.info_logs


def test_auth_components_emit_observability():
    runtime, logger = make_runtime()
    settings = build_settings()
    verifier = Hs256TokenVerifier(settings=settings, observability=runtime)
    claims = verifier.verify(build_token(settings))
    authorizer = RbacAuthorizer(observability=runtime)
    authorizer.require(claims=claims, required_permission="accounts:read")
    assert any(item["service"] == "auth.jwt.verify" for item in logger.info_logs)
    assert any(item["service"] == "auth.rbac.require" for item in logger.info_logs)


def test_repository_and_service_emit_observability():
    runtime, logger = make_runtime()
    repo = SqlAccountRepository(
        FakeAccountSession(
            [FakeAccount(id="a1", tenant_id="t1", name="Acme", domain="acme.test", lifecycle_stage="prospect")]
        ),
        observability=runtime,
    )
    service = AccountsService(repo, observability=runtime)
    context = TenantContext(tenant_id="t1", actor_user_id="u1", roles=("seller",), permissions=("accounts:read",))
    response = service.list_accounts(context=context, query=ListAccountsQuery(limit=10, offset=0))
    assert response.count == 1
    assert any(item["service"] == "repositories.accounts.list_by_tenant" for item in logger.info_logs)
    assert any(item["service"] == "services.accounts.list_accounts" for item in logger.info_logs)


def test_audit_service_enforces_tenant_and_emits_error_log():
    runtime, logger = make_runtime()
    service = SqlAuditService(FakeAuditRepository(), observability=runtime)
    context = TenantContext(tenant_id="tenant-a", actor_user_id="user-a", roles=("admin",), permissions=("*:*",))
    try:
        service.record_scoped(
            context=context,
            event=AuditEventScoped(tenant_id="tenant-b", actor_user_id="user-a", action="a", resource_type="r"),
        )
    except AuditTenantMismatchError:
        pass
    assert any(item["service"] == "audit.record_scoped" for item in logger.error_logs)


def test_audit_service_records_with_context_tenant():
    runtime, logger = make_runtime()
    service = SqlAuditService(FakeAuditRepository(), observability=runtime)
    context = TenantContext(tenant_id="tenant-a", actor_user_id="user-a", roles=("admin",), permissions=("*:*",))
    result = service.record(context=context, event=AuditEventCreate(action="a", resource_type="r"))
    assert result.tenant_id == "tenant-a"
    assert any(item["service"] == "audit.record_scoped" for item in logger.info_logs)


def test_rbac_missing_permissions_emits_error():
    runtime, logger = make_runtime()
    authorizer = RbacAuthorizer(observability=runtime)
    claims = TokenClaims(sub="u1", tenant_id="t1", permissions=["signals:read"])
    try:
        authorizer.require(claims=claims, required_permission="accounts:read")
    except AuthorizationError:
        pass
    assert any(item["service"] == "auth.rbac.require" for item in logger.error_logs)

