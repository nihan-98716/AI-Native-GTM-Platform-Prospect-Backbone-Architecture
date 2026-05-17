# Product Vision

Build an AI-native go-to-market platform where sales work happens inside a unified operating layer instead of across disconnected point tools. The platform must treat AI agents as first-class actors that can read GTM data, call approved tools, make structured decisions, request human approval, write back to the system of record, and leave durable execution traces.

The first product surface is Prospect: define or load an ICP, source matching accounts, enrich contacts, capture intent signals, generate account-specific value hypotheses, and produce personalized outreach. Prospect is the proof that the backbone is extensible enough to support future Engage, Manage, and Operate modules.

# Architecture Goals

- Use a unified GTM data model as the platform center: tenants, users, accounts, contacts, opportunities, activities, signals, ICP definitions, personas, agent runs, traces, integrations, integration jobs, custom fields, and audit events.
- Enforce multi-tenancy at every layer: JWT claims, request context, service authorization, repository filters, database constraints, and tests.
- Keep agent execution traceable: each workflow run must persist inputs, decision nodes, tool calls, structured outputs, failures, approvals, and database writes.
- Make integrations pluggable: each external provider must implement common authentication, sync, normalization, rate limit, retry, and observability contracts.
- Keep integration selection provider-agnostic: implement one real integration that materially powers Prospect, with Apollo preferred and HubSpot, Clearbit, Hunter, Gmail, or another enrichment provider acceptable if credentials or API access make Apollo impractical.
- Keep the Prospect vertical slice real but bounded: the implementation must work end-to-end with seeded data and real LLM/API calls while avoiding a fragile demo-only architecture.
- Prefer boring, auditable infrastructure: FastAPI, PostgreSQL, SQLAlchemy, Alembic, Redis, ChromaDB, LangGraph, Next.js, Docker Compose, OpenTelemetry, pytest, and Playwright.

# Constraints

- Implementation must follow contract-first development: interfaces, DTOs, API contracts, agent contracts, tool contracts, response models, and event schemas precede business logic.
- Contract artifacts must live under `/backbone/app/contracts` with explicit `api`, `events`, `agents`, `tools`, `integrations`, `workflows`, and `responses` subfolders.
- Persistence must use PostgreSQL; in-memory and JSON-file persistence are disallowed for platform data.
- The system must be Dockerized and bootable with one documented command.
- Secrets must come from environment variables only.
- Files should stay under 500 lines unless generated migrations or lockfiles make that impractical.
- Routes must not contain business logic; use service and repository layers.
- Agent workflows must not degrade into single prompt -> single response interactions.
- After Phase 1, core architecture is frozen. Later changes must be additive, optimizing, or corrective.

# Assumptions

- Reviewers will provide their own OpenAI-compatible LLM key and at least one supported integration API key when live integration review is required.
- Apollo is the preferred first Prospect integration because it materially powers account/contact sourcing and enrichment, but the architecture must allow a different real provider without core rewrites.
- A seeded demo environment can include representative local GTM data while live external enrichment requires the reviewer to provide valid API credentials.
- Authentication can use locally issued JWTs for the challenge, with production SSO deferred but the RBAC model designed for it.
- The first deployment target is Docker Compose for review, with cloud deployment and managed services deferred.
- ChromaDB is used for retrieval and semantic context only; PostgreSQL remains the source of truth.

# Risks

- External API availability and quota limits may make live Apollo runs inconsistent during judging.
- Provider credential availability may require using a non-Apollo real integration; the integration framework must keep Prospect dependent on normalized provider outputs, not provider-specific payloads.
- Seed data can be mistaken for live integration output if provenance is not explicit in the UI, README, and `integration_runs` records.
- LLM latency and cost may vary by reviewer model/account; workflows need model routing, timeouts, and resumable traces.
- Multi-tenancy bugs are high-severity because they can leak customer data; tenant isolation needs integration tests early.
- Long-running agent and integration workflows can overload request handlers unless async execution, workflow status tracking, cancellation, retries, and backpressure are designed before implementation.
- Agent trace logs can create privacy and compliance risk if they capture hidden chain-of-thought or unredacted sensitive data.
- Frontend polish can consume time without improving the core score; UI scope must stay focused on proving the backbone.
- Overbuilding generic extensibility before the Prospect loop works can delay the vertical slice.
- Under-documenting deferred items can make honest limitations look like accidental gaps.

# Technical Decisions

- FastAPI backend exposes typed REST APIs for UI, workflow execution, integrations, and traces.
- PostgreSQL stores all system-of-record entities, normalized integration records, agent runs, trace events, audit logs, and custom fields.
- SQLAlchemy 2.x models and Alembic migrations define schema evolution.
- Redis backs async job coordination, workflow locks, rate limit counters, and short-lived cache entries.
- Redis-backed workers execute long-running workflow and integration jobs outside request handlers.
- LangGraph models Prospect as a durable multi-step workflow with state passing between agents.
- ChromaDB stores embeddings for account/activity/signal retrieval used by value hypothesis and outreach agents.
- Next.js frontend is a thin client over backend APIs and never accesses the database directly.
- OpenTelemetry provides trace IDs, correlation IDs, spans, and metrics across API, workflow, tool, DB, and integration operations.

# MVP Scope

- Repository structure matching the required Topcoder package layout.
- Platform backbone with typed contracts, models, repositories, services, APIs, observability, and tests.
- Unified GTM schema with multi-tenant constraints and indexes.
- JWT authentication, RBAC primitives, request-scoped tenant context, CORS, rate limiting, validation, and audit logs.
- LangGraph Prospect workflow with five agents: ProspectResearchAgent, ContactEnrichmentAgent, IntentSignalAgent, ValueHypothesisAgent, and OutreachAgent.
- Integration framework plus one real provider, preferably Apollo, with API-key configuration, live API calls, normalization, retries, rate limiting, provenance, and error logging.
- Prospect UI covering ICP selection, account sourcing, enrichment, signals, hypotheses, outreach, and trace review.
- Seeded data: at least one tenant, two ICPs, three personas, ten companies, ten contacts, and ten signals.
- Tests for Prospect loop, agent orchestration, integration adapters, repositories, and tenant isolation.
- Required docs, saved traces, and root README.
- Explicit contract artifacts for APIs, events, agents, tools, integrations, workflows, and response models before implementation.
- Workflow, integration, approval, idempotency, tool-call, audit, and LLM usage persistence entities.

# Deferred Features

- Production SSO/SAML, SCIM, and enterprise identity lifecycle.
- Billing, usage quotas by plan, and procurement workflows.
- Full CRM two-way sync with Salesforce/HubSpot.
- Email send capability and deliverability management.
- Forecasting, pipeline inspection, and quote workflows for later Manage/Operate modules.
- Advanced admin console for custom objects and field-level permissions.
- Cloud IaC, Kubernetes, autoscaling, and managed observability stack.
- Full data lifecycle automation for trace redaction, PII classification, retention policy enforcement, and immutable audit export. These policies must be designed early but can be implemented incrementally.

# Future Extensions

- Engage module plugs into accounts, contacts, activities, outreach drafts, approvals, and email/calendar integrations.
- Manage module plugs into opportunities, activities, account plans, conversation summaries, next-best actions, and forecasting events.
- Operate module plugs into audit logs, workflow policies, integration health, quotas, tenant admin, and compliance exports.
- Additional integrations implement the same ProviderAdapter contract: HubSpot, Salesforce, Gmail, Outlook, Slack, LinkedIn-safe signal sources, Clearbit/People Data Labs alternatives, and website intent providers.
- Custom object support grows from typed custom fields into tenant-defined schemas with governance, search, and workflow triggers.

# Delivery Roadmap

1. Phase 0: Planning artifacts, repository contract, ADRs, and task tracker.
2. Phase 1: Architecture docs, diagrams, contract plan, and staff/principal/scalability review.
3. Phase 2: PostgreSQL schema, SQLAlchemy models, Alembic migrations, seed schema design, and tenant-isolation tests.
4. Phase 3: Contract artifacts, backbone modules, seed loader, APIs, auth/RBAC, repositories, services, observability, and audit logging.
5. Phase 4: LangGraph Prospect agents, tool contracts, prompts, structured outputs, retries, fallbacks, and trace persistence.
6. Phase 5: Integration framework and one real Prospect-powering provider, preferably Apollo.
7. Phase 6: Prospect UI and workflow surface.
8. Phase 7: Seeded demo environment.
9. Phase 8: Automated tests and review hardening.
10. Phase 9: Final documentation.
11. Phase 10: Saved traces and final judge simulation.
