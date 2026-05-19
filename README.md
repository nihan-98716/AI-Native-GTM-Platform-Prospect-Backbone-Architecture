# AI-Native GTM Operating Layer

An AI-native go-to-market platform where sales work happens inside a unified operating layer instead of across disconnected point tools. This platform treats AI agents as first-class actors that can read GTM data, call approved tools, make structured decisions, request human approval, and leave durable execution traces.

## Repository Map

```text
/
├── backbone/      — Platform backbone code (FastAPI, SQLAlchemy, LangGraph)
├── prospect/      — Prospect vertical slice UI and client logic (Next.js)
├── infra/         — Docker Compose, Dockerfiles, and entrypoints
├── docs/          — Detailed system and architectural documentation
├── traces/        — Human-readable saved agent execution traces
├── tests/         — System-level integration and security tests
├── data/          — Seeded demo data and manifest
└── README.md      — This file
```

## Quick Start (One-Command)

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Configure Environment:**
    Copy `infra/env.example` to `.env` and add your `OPENAI_API_KEY`.
    ```bash
    cp infra/env.example .env
    ```

3.  **Boot the Platform:**
    ```bash
    docker compose up --build
    ```

### Accessing the System
- **Frontend UI:** [http://localhost:3000](http://localhost:3000)
- **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

## Prospect Workflow Walkthrough

The platform includes a complete **Prospect** vertical slice:
1.  **Targeting:** Define or load an ICP.
2.  **Sourcing:** Agents use the Apollo integration to source matching accounts.
3.  **Enrichment:** Contacts are discovered and enriched for target personas.
4.  **Signals:** Intent signals are captured and prioritized.
5.  **Hypothesis:** The system generates account-specific value propositions.
6.  **Outreach:** Personalized messaging is drafted for review.

## Implementation Status

### Built
- **Unified GTM Schema:** Relational PostgreSQL model with multi-tenant isolation.
- **Agent Orchestration:** Full LangGraph implementation with six specialized agents.
- **Integration Registry:** Pluggable adapter system with a functional Apollo provider.
- **Durable Tracing:** Persistent execution logs for all AI decisions and tool calls.
- **Async Execution:** Redis-backed worker layer for long-running jobs.

### Partial/Stubbed
- **Vector Store:** ChromaDB integration is planned but agents currently use relational grounding.
- **SSO:** Authentication uses locally issued JWTs; production identity provider integration is deferred.
- **UI Details:** Some management views (e.g., advanced integration config) are currently handled via seeded configuration.

## Documentation Links

- [Architecture Overview](docs/architecture.md)
- [Agent & Orchestration Design](docs/agents.md)
- [Integration Framework](docs/integrations.md)
- [Setup & Installation](docs/setup.md)
- [Deployment & Runtime](docs/deployment.md)

## Video Demo
*(Placeholder for submission video)*

## Known Limitations
- The system currently supports a single concurrent integration provider (Apollo).
- Workflow cancellation is implemented but requires a browser-side refresh for the latest status.
- Audit logs are tamper-evident but not yet tamper-proof in the local Docker deployment.
