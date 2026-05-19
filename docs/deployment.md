# Deployment & Runtime

## Container Architecture

The platform is deployed as a suite of five containers, coordinated by Docker Compose:

1.  **db (PostgreSQL):** Relational storage for all GTM entities and system state.
2.  **redis:** Used for the workflow job queue, rate limit counters, and distributed locking.
3.  **backend (FastAPI):** Handles HTTP requests, authentication, and job enqueueing.
4.  **worker (Python):** Background job processor that executes agent workflows and integration syncs.
5.  **frontend (Next.js):** React-based user interface.

## Startup Sequence

1.  **Database Availability:** The `backend` and `worker` containers wait for PostgreSQL to be ready before starting.
2.  **Migrations:** The `backend` container runs `alembic upgrade head` to ensure the schema is up to date.
3.  **Seeding:** If `AUTO_SEED_ON_STARTUP=true`, the `backend` populates initial demo data.
4.  **API Readiness:** The FastAPI server starts and begins accepting connections.
5.  **Worker Loop:** The `worker` process starts polling Redis for new jobs.

## Worker Lifecycle

The background worker operates as a long-running polling loop:

1.  **Poll:** Checks the `workflow_jobs` list in Redis.
2.  **Lease:** Pops a job and establishes a distributed lock (if applicable).
3.  **Execute:** Invokes the `ProspectWorkflowService` to run the agentic graph.
4.  **Update:** Persists state transitions and results back to PostgreSQL.
5.  **Retry/Requeue:** If a job fails due to a transient error, it may be requeued based on the retry policy.

## Redis Usage

- **Job Queue:** `workflow_jobs` (List) - Stores serialized workflow job identifiers.
- **Rate Limiting:** (Fixed Window) - Stores request counts per tenant/user.
- **Caching:** (Planned) - For short-lived LLM responses or provider metadata.

## Production Deployment Notes

While the current setup uses Docker Compose for ease of review, the architecture is designed for cloud scalability:

- **Stateless Backend:** Multiple replicas of the FastAPI `backend` can be deployed behind a load balancer.
- **Horizontal Workers:** Additional `worker` containers can be added to handle increased workflow volume.
- **Managed Services:** PostgreSQL and Redis can be replaced with managed offerings (e.g., AWS RDS, AWS ElastiCache).
- **Secrets:** In production, use a dedicated secret manager (e.g., AWS Secrets Manager, HashiCorp Vault) rather than `.env` files.
- **Monitoring:** OpenTelemetry is partially integrated; a production deployment should export spans and metrics to a collector (e.g., Prometheus, Honeycomb).
