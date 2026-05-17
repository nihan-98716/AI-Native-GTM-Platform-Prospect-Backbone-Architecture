from sqlalchemy.dialects import postgresql

from app.repositories.account_repository import SqlAccountRepository


def test_account_repository_query_contains_tenant_filter():
    tenant_id = "11111111-1111-1111-1111-111111111111"
    stmt = SqlAccountRepository.build_query(
        tenant_id=tenant_id,
        limit=10,
        offset=0,
    )
    sql = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "accounts.tenant_id" in sql
    assert tenant_id.replace("-", "") in sql

