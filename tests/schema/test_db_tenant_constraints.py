import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.fixture()
def engine():
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL is required for DB-backed schema tests")
    created = create_engine(DATABASE_URL)
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture()
def db(engine):
    with engine.begin() as connection:
        for table_name in [
            "outreach_drafts",
            "value_hypotheses",
            "llm_usage_records",
            "tool_calls",
            "approval_requests",
            "workflow_steps",
            "workflow_runs",
            "sync_cursors",
            "integration_runs",
            "integration_connections",
            "signals",
            "activities",
            "opportunities",
            "contacts",
            "icp_definitions",
            "personas",
            "accounts",
            "users",
            "tenants",
        ]:
            connection.execute(text(f"delete from {table_name}"))
    yield engine


def scalar(connection, statement, **params):
    return connection.execute(text(statement), params).scalar_one()


def create_tenant(connection, slug: str):
    return scalar(connection, "insert into tenants (name, slug) values (:name, :slug) returning id", name=slug, slug=slug)


def test_accounts_are_unique_per_tenant_not_globally(db):
    with db.begin() as connection:
        tenant_a = create_tenant(connection, "tenant-a")
        tenant_b = create_tenant(connection, "tenant-b")
        connection.execute(
            text("insert into accounts (tenant_id, name, domain, lifecycle_stage) values (:tenant_id, 'A', 'same.test', 'prospect')"),
            {"tenant_id": tenant_a},
        )
        connection.execute(
            text("insert into accounts (tenant_id, name, domain, lifecycle_stage) values (:tenant_id, 'B', 'same.test', 'prospect')"),
            {"tenant_id": tenant_b},
        )

    with pytest.raises(IntegrityError):
        with db.begin() as connection:
            connection.execute(
                text("insert into accounts (tenant_id, name, domain, lifecycle_stage) values ((select id from tenants where slug='tenant-a'), 'C', 'same.test', 'prospect')")
            )


def test_contacts_reject_cross_tenant_account_fk(db):
    with db.begin() as connection:
        tenant_a = create_tenant(connection, "contact-a")
        tenant_b = create_tenant(connection, "contact-b")
        account_a = scalar(
            connection,
            "insert into accounts (tenant_id, name, domain, lifecycle_stage) values (:tenant_id, 'A', :domain, 'prospect') returning id",
            tenant_id=tenant_a,
            domain=f"{uuid4()}.test",
        )

    with pytest.raises(IntegrityError):
        with db.begin() as connection:
            connection.execute(
                text(
                    """
                    insert into contacts (tenant_id, account_id, full_name, email)
                    values (:tenant_id, :account_id, 'Wrong Tenant', :email)
                    """
                ),
                {"tenant_id": tenant_b, "account_id": account_a, "email": f"{uuid4()}@example.com"},
            )


def test_workflow_runs_reject_cross_tenant_account_fk(db):
    with db.begin() as connection:
        tenant_a = create_tenant(connection, "workflow-a")
        tenant_b = create_tenant(connection, "workflow-b")
        account_a = scalar(
            connection,
            "insert into accounts (tenant_id, name, domain, lifecycle_stage) values (:tenant_id, 'A', :domain, 'prospect') returning id",
            tenant_id=tenant_a,
            domain=f"{uuid4()}.test",
        )

    with pytest.raises(IntegrityError):
        with db.begin() as connection:
            connection.execute(
                text(
                    """
                    insert into workflow_runs (tenant_id, workflow_type, status, account_id, idempotency_key)
                    values (:tenant_id, 'prospect', 'queued', :account_id, :key)
                    """
                ),
                {"tenant_id": tenant_b, "account_id": account_a, "key": str(uuid4())},
            )


def test_integration_connections_enforce_tenant_provider_connection_name(db):
    with db.begin() as connection:
        tenant_a = create_tenant(connection, "integration-a")
        tenant_b = create_tenant(connection, "integration-b")
        statement = text(
            """
            insert into integration_connections
              (tenant_id, provider, connection_name, is_default, auth_type, status)
            values (:tenant_id, 'apollo', 'default', false, 'api_key', 'not_configured')
            """
        )
        connection.execute(statement, {"tenant_id": tenant_a})
        connection.execute(statement, {"tenant_id": tenant_b})

    with pytest.raises(IntegrityError):
        with db.begin() as connection:
            connection.execute(statement, {"tenant_id": tenant_a})


def test_sync_cursors_are_unique_per_connection_and_name(db):
    with db.begin() as connection:
        tenant_id = create_tenant(connection, "cursor-a")
        connection_id = scalar(
            connection,
            """
            insert into integration_connections
              (tenant_id, provider, connection_name, is_default, auth_type, status)
            values (:tenant_id, 'apollo', 'default', true, 'api_key', 'live')
            returning id
            """,
            tenant_id=tenant_id,
        )
        connection.execute(
            text(
                """
                insert into sync_cursors (tenant_id, connection_id, provider, cursor_name)
                values (:tenant_id, :connection_id, 'apollo', 'people')
                """
            ),
            {"tenant_id": tenant_id, "connection_id": connection_id},
        )

    with pytest.raises(IntegrityError):
        with db.begin() as connection:
            connection.execute(
                text(
                    """
                    insert into sync_cursors (tenant_id, connection_id, provider, cursor_name)
                    values (:tenant_id, :connection_id, 'apollo', 'people')
                    """
                ),
                {"tenant_id": tenant_id, "connection_id": connection_id},
            )
