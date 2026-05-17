# Current Sprint

Task: Phase 0 planning artifacts
Priority: P0
Dependencies: Challenge requirements
Status: Completed

Task: Define immutable architecture baseline
Priority: P0
Dependencies: Phase 0 planning artifacts
Status: Completed

Task: Draft `docs/architecture.md` with Mermaid diagrams
Priority: P0
Dependencies: Define immutable architecture baseline
Status: Completed

Task: Define contract artifact inventory under `/backbone/app/contracts`
Priority: P0
Dependencies: Define immutable architecture baseline
Status: Completed

Task: Define tenant isolation enforcement strategy
Priority: P0
Dependencies: Define immutable architecture baseline
Status: Completed

Task: Define async workflow/job execution strategy
Priority: P0
Dependencies: Define immutable architecture baseline
Status: Completed

Task: Define observability and audit contracts
Priority: P0
Dependencies: Define immutable architecture baseline
Status: Completed

Task: Staff Architecture Review after Phase 1
Priority: P0
Dependencies: `docs/architecture.md`
Status: Completed

Task: Principal Engineer Review after Phase 1
Priority: P0
Dependencies: `docs/architecture.md`
Status: Completed

Task: Scalability Review after Phase 1
Priority: P0
Dependencies: `docs/architecture.md`
Status: Completed

# Backlog

Task: Create backend project scaffold under `/backbone`
Priority: P0
Dependencies: Architecture freeze after Phase 1
Status: Pending

Task: Create frontend project scaffold under `/prospect`
Priority: P1
Dependencies: Architecture freeze after Phase 1
Status: Pending

Task: Add Docker Compose infrastructure under `/infra`
Priority: P0
Dependencies: Backend and frontend scaffold decisions
Status: Pending

Task: Define API, DTO, event, agent, tool, integration, workflow, and response contracts under `/backbone/app/contracts`
Priority: P0
Dependencies: Architecture freeze after Phase 1
Status: Pending

Task: Create `/backbone/app/contracts/api`
Priority: P0
Dependencies: Architecture freeze after Phase 1
Status: Pending

Task: Create `/backbone/app/contracts/events`
Priority: P0
Dependencies: Architecture freeze after Phase 1
Status: Pending

Task: Create `/backbone/app/contracts/agents`
Priority: P0
Dependencies: Architecture freeze after Phase 1
Status: Pending

Task: Create `/backbone/app/contracts/tools`
Priority: P0
Dependencies: Architecture freeze after Phase 1
Status: Pending

Task: Create `/backbone/app/contracts/integrations`
Priority: P0
Dependencies: Architecture freeze after Phase 1
Status: Pending

Task: Create `/backbone/app/contracts/workflows`
Priority: P0
Dependencies: Architecture freeze after Phase 1
Status: Pending

Task: Create `/backbone/app/contracts/responses`
Priority: P0
Dependencies: Architecture freeze after Phase 1
Status: Pending

Task: Implement PostgreSQL schema, SQLAlchemy models, Alembic migrations, and indexes
Priority: P0
Dependencies: Contracts
Status: Pending

Task: Design seed schema for tenants, users, ICPs, personas, accounts, contacts, and signals
Priority: P0
Dependencies: Database schema design
Status: Pending

Task: Implement tenant context, JWT validation, RBAC, CORS, rate limiting, and audit logs
Priority: P0
Dependencies: Core backend scaffold
Status: Pending

Task: Implement repositories with mandatory tenant filters
Priority: P0
Dependencies: Database schema
Status: Pending

Task: Implement composite tenant constraints and tenant-scoped unique indexes
Priority: P0
Dependencies: Database schema
Status: Pending

Task: Document PostgreSQL RLS deferral and compensating controls in migration assumptions
Priority: P0
Dependencies: Database schema
Status: Pending

Task: Implement mandatory tenant-aligned foreign keys for core tenant-owned relationships
Priority: P0
Dependencies: Database schema
Status: Pending

Task: Add `custom_field_definitions` schema and validation assumptions
Priority: P0
Dependencies: Database schema
Status: Pending

Task: Implement workflow run, workflow step, approval request, tool call, integration run, integration connection, sync cursor, audit event, idempotency key, and LLM usage entities
Priority: P0
Dependencies: Database schema
Status: Pending

Task: Implement Redis-backed worker execution with workflow status transitions
Priority: P0
Dependencies: Workflow contracts and persistence entities
Status: Pending

Task: Implement retry, timeout, cancellation, idempotency, and backpressure handling
Priority: P0
Dependencies: Redis-backed worker execution
Status: Pending

Task: Implement worker watchdog for stuck jobs, timeout marking, lock release, telemetry, and audit events
Priority: P0
Dependencies: Redis-backed worker execution
Status: Pending

Task: Implement lightweight admission control with per-tenant workflow limits, queue thresholds, 202 deferred responses, and 429 rejection behavior
Priority: P0
Dependencies: Redis-backed worker execution
Status: Pending

Task: Implement LangGraph Prospect workflow
Priority: P0
Dependencies: Agent contracts and persistence
Status: Pending

Task: Implement ProspectResearchAgent
Priority: P0
Dependencies: LangGraph workflow contracts
Status: Pending

Task: Implement ContactEnrichmentAgent
Priority: P0
Dependencies: Integration framework
Status: Pending

Task: Implement IntentSignalAgent
Priority: P0
Dependencies: Signal model and integration framework
Status: Pending

Task: Implement ValueHypothesisAgent
Priority: P0
Dependencies: Retrieval and agent tool contracts
Status: Pending

Task: Implement OutreachAgent
Priority: P0
Dependencies: Value hypotheses and contact/persona model
Status: Pending

Task: Implement one real Prospect-powering integration provider, preferably Apollo
Priority: P0
Dependencies: Integration framework
Status: Pending

Task: Implement integration states `not_configured`, `live`, `failed`, and `rate_limited`
Priority: P0
Dependencies: Integration framework
Status: Pending

Task: Persist integration run provider, request metadata, status, errors, counts, and data provenance
Priority: P0
Dependencies: Integration framework
Status: Pending

Task: Implement provider auth variants for `api_key`, `oauth2`, and `manual_config`
Priority: P0
Dependencies: Integration framework
Status: Pending

Task: Persist `source_provider`, `source_type`, `ingestion_timestamp`, and `source_record_id` on imported or generated records where provenance is required
Priority: P0
Dependencies: Integration framework
Status: Pending

Task: Build Prospect UI workflow
Priority: P1
Dependencies: Backend Prospect APIs
Status: Pending

Task: Add automatic seed loader
Priority: P0
Dependencies: Database schema
Status: Pending

Task: Add integration, agent, repository, tenant-isolation, and Playwright tests
Priority: P0
Dependencies: Implemented backend and frontend flows
Status: Pending

Task: Add negative tenant-isolation tests at API and repository layers
Priority: P0
Dependencies: Tenant isolation implementation
Status: Pending

Task: Add observability contract tests for required log fields and trace propagation
Priority: P1
Dependencies: Observability implementation
Status: Pending

Task: Enforce observability metric cardinality rules
Priority: P1
Dependencies: Observability implementation
Status: Pending

Task: Implement centralized audit service contract for services, workers, agents, integrations, and approvals
Priority: P0
Dependencies: Audit event schema
Status: Pending

Task: Write `docs/agents.md`, `docs/integrations.md`, and root `README.md`
Priority: P0
Dependencies: Implementation details stabilized
Status: Pending

Task: Generate three saved agent traces
Priority: P0
Dependencies: Working Prospect loop with seeded data
Status: Pending

Task: Ensure saved traces exclude hidden chain-of-thought and include decision summaries, rationale summaries, tool calls, state transitions, validation results, inputs, outputs, and final decisions
Priority: P0
Dependencies: Trace persistence
Status: Pending

Task: Apply minimum v1 trace redaction for API keys, tokens, credentials, auth headers, and secrets
Priority: P0
Dependencies: Trace persistence
Status: Pending

Task: Implement approval states `pending`, `approved`, `rejected`, and `expired` with reviewer, timestamp, and reason fields
Priority: P0
Dependencies: Workflow and approval schemas
Status: Pending

# Technical Debt

Task: Replace local JWT issuance with production identity provider integration
Priority: P2
Dependencies: Enterprise auth requirements
Status: Deferred

Task: Add cloud deployment IaC
Priority: P2
Dependencies: Target cloud decision
Status: Deferred

Task: Add tenant-level quotas and billing controls
Priority: P2
Dependencies: Product packaging decisions
Status: Deferred

Task: Add vector index rebuild jobs and embedding drift monitoring
Priority: P2
Dependencies: Production retrieval operations
Status: Deferred

Task: Add full CRM two-way sync conflict resolution
Priority: P2
Dependencies: Salesforce/HubSpot integration phase
Status: Deferred

Task: Implement automated trace redaction, PII classification, retention enforcement, and immutable audit export
Priority: P2
Dependencies: Production compliance requirements
Status: Deferred

# Risks

Risk: Apollo API quota or credential availability could block live review.
Mitigation: Keep integration provider-agnostic, support one real Prospect-powering provider, document required key, handle provider errors clearly, persist integration provenance, and preserve seeded fallback data as explicitly seeded data rather than fake integration output.
Status: Open

Risk: LLM costs and latency could make full Prospect runs slow.
Mitigation: Use model routing, structured compact prompts, caching, and persisted intermediate state.
Status: Open

Risk: Tenant isolation regression could leak data.
Mitigation: Require tenant context in repositories and add negative isolation tests.
Status: Open

Risk: Scope pressure could reduce architecture quality.
Mitigation: Keep UI pragmatic and invest first in schema, contracts, traces, and docs.
Status: Open

Risk: Architecture freeze after Phase 1 makes early mistakes expensive.
Mitigation: Perform staff, principal, and scalability reviews before implementation.
Status: Open

Risk: Long-running workflows may overload API request handlers if async execution is weak.
Mitigation: Use Redis-backed workers, workflow status tracking, timeouts, retries, cancellation, idempotency keys, and queue backpressure controls.
Status: Open

Risk: Trace data may expose sensitive information or imply private reasoning log capture.
Mitigation: Store decision summaries, rationale summaries, tool calls, state transitions, validation results, inputs, outputs, and final decisions only; design redaction and retention policies.
Status: Open

Risk: Observability can become inconsistent across API, workers, agents, tools, integrations, and database access.
Mitigation: Define required log fields, metrics, span naming rules, trace propagation, and audit-versus-telemetry boundaries before implementation.
Status: Open
