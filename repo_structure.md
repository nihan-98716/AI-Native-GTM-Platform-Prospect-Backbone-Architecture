# Repository Structure

The submission package must preserve this top-level layout:

```text
/
├── backbone/
├── prospect/
├── infra/
├── docs/
├── traces/
├── tests/
├── data/
├── README.md
├── plan.md
├── repo_structure.md
├── architecture-decisions.md
└── tasks.md
```

## `/backbone`

Platform backbone code. This directory owns backend services, persistence, contracts, agent orchestration, integrations, auth, and observability.

Planned structure:

```text
backbone/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── deps.py
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── accounts.py
│   │   │   ├── contacts.py
│   │   │   ├── icps.py
│   │   │   ├── integrations.py
│   │   │   ├── prospect.py
│   │   │   └── traces.py
│   ├── agents/
│   │   ├── contracts.py
│   │   ├── graph.py
│   │   ├── prompts/
│   │   ├── tools/
│   │   └── workflows/
│   ├── core/
│   │   ├── config.py
│   │   ├── errors.py
│   │   ├── security.py
│   │   ├── tenancy.py
│   │   └── rate_limit.py
│   ├── contracts/
│   │   ├── api/
│   │   ├── events/
│   │   ├── agents/
│   │   ├── tools/
│   │   ├── integrations/
│   │   ├── workflows/
│   │   └── responses/
│   ├── integrations/
│   │   ├── contracts.py
│   │   ├── registry.py
│   │   ├── services.py
│   │   └── providers/
│   │       └── apollo.py
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── storage/
│   └── observability/
└── tests/
```

Boundary rules:

- API modules parse/validate requests and delegate to services.
- Services own business workflows and authorization checks.
- Repositories own SQLAlchemy queries and must require tenant context for tenant-scoped entities.
- Agents use tool interfaces, not repositories directly.
- Integrations normalize external payloads into platform DTOs before writes.
- Contract files under `app/contracts` are created before implementation and define API DTOs, events, agent state, tool IO, integration adapters, workflow state, and response models.
- Long-running workflows and integration syncs run through worker/job abstractions, not request handlers.
- Workflow contracts include `workflow_start`, `workflow_pause`, `workflow_resume`, `workflow_cancel`, and `workflow_complete`.
- Services own use-case logic and workflow lifecycle commands; LangGraph owns workflow progression; tools own bounded side effects; repositories own persistence only.

Testing boundary:

- `/backbone/tests` contains package-local unit tests for repositories, services, contracts, auth, agents, and integration adapters.
- Top-level `/tests` contains integration, acceptance, security, and end-to-end workflow tests that exercise the submission as a system.

## `/prospect`

Prospect vertical slice frontend and slice-specific client logic.

Planned structure:

```text
prospect/
├── package.json
├── next.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   └── prospect/
│       ├── page.tsx
│       ├── accounts/
│       ├── contacts/
│       ├── signals/
│       ├── hypotheses/
│       ├── outreach/
│       └── traces/
├── components/
├── lib/
│   ├── api-client.ts
│   ├── auth.ts
│   └── types.ts
└── tests/
```

Boundary rules:

- The frontend calls only backend HTTP APIs.
- No direct database access.
- UI state mirrors backend workflow state; backend remains authoritative.
- Any mocked or partial surface must be labeled in README.

## `/infra`

Local review infrastructure.

Planned structure:

```text
infra/
├── docker-compose.yml
├── Dockerfile.backbone
├── Dockerfile.prospect
├── postgres/
│   └── init.sql
├── otel/
│   └── collector-config.yaml
└── env.example
```

## `/docs`

Required challenge documentation.

```text
docs/
├── architecture.md
├── agents.md
└── integrations.md
```

## `/traces`

Human-readable saved agent execution traces.

```text
traces/
├── prospect-run-001.json
├── prospect-run-002.json
└── prospect-run-003.json
```

Trace files must contain decision summaries, rationale summaries, tool calls, state transitions, validation results, inputs, outputs, and final decisions. They must not require hidden chain-of-thought or private reasoning logs.

Trace files must redact API keys, tokens, credentials, auth headers, and secrets. They should mark PII fields, generated outreach, and provider payloads when present.

## `/tests`

Submission-level tests that exercise cross-package behavior, multi-tenancy, security boundaries, and user-visible Prospect flows.

```text
tests/
├── integration/
│   └── test_prospect_loop.py
├── security/
│   └── test_tenant_isolation.py
└── e2e/
    └── prospect.spec.ts
```

## `/data`

Seeded demo data and seed loader inputs.

```text
data/
├── seed_manifest.yaml
├── tenants.yaml
├── users.yaml
├── icps.yaml
├── personas.yaml
├── accounts.yaml
├── contacts.yaml
└── signals.yaml
```

## Packaging Rule

The final zip must contain source, infra, docs, traces, tests, and seed data only. It must not contain secrets, local virtual environments, node_modules, compiled binaries, database volumes, or generated caches.
