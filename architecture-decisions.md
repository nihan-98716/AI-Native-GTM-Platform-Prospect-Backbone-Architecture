# Architecture Decisions

## ADR-001: Use PostgreSQL as the GTM System of Record

Status: Accepted

Context:
The platform needs durable, relational, multi-tenant data for accounts, contacts, opportunities, activities, signals, agent runs, integrations, and audit events. The challenge explicitly disallows in-memory or file persistence and judges the schema as the platform foundation.

Decision:
Use PostgreSQL as the source of truth, with SQLAlchemy 2.x models and Alembic migrations. Use tenant-scoped UUID primary keys, foreign keys, composite tenant/entity indexes, JSONB for controlled extensibility, and normalized relational tables for core GTM entities.

Consequences:
- Strong relational integrity supports senior-engineer review and future modules.
- PostgreSQL indexes and query planning support growth from demo data to large tenants.
- JSONB custom fields allow extensibility without replacing the core schema.
- Tenant isolation must be enforced consistently in repositories and tested because shared tables increase blast radius if filters are missed.

Alternatives Considered:
- MongoDB: flexible but weaker for the required relational GTM model and joins.
- SQLite: easier local setup but not credible for multi-tenant platform review.
- Separate database per tenant: strong isolation but operationally heavy for challenge scope.

## ADR-002: Use a Modular Monolith Backend for the First Challenge

Status: Accepted

Context:
The platform needs strong service boundaries, but the first challenge must ship a coherent backbone, Prospect slice, integration, tests, and docs. Premature microservices would add deployment and observability complexity without proving product value.

Decision:
Implement the backend as a modular monolith in FastAPI with explicit module boundaries: `core`, `api`, `models`, `repositories`, `services`, `agents`, `integrations`, `storage`, and `observability`. Enforce boundaries through interfaces and dependency injection rather than network calls.

Consequences:
- One-command Docker Compose review stays simple.
- Internal boundaries remain clear enough to extract services later.
- Cross-module calls are cheap and testable.
- Teams adding Engage, Manage, and Operate can extend modules without standing up new services.
- Future extraction requires discipline now: no business logic in routes, no direct DB access from agents, no circular imports.

Alternatives Considered:
- Microservices from day one: more scalable in theory, but higher delivery risk and harder review setup.
- Single unstructured FastAPI app: faster initially, but poor extension story and weaker architecture score.

## ADR-003: Use LangGraph for Explicit Agent Workflow State

Status: Accepted

Context:
The challenge requires real agentic behavior: multi-step reasoning, tool use, structured outputs, retries, human checkpoints, persistent traces, and state passing. A single LLM call or chat wrapper is explicitly insufficient.

Decision:
Use LangGraph to model the Prospect workflow as a directed state graph. Each agent node receives typed state, calls tools through interfaces, validates structured outputs, writes trace events, and passes state forward. Human approval checkpoints are represented as graph interrupts or persisted review states.

Consequences:
- Agent behavior is inspectable and naturally traceable.
- Workflow nodes can be tested independently.
- New modules can add graph nodes or compose new workflows without replacing orchestration.
- Graph state must be versioned carefully because saved traces and resumable workflows become platform records.

Alternatives Considered:
- Raw OpenAI SDK orchestration: maximum control but more custom framework code.
- LangChain chains only: less explicit state and branching than required.
- Background jobs only: useful execution primitive, but insufficient agent semantics.

## ADR-004: Use Provider Adapter Contracts for Integrations

Status: Accepted

Context:
The first integration must be real and power Prospect, but the platform should support many future providers without touching core code.

Decision:
Define integration provider contracts for auth, connection validation, sync planning, fetch, normalize, write, retry, and health reporting. Register providers through an integration registry. Implement one real integration that materially powers Prospect. Apollo is preferred for account/contact sourcing and enrichment, but HubSpot, Clearbit, Hunter, Gmail, or another enrichment provider can be used if it satisfies the same provider contracts and powers the Prospect slice.

Consequences:
- The next integration follows a repeatable pattern.
- Core Prospect services depend on normalized platform DTOs, not provider payloads.
- Provider-specific rate limits and auth live outside core workflow logic.
- Requires careful documentation and tests to prove this is a framework rather than a one-off wrapper.
- Integration connection states are `not_configured`, `live`, `failed`, and `rate_limited`.
- Integration runs persist provider, request metadata, status, errors, record counts, and provenance so reviewers can distinguish seed data from live integration data.

Alternatives Considered:
- Direct Apollo calls inside Prospect services: faster but poor extension story.
- External iPaaS dependency: not appropriate for a self-contained challenge submission.

## ADR-005: Use JWT and RBAC Primitives from the Start

Status: Accepted

Context:
The challenge requires JWT validation, RBAC, tenant isolation, audit logs, and enterprise security posture. Even a local demo must prove the security model.

Decision:
Use locally issued JWTs for review, with claims for `sub`, `tenant_id`, `roles`, and `permissions`. Enforce RBAC in service dependencies and persist audit events for sensitive operations. Keep SSO/SAML out of scope but preserve identity-provider extension points.

Consequences:
- Reviewers can evaluate security without external identity setup.
- Future enterprise identity can replace token issuance without rewriting authorization logic.
- Tests must cover tenant isolation and permission failures.

Alternatives Considered:
- No auth for local demo: unacceptable under security requirements.
- Full OAuth/SAML identity provider: too much setup burden for reviewers.

## ADR-006: Keep ChromaDB Retrieval-Only

Status: Accepted

Context:
The platform benefits from semantic retrieval over account context, activities, and signals, but source-of-truth data must remain relational and auditable.

Decision:
Use ChromaDB for embeddings and retrieval only. Store references to PostgreSQL entity IDs and tenant IDs in vector metadata. Rehydrate authoritative records from PostgreSQL before agent use.

Consequences:
- Retrieval improves hypothesis and outreach quality.
- Data correctness remains anchored in PostgreSQL.
- Tenant metadata must be included in vector filters to prevent cross-tenant leakage.
- Vector rebuild and drift handling are deferred but documented.

Alternatives Considered:
- pgvector: simpler operational footprint, but ChromaDB aligns with the requested stack.
- No vector store: acceptable for v1 but weaker AI-native architecture.

## ADR-007: Tenant Isolation Strategy

Status: Accepted

Context:
The platform is multi-tenant from the first challenge. Tenant isolation cannot depend only on route-level checks because future modules and integrations will add new query paths.

Decision:
Use layered tenant isolation across request, service, repository, and database layers. Every tenant-owned entity must include `tenant_id`. Tenant-scoped uniqueness must use composite unique constraints that include `tenant_id`. Foreign-key relationships between tenant-owned entities should include tenant alignment where practical, either through composite foreign keys or explicit database constraints. Repositories must require tenant context and apply tenant filters by default. Service methods must authorize tenant and permission scope before invoking repositories. Request handling must derive tenant context from validated JWT claims. PostgreSQL Row Level Security will be evaluated during Phase 1 and either adopted for tenant-owned tables or explicitly deferred with compensating controls.

Consequences:
- Tenant filtering becomes a mandatory platform invariant rather than a convention.
- Negative isolation tests can prove cross-tenant access is blocked at repository and API layers.
- Composite keys and constraints add schema complexity but reduce data leakage risk.
- Optional RLS evaluation preserves the current stack while allowing stronger database enforcement if it fits the delivery timeline.

Alternatives Considered:
- Repository filters only: simpler but too easy to bypass.
- Separate database per tenant: strong isolation but operationally heavy for the challenge and later local review.
- RLS only: strong data-layer protection, but still requires request/service authorization and careful session context management.

## ADR-008: Async Workflow and Job Execution

Status: Accepted

Context:
Prospect workflows, LLM calls, integration syncs, retries, and enrichment steps can exceed HTTP request timeouts and require resumability. Running them only inside request handlers would make cancellation, retries, backpressure, and observability weak.

Decision:
Use Redis-backed workers for long-running workflow and integration jobs. API requests enqueue jobs, return workflow/job status, and allow polling or refresh from persisted state. PostgreSQL stores `workflow_runs`, `workflow_steps`, and `idempotency_keys`. Workflow status transitions are `queued`, `running`, `waiting_for_approval`, `succeeded`, `failed`, `cancelled`, and `timed_out`. Retries use bounded exponential backoff with provider-aware retryability checks. Timeouts are defined per job type and per external call. Cancellation marks the workflow run and prevents new work from starting; in-flight external calls are allowed to finish but their outputs are ignored if the run is cancelled. Backpressure is handled with queue depth checks, per-tenant rate limits, and worker concurrency limits.

Consequences:
- UI can show durable workflow progress instead of blocking on long requests.
- Agent traces and integration runs are resilient to partial failure.
- Idempotency keys prevent duplicate writes from retries or browser resubmits.
- Worker orchestration adds implementation complexity but stays within the chosen Redis/FastAPI stack.

Alternatives Considered:
- Synchronous request execution: simpler but unreliable for real agentic workflows.
- New workflow service: more scalable later, but it would introduce a major service before the architecture freeze.

## ADR-009: Security Architecture Baseline

Status: Accepted

Context:
The submission will undergo security review and must satisfy explicit requirements for JWT validation, RBAC, tenant isolation, secrets, SQL injection protection, XSS protection, SSRF protection, API validation, rate limiting, CORS, and audit logs.

Decision:
Use JWT validation at API boundaries with tenant and permission claims. Enforce RBAC in service-layer authorization checks. Validate all API payloads with typed schemas. Use SQLAlchemy parameter binding only and prohibit raw string-built SQL. Store secrets in environment variables only. Store external integration tokens encrypted at rest. Restrict outbound integration calls to registered provider base URLs through an outbound allowlist to reduce SSRF risk. Configure CORS to explicit frontend origins. Apply per-tenant and per-user rate limits. Persist audit events for authentication, integration configuration, workflow execution, approval, data export, and privileged changes. Frontend code must use framework escaping defaults, avoid unsafe HTML rendering, and treat API-returned text as untrusted.

Consequences:
- Security controls are explicit before implementation.
- Future identity providers can replace local token issuance without changing service authorization semantics.
- Integration flexibility is constrained by the outbound allowlist, which is acceptable for enterprise safety.
- Token encryption key management remains a production hardening item for later deployment.

Alternatives Considered:
- Local demo with relaxed auth: incompatible with challenge requirements.
- Full enterprise IdP setup: too much reviewer burden for this challenge.

## ADR-010: Observability Contract

Status: Accepted

Context:
The platform must be operable and reviewable. Agent workflows, tool calls, integration jobs, and database operations need consistent logs, metrics, traces, and audit boundaries.

Decision:
Every service log event must include `trace_id`, `correlation_id`, `tenant_id`, `request_id`, `workflow_id` when available, `service`, `status`, and `duration`. Span names use `service.operation`, for example `api.prospect.start`, `agent.value_hypothesis.run`, `tool.integration.search_accounts`, and `db.accounts.query`. Required metrics include `api_requests_total`, `api_request_duration_ms`, `workflow_runs_total`, `workflow_duration_ms`, `workflow_step_duration_ms`, `agent_runs_total`, `agent_tokens_total`, `agent_cost_usd`, `tool_calls_total`, `tool_call_duration_ms`, `integration_requests_total`, `integration_rate_limited_total`, `db_query_duration_ms`, and `errors_total`. Trace and correlation IDs propagate from API requests into workers, agent nodes, tools, repositories, and integration providers. Telemetry records operational behavior; audit logs record user/security/compliance events and must be durable and tamper-resistant in design.

Consequences:
- Reviewers can inspect how work moved through the platform.
- Agent cost and latency can be measured instead of estimated from code.
- Audit and telemetry remain separate, avoiding noisy compliance records and insufficient operational logs.

Alternatives Considered:
- Ad hoc logging: faster initially but weak under AI-assisted review.
- Full managed observability stack: useful in production but unnecessary for local Docker Compose review.

## ADR-011: Data Lifecycle and Trace Privacy

Status: Accepted

Context:
Agent traces, integration payloads, contacts, and outreach drafts may contain sensitive business and personal data. Traceability is required, but hidden chain-of-thought and private reasoning logs must not be exposed.

Decision:
Traceability captures decision summaries, rationale summaries, tool calls, state transitions, validation results, inputs, outputs, and final decisions. The platform must not require hidden chain-of-thought or private reasoning logs. Design for trace redaction, PII classification, encrypted integration tokens, retention rules, and immutable audit logs. Implementation can be incremental, but schemas must preserve the ability to redact sensitive trace fields while retaining reviewable execution evidence.

Consequences:
- The platform satisfies traceability without relying on unavailable or unsafe raw model reasoning.
- Future compliance work has schema support instead of requiring trace rewrites.
- Review traces remain human-readable and safer to commit.

Alternatives Considered:
- Store raw prompts and model outputs only: simpler but weaker operational traceability.
- Store all reasoning verbatim: unsafe and incompatible with modern model behavior.

## ADR-012: Scalability Modeling Assumptions

Status: Accepted

Context:
The challenge asks for scalability review including a stress scenario, but 100k concurrent users should be treated as a modeling scenario rather than an immediate hard requirement for the local submission.

Decision:
Phase 1 scalability review will model expected load, peak load, and growth scenarios. A 100k concurrent user stress scenario will evaluate stateless API replicas, worker scaling, database connection limits, queue backpressure, external provider limits, LLM throughput, vector retrieval limits, and likely bottlenecks. The implementation remains Docker Compose for review, but boundaries must not prevent horizontal API and worker scaling later.

Consequences:
- Scalability reasoning stays credible without pretending the challenge implementation is production-scale.
- Early bottlenecks can be identified before architecture freeze.
- Later cloud deployment can add managed Postgres, Redis, workers, and observability without changing core boundaries.

Alternatives Considered:
- Claim 100k-user readiness now: unrealistic and likely to weaken judge confidence.
- Ignore 100k entirely: misses the requested review checkpoint.
