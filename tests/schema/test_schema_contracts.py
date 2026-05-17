import sys
from pathlib import Path

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

sys.path.append(str(Path(__file__).resolve().parents[2] / "backbone"))

from app.models import Base  # noqa: E402


TENANT_OWNED_TABLES = {
    "users",
    "accounts",
    "contacts",
    "opportunities",
    "activities",
    "signals",
    "icp_definitions",
    "personas",
    "custom_field_definitions",
    "integration_connections",
    "integration_runs",
    "sync_cursors",
    "workflow_runs",
    "workflow_steps",
    "approval_requests",
    "tool_calls",
    "idempotency_keys",
    "llm_usage_records",
    "audit_events",
    "value_hypotheses",
    "outreach_drafts",
}

TENANT_ALIGNED_FK_TABLES = {
    "contacts",
    "opportunities",
    "activities",
    "signals",
    "workflow_runs",
    "workflow_steps",
    "integration_runs",
    "tool_calls",
    "approval_requests",
    "value_hypotheses",
    "outreach_drafts",
}

PROVENANCE_TABLES = {"accounts", "contacts", "activities", "signals"}


def table(name: str):
    return Base.metadata.tables[name]


def unique_column_sets(table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(constraint.columns.keys())
        for constraint in table(table_name).constraints
        if isinstance(constraint, UniqueConstraint)
    }


def foreign_key_column_sets(table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(constraint.columns.keys())
        for constraint in table(table_name).constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }


def check_constraint_names(table_name: str) -> set[str]:
    return {
        constraint.name
        for constraint in table(table_name).constraints
        if isinstance(constraint, CheckConstraint)
    }


def test_every_tenant_owned_table_has_tenant_id():
    for table_name in TENANT_OWNED_TABLES:
        assert "tenant_id" in table(table_name).columns, table_name


def test_referenced_core_tables_have_tenant_id_uniqueness():
    for table_name in [
        "users",
        "accounts",
        "contacts",
        "personas",
        "icp_definitions",
        "integration_connections",
        "workflow_runs",
        "workflow_steps",
    ]:
        assert ("tenant_id", "id") in unique_column_sets(table_name), table_name


def test_core_relationships_have_tenant_aligned_foreign_keys():
    for table_name in TENANT_ALIGNED_FK_TABLES:
        composite_fks = foreign_key_column_sets(table_name)
        assert any(columns[0] == "tenant_id" and len(columns) > 1 for columns in composite_fks), table_name


def test_provenance_columns_exist_on_importable_tables():
    for table_name in PROVENANCE_TABLES:
        columns = table(table_name).columns
        assert "source_provider" in columns
        assert "source_type" in columns
        assert "ingestion_timestamp" in columns
        assert "source_record_id" in columns


def test_custom_field_definitions_govern_custom_fields():
    columns = table("custom_field_definitions").columns
    for column_name in [
        "tenant_id",
        "entity_type",
        "field_name",
        "field_type",
        "validation_rules",
        "default_value",
        "metadata",
    ]:
        assert column_name in columns
    assert ("tenant_id", "entity_type", "field_name") in unique_column_sets("custom_field_definitions")


def test_state_and_range_constraints_exist():
    expected = {
        "workflow_runs": "ck_workflow_runs_status",
        "workflow_steps": "ck_workflow_steps_job_status",
        "tool_calls": "ck_tool_calls_job_status",
        "approval_requests": "ck_approval_requests_status",
        "integration_connections": "ck_integration_connections_status",
        "integration_runs": "ck_integration_runs_status",
        "signals": "ck_signals_strength_range",
        "activities": "ck_activities_not_orphaned",
        "value_hypotheses": "ck_value_hypotheses_confidence_range",
        "outreach_drafts": "ck_outreach_drafts_status",
    }
    for table_name, constraint_name in expected.items():
        assert any(name.endswith(constraint_name) for name in check_constraint_names(table_name)), table_name


def test_generated_artifact_tables_have_traceability_fields():
    for table_name in ["value_hypotheses", "outreach_drafts"]:
        columns = table(table_name).columns
        for column_name in [
            "tenant_id",
            "account_id",
            "contact_id",
            "workflow_run_id",
            "generated_by_agent",
            "generated_at",
            "confidence_score",
            "metadata",
        ]:
            assert column_name in columns


def test_llm_usage_records_track_cost_and_latency():
    columns = table("llm_usage_records").columns
    for column_name in ["model", "token_input", "token_output", "estimated_cost", "latency_ms"]:
        assert column_name in columns
