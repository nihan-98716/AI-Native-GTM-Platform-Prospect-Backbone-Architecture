"""Initial GTM platform schema.

Revision ID: 20260517_0001
Revises:
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260517_0001"
down_revision = None
branch_labels = None
depends_on = None

uuid = postgresql.UUID(as_uuid=False)
jsonb = postgresql.JSONB(astext_type=sa.Text())


def id_col() -> sa.Column:
    return sa.Column("id", uuid, primary_key=True, server_default=sa.text("gen_random_uuid()"))


def tenant_col() -> sa.Column:
    return sa.Column("tenant_id", uuid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def provenance() -> list[sa.Column]:
    return [
        sa.Column("source_provider", sa.String(80)),
        sa.Column("source_type", sa.String(40), nullable=False, server_default="seeded"),
        sa.Column("ingestion_timestamp", sa.DateTime(timezone=True)),
        sa.Column("source_record_id", sa.String(255)),
    ]


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table("tenants", id_col(), sa.Column("name", sa.String(255), nullable=False), sa.Column("slug", sa.String(100), nullable=False), *timestamps(), sa.UniqueConstraint("slug"))
    op.create_table("users", id_col(), tenant_col(), sa.Column("email", sa.String(255), nullable=False), sa.Column("full_name", sa.String(255), nullable=False), sa.Column("status", sa.String(50), nullable=False), sa.Column("roles", postgresql.ARRAY(sa.String()), nullable=False), sa.Column("permissions", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), *timestamps(), sa.UniqueConstraint("tenant_id", "id", name="uq_users_tenant_id"), sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"))
    op.create_index("ix_users_tenant_status", "users", ["tenant_id", "status"])

    op.create_table("accounts", id_col(), tenant_col(), sa.Column("name", sa.String(255), nullable=False), sa.Column("domain", sa.String(255)), sa.Column("lifecycle_stage", sa.String(80), nullable=False), sa.Column("firmographics", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("custom_fields", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), *provenance(), *timestamps(), sa.CheckConstraint("source_type in ('seeded', 'imported', 'generated')", name="ck_accounts_source_type"), sa.UniqueConstraint("tenant_id", "id", name="uq_accounts_tenant_id"), sa.UniqueConstraint("tenant_id", "domain", name="uq_accounts_tenant_domain"))
    op.create_index("ix_accounts_tenant_stage", "accounts", ["tenant_id", "lifecycle_stage"])

    op.create_table("personas", id_col(), tenant_col(), sa.Column("name", sa.String(120), nullable=False), sa.Column("description", sa.Text()), sa.Column("buying_committee_role", sa.String(120)), *timestamps(), sa.UniqueConstraint("tenant_id", "id", name="uq_personas_tenant_id"), sa.UniqueConstraint("tenant_id", "name", name="uq_personas_tenant_name"))
    op.create_table("icp_definitions", id_col(), tenant_col(), sa.Column("name", sa.String(255), nullable=False), sa.Column("description", sa.Text()), sa.Column("status", sa.String(50), nullable=False), sa.Column("criteria", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("target_personas", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), *timestamps(), sa.UniqueConstraint("tenant_id", "id", name="uq_icp_definitions_tenant_id"), sa.UniqueConstraint("tenant_id", "name", name="uq_icp_definitions_tenant_name"))
    op.create_index("ix_icp_definitions_tenant_status", "icp_definitions", ["tenant_id", "status"])

    op.create_table("contacts", id_col(), tenant_col(), sa.Column("account_id", uuid, nullable=False), sa.Column("persona_id", uuid), sa.Column("email", sa.String(255)), sa.Column("full_name", sa.String(255), nullable=False), sa.Column("title", sa.String(255)), sa.Column("custom_fields", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), *provenance(), *timestamps(), sa.CheckConstraint("source_type in ('seeded', 'imported', 'generated')", name="ck_contacts_source_type"), sa.ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]), sa.ForeignKeyConstraint(["tenant_id", "persona_id"], ["personas.tenant_id", "personas.id"]), sa.UniqueConstraint("tenant_id", "id", name="uq_contacts_tenant_id"), sa.UniqueConstraint("tenant_id", "email", name="uq_contacts_tenant_email"))
    op.create_index("ix_contacts_tenant_account", "contacts", ["tenant_id", "account_id"])

    op.create_table("opportunities", id_col(), tenant_col(), sa.Column("account_id", uuid, nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("stage", sa.String(120), nullable=False), sa.Column("amount", sa.Numeric(12, 2)), sa.Column("custom_fields", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), *timestamps(), sa.ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]), sa.UniqueConstraint("tenant_id", "id", name="uq_opportunities_tenant_id"))
    op.create_index("ix_opportunities_tenant_account", "opportunities", ["tenant_id", "account_id"])

    op.create_table("activities", id_col(), tenant_col(), sa.Column("account_id", uuid), sa.Column("contact_id", uuid), sa.Column("activity_type", sa.String(80), nullable=False), sa.Column("subject", sa.String(255)), sa.Column("body", sa.Text()), sa.Column("payload", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), *provenance(), *timestamps(), sa.CheckConstraint("account_id is not null or contact_id is not null", name="ck_activities_not_orphaned"), sa.CheckConstraint("source_type in ('seeded', 'imported', 'generated')", name="ck_activities_source_type"), sa.ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]), sa.ForeignKeyConstraint(["tenant_id", "contact_id"], ["contacts.tenant_id", "contacts.id"]), sa.UniqueConstraint("tenant_id", "id", name="uq_activities_tenant_id"))
    op.create_index("ix_activities_tenant_created", "activities", ["tenant_id", "created_at"])

    op.create_table("signals", id_col(), tenant_col(), sa.Column("account_id", uuid, nullable=False), sa.Column("source", sa.String(120), nullable=False), sa.Column("signal_type", sa.String(120), nullable=False), sa.Column("strength", sa.Numeric(5, 2)), sa.Column("payload", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False), *provenance(), *timestamps(), sa.CheckConstraint("strength is null or (strength >= 0 and strength <= 100)", name="ck_signals_strength_range"), sa.CheckConstraint("source_type in ('seeded', 'imported', 'generated')", name="ck_signals_source_type"), sa.ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]), sa.UniqueConstraint("tenant_id", "id", name="uq_signals_tenant_id"))
    op.create_index("ix_signals_tenant_observed", "signals", ["tenant_id", "observed_at"])
    op.create_index("ix_signals_tenant_type", "signals", ["tenant_id", "signal_type"])

    op.create_table("custom_field_definitions", id_col(), tenant_col(), sa.Column("entity_type", sa.String(120), nullable=False), sa.Column("field_name", sa.String(120), nullable=False), sa.Column("field_type", sa.String(80), nullable=False), sa.Column("validation_rules", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("default_value", jsonb), sa.Column("metadata", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), *timestamps(), sa.UniqueConstraint("tenant_id", "entity_type", "field_name", name="uq_custom_field_definitions_tenant_entity_field"))
    op.create_index("ix_custom_field_definitions_tenant_entity", "custom_field_definitions", ["tenant_id", "entity_type"])

    op.create_table("integration_connections", id_col(), tenant_col(), sa.Column("provider", sa.String(80), nullable=False), sa.Column("connection_name", sa.String(120), nullable=False), sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")), sa.Column("auth_type", sa.String(40), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("scopes", jsonb, nullable=False, server_default=sa.text("'[]'::jsonb")), sa.Column("encrypted_credentials", sa.LargeBinary()), sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("health", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), *timestamps(), sa.CheckConstraint("auth_type in ('api_key', 'oauth2', 'manual_config')", name="ck_integration_connections_auth_type"), sa.CheckConstraint("status in ('not_configured', 'live', 'failed', 'rate_limited')", name="ck_integration_connections_status"), sa.UniqueConstraint("tenant_id", "id", name="uq_integration_connections_tenant_id"), sa.UniqueConstraint("tenant_id", "provider", "connection_name", name="uq_integration_connections_tenant_provider_name"))
    op.create_index("ix_integration_connections_tenant_provider_status", "integration_connections", ["tenant_id", "provider", "status"])
    op.create_index("uq_integration_connections_one_live_default", "integration_connections", ["tenant_id", "provider"], unique=True, postgresql_where=sa.text("is_default = true and status = 'live'"))

    op.create_table("integration_runs", id_col(), tenant_col(), sa.Column("connection_id", uuid, nullable=False), sa.Column("provider", sa.String(80), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("request_metadata", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("error_message", sa.Text()), sa.Column("counts", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), *timestamps(), sa.CheckConstraint("status in ('pending', 'running', 'completed', 'failed', 'timed_out', 'cancelled')", name="ck_integration_runs_status"), sa.ForeignKeyConstraint(["tenant_id", "connection_id"], ["integration_connections.tenant_id", "integration_connections.id"]))
    op.create_index("ix_integration_runs_tenant_provider_status", "integration_runs", ["tenant_id", "provider", "status"])
    op.create_index("ix_integration_runs_tenant_created", "integration_runs", ["tenant_id", "created_at"])

    op.create_table("sync_cursors", id_col(), tenant_col(), sa.Column("connection_id", uuid, nullable=False), sa.Column("provider", sa.String(80), nullable=False), sa.Column("cursor_name", sa.String(120), nullable=False), sa.Column("cursor_value", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), *timestamps(), sa.ForeignKeyConstraint(["tenant_id", "connection_id"], ["integration_connections.tenant_id", "integration_connections.id"]), sa.UniqueConstraint("tenant_id", "connection_id", "cursor_name", name="uq_sync_cursors_tenant_connection_name"))
    op.create_index("ix_sync_cursors_tenant_provider", "sync_cursors", ["tenant_id", "provider"])

    op.create_table("workflow_runs", id_col(), tenant_col(), sa.Column("workflow_type", sa.String(80), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("icp_id", uuid), sa.Column("account_id", uuid), sa.Column("idempotency_key", sa.String(160), nullable=False), sa.Column("input", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("output", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("last_heartbeat_at", sa.DateTime(timezone=True)), *timestamps(), sa.CheckConstraint("status in ('queued', 'running', 'waiting_for_approval', 'succeeded', 'failed', 'cancelled', 'timed_out')", name="ck_workflow_runs_status"), sa.ForeignKeyConstraint(["tenant_id", "icp_id"], ["icp_definitions.tenant_id", "icp_definitions.id"]), sa.ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]), sa.UniqueConstraint("tenant_id", "id", name="uq_workflow_runs_tenant_id"), sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_workflow_runs_tenant_idempotency_key"))
    op.create_index("ix_workflow_runs_tenant_status", "workflow_runs", ["tenant_id", "status"])
    op.create_index("ix_workflow_runs_tenant_created", "workflow_runs", ["tenant_id", "created_at"])

    op.create_table("value_hypotheses", id_col(), tenant_col(), sa.Column("account_id", uuid, nullable=False), sa.Column("contact_id", uuid), sa.Column("workflow_run_id", uuid, nullable=False), sa.Column("generated_by_agent", sa.String(120), nullable=False), sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("confidence_score", sa.Numeric(5, 2)), sa.Column("title", sa.String(255), nullable=False), sa.Column("hypothesis", sa.Text(), nullable=False), sa.Column("metadata", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), *timestamps(), sa.CheckConstraint("confidence_score is null or (confidence_score >= 0 and confidence_score <= 100)", name="ck_value_hypotheses_confidence_range"), sa.ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]), sa.ForeignKeyConstraint(["tenant_id", "contact_id"], ["contacts.tenant_id", "contacts.id"]), sa.ForeignKeyConstraint(["tenant_id", "workflow_run_id"], ["workflow_runs.tenant_id", "workflow_runs.id"]))
    op.create_index("ix_value_hypotheses_tenant_account", "value_hypotheses", ["tenant_id", "account_id"])
    op.create_index("ix_value_hypotheses_tenant_workflow", "value_hypotheses", ["tenant_id", "workflow_run_id"])

    op.create_table("outreach_drafts", id_col(), tenant_col(), sa.Column("account_id", uuid, nullable=False), sa.Column("contact_id", uuid), sa.Column("workflow_run_id", uuid, nullable=False), sa.Column("generated_by_agent", sa.String(120), nullable=False), sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("confidence_score", sa.Numeric(5, 2)), sa.Column("subject", sa.String(255), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("metadata", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), *timestamps(), sa.CheckConstraint("confidence_score is null or (confidence_score >= 0 and confidence_score <= 100)", name="ck_outreach_drafts_confidence_range"), sa.CheckConstraint("status in ('draft', 'pending_approval', 'approved', 'rejected')", name="ck_outreach_drafts_status"), sa.ForeignKeyConstraint(["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]), sa.ForeignKeyConstraint(["tenant_id", "contact_id"], ["contacts.tenant_id", "contacts.id"]), sa.ForeignKeyConstraint(["tenant_id", "workflow_run_id"], ["workflow_runs.tenant_id", "workflow_runs.id"]))
    op.create_index("ix_outreach_drafts_tenant_contact", "outreach_drafts", ["tenant_id", "contact_id"])
    op.create_index("ix_outreach_drafts_tenant_status", "outreach_drafts", ["tenant_id", "status"])
    op.create_index("ix_outreach_drafts_tenant_workflow", "outreach_drafts", ["tenant_id", "workflow_run_id"])

    op.create_table("workflow_steps", id_col(), tenant_col(), sa.Column("workflow_run_id", uuid, nullable=False), sa.Column("step_name", sa.String(120), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("input", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("output", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("error_message", sa.Text()), *timestamps(), sa.CheckConstraint("status in ('pending', 'running', 'completed', 'failed', 'timed_out', 'cancelled')", name="ck_workflow_steps_job_status"), sa.ForeignKeyConstraint(["tenant_id", "workflow_run_id"], ["workflow_runs.tenant_id", "workflow_runs.id"]), sa.UniqueConstraint("tenant_id", "id", name="uq_workflow_steps_tenant_id"))
    op.create_index("ix_workflow_steps_tenant_run", "workflow_steps", ["tenant_id", "workflow_run_id"])

    op.create_table("approval_requests", id_col(), tenant_col(), sa.Column("workflow_run_id", uuid, nullable=False), sa.Column("workflow_step_id", uuid), sa.Column("status", sa.String(40), nullable=False), sa.Column("reviewer_user_id", uuid), sa.Column("reviewed_at", sa.DateTime(timezone=True)), sa.Column("reason", sa.Text()), sa.Column("decision_payload", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), *timestamps(), sa.CheckConstraint("status in ('pending', 'approved', 'rejected', 'expired')", name="ck_approval_requests_status"), sa.ForeignKeyConstraint(["tenant_id", "workflow_run_id"], ["workflow_runs.tenant_id", "workflow_runs.id"]), sa.ForeignKeyConstraint(["tenant_id", "workflow_step_id"], ["workflow_steps.tenant_id", "workflow_steps.id"]), sa.ForeignKeyConstraint(["tenant_id", "reviewer_user_id"], ["users.tenant_id", "users.id"]))
    op.create_index("ix_approval_requests_tenant_status", "approval_requests", ["tenant_id", "status"])

    op.create_table("tool_calls", id_col(), tenant_col(), sa.Column("workflow_run_id", uuid, nullable=False), sa.Column("workflow_step_id", uuid), sa.Column("tool_name", sa.String(120), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("input", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("output", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("error_message", sa.Text()), *timestamps(), sa.CheckConstraint("status in ('pending', 'running', 'completed', 'failed', 'timed_out', 'cancelled')", name="ck_tool_calls_job_status"), sa.ForeignKeyConstraint(["tenant_id", "workflow_run_id"], ["workflow_runs.tenant_id", "workflow_runs.id"]), sa.ForeignKeyConstraint(["tenant_id", "workflow_step_id"], ["workflow_steps.tenant_id", "workflow_steps.id"]))
    op.create_index("ix_tool_calls_tenant_run", "tool_calls", ["tenant_id", "workflow_run_id"])

    op.create_table("idempotency_keys", id_col(), tenant_col(), sa.Column("key", sa.String(160), nullable=False), sa.Column("resource_type", sa.String(120), nullable=False), sa.Column("resource_id", uuid), *timestamps(), sa.UniqueConstraint("tenant_id", "key", name="uq_idempotency_keys_tenant_key"))
    op.create_table("llm_usage_records", id_col(), tenant_col(), sa.Column("workflow_run_id", uuid, nullable=False), sa.Column("model", sa.String(120), nullable=False), sa.Column("token_input", sa.Integer(), nullable=False), sa.Column("token_output", sa.Integer(), nullable=False), sa.Column("estimated_cost", sa.Numeric(12, 6)), sa.Column("latency_ms", sa.Integer()), *timestamps(), sa.ForeignKeyConstraint(["tenant_id", "workflow_run_id"], ["workflow_runs.tenant_id", "workflow_runs.id"]))
    op.create_index("ix_llm_usage_records_tenant_run", "llm_usage_records", ["tenant_id", "workflow_run_id"])

    op.create_table("audit_events", id_col(), tenant_col(), sa.Column("actor_user_id", uuid), sa.Column("action", sa.String(120), nullable=False), sa.Column("resource_type", sa.String(120), nullable=False), sa.Column("resource_id", uuid), sa.Column("metadata", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.ForeignKeyConstraint(["tenant_id", "actor_user_id"], ["users.tenant_id", "users.id"]))
    op.create_index("ix_audit_events_tenant_created", "audit_events", ["tenant_id", "created_at"])


def downgrade() -> None:
    for table in [
        "audit_events", "llm_usage_records", "idempotency_keys", "tool_calls",
        "approval_requests", "workflow_steps", "outreach_drafts", "value_hypotheses", "workflow_runs", "sync_cursors",
        "integration_runs", "integration_connections", "custom_field_definitions",
        "signals", "activities", "opportunities", "contacts", "icp_definitions",
        "personas", "accounts", "users", "tenants",
    ]:
        op.drop_table(table)
