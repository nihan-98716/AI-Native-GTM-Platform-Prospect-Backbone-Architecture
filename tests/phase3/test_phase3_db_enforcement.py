import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.audit.service import AuditTenantMismatchError, SqlAuditService
from app.contracts.api.accounts import ListAccountsQuery
from app.contracts.events.audit import AuditEventCreate, AuditEventScoped
from app.core.tenancy import TenantContext
from app.repositories.account_repository import SqlAccountRepository
from app.repositories.audit_repository import SqlAuditEventRepository
from app.services.accounts import AccountsService


DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.fixture()
def engine():
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL is required for DB-backed phase 3 tests")
    created = create_engine(DATABASE_URL)
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture()
def db(engine):
    with engine.begin() as connection:
        for table_name in ["audit_events", "accounts", "users", "tenants"]:
            connection.execute(text(f"delete from {table_name}"))
    yield engine


def scalar(connection, statement, **params):
    return connection.execute(text(statement), params).scalar_one()


def create_tenant(connection, slug: str):
    return scalar(connection, "insert into tenants (name, slug) values (:name, :slug) returning id", name=slug, slug=slug)


def test_cross_tenant_audit_write_fails(db):
    with db.begin() as connection:
        tenant_a = create_tenant(connection, "audit-a")
        tenant_b = create_tenant(connection, "audit-b")

    session = Session(db)
    try:
        service = SqlAuditService(SqlAuditEventRepository(session))
        context = TenantContext(tenant_id=tenant_a, actor_user_id="u-a", roles=("admin",), permissions=("*:*",))
        with pytest.raises(AuditTenantMismatchError):
            service.record_scoped(
                context=context,
                event=AuditEventScoped(
                    tenant_id=tenant_b,
                    actor_user_id="u-a",
                    action="auth.login",
                    resource_type="session",
                ),
            )
    finally:
        session.rollback()
        session.close()


def test_audit_service_injects_tenant_from_context(db):
    with db.begin() as connection:
        tenant_a = create_tenant(connection, "audit-injected")

    session = Session(db)
    try:
        service = SqlAuditService(SqlAuditEventRepository(session))
        context = TenantContext(tenant_id=tenant_a, actor_user_id="u-a", roles=("admin",), permissions=("*:*",))
        result = service.record(
            context=context,
            event=AuditEventCreate(action="workflow.start", resource_type="workflow", resource_id=str(uuid4())),
        )
        session.commit()
        assert result.tenant_id == tenant_a
    finally:
        session.close()


def test_account_repository_is_tenant_scoped_and_returns_dtos(db):
    with db.begin() as connection:
        tenant_a = create_tenant(connection, "accounts-a")
        tenant_b = create_tenant(connection, "accounts-b")
        connection.execute(
            text(
                """
                insert into accounts (tenant_id, name, domain, lifecycle_stage)
                values (:tenant_id, 'A Co', :domain, 'prospect')
                """
            ),
            {"tenant_id": tenant_a, "domain": f"{uuid4()}.test"},
        )
        connection.execute(
            text(
                """
                insert into accounts (tenant_id, name, domain, lifecycle_stage)
                values (:tenant_id, 'B Co', :domain, 'prospect')
                """
            ),
            {"tenant_id": tenant_b, "domain": f"{uuid4()}.test"},
        )

    session = Session(db)
    try:
        repository = SqlAccountRepository(session)
        rows = repository.list_by_tenant(tenant_id=tenant_a, limit=10, offset=0)
        assert len(rows) == 1
        assert rows[0].tenant_id == tenant_a
        assert rows[0].name == "A Co"
    finally:
        session.close()


def test_accounts_service_uses_repository_dto_mapping(db):
    with db.begin() as connection:
        tenant = create_tenant(connection, "service-dto")
        connection.execute(
            text(
                """
                insert into accounts (tenant_id, name, domain, lifecycle_stage)
                values (:tenant_id, 'DTO Co', :domain, 'prospect')
                """
            ),
            {"tenant_id": tenant, "domain": f"{uuid4()}.test"},
        )

    session = Session(db)
    try:
        context = TenantContext(tenant_id=tenant, actor_user_id="u-1", roles=("seller",), permissions=("accounts:read",))
        service = AccountsService(SqlAccountRepository(session))
        response = service.list_accounts(context=context, query=ListAccountsQuery(limit=20, offset=0))
        assert response.count == 1
        assert response.items[0].name == "DTO Co"
        assert response.items[0].tenant_id == tenant
    finally:
        session.close()

