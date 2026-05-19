# Integration Framework

## Overview

The platform uses a pluggable integration framework designed to normalize data from external GTM providers (CRMs, enrichment tools, intent sources) into a unified platform schema.

## Current Provider: Apollo

The **Apollo** integration is fully implemented and provides the primary data source for the Prospecting vertical slice.

### Capabilities
- **Account Search:** Sourcing target organizations based on name, domain, or ICP criteria.
- **Contact Enrichment:** Discovering and retrieving emails/titles for target personas.
- **Signal Discovery:** Identifying intent signals associated with accounts.

### Authentication
- **API Key:** Standard header-based authentication (`X-Api-Key`).
- **OAuth2:** Support for access/refresh tokens and scope validation (implemented in the framework, configured for Apollo).

## Registry Architecture

The **IntegrationProviderRegistry** manages the lifecycle of provider adapters.

- **Dynamic Loading:** Providers are registered at startup based on configuration.
- **Interface Driven:** Every provider must implement the `IntegrationProvider` interface, ensuring the core platform remains provider-agnostic.

## Data Flow & Normalization

1.  **Request:** A service or agent requests data (e.g., `fetch_accounts`).
2.  **Adapter:** The provider-specific adapter translates the request into the provider's native API format.
3.  **Transport:** The adapter handles HTTP communication, including timeouts and headers.
4.  **Normalization:** The raw JSON response is mapped into platform-standard DTOs (`IntegrationAccountRecord`, `IntegrationContactRecord`).
5.  **Provenance:** Every normalized record retains its `source_provider` and `source_record_id` for auditability.

## Error Handling & Reliability

- **Rate Limiting:** The framework detects `429` responses and raises a typed `IntegrationRateLimitError`. The system can then pause or requeue the job.
- **Circuit Breaking:** (Planned) To prevent cascading failures when a provider is down.
- **Retries:** Configurable retry policies with exponential backoff for transient network errors.

## Adding a New Provider

To add a new provider (e.g., HubSpot):

1.  **Implement Adapter:** Create a new class in `backbone/app/integrations/providers/` that implements the standard provider interface.
2.  **Define Normalization:** Map the new provider's response fields to platform DTOs.
3.  **Register:** Add the provider to the `get_integration_provider_registry` factory in `backbone/app/api/deps.py`.
4.  **Configure:** Add the required API keys or OAuth credentials to the environment variables.

## Observability

- **Integration Runs:** Every sync or execution is recorded in the `integration_runs` table.
- **Metadata:** Request payloads, response status codes, and error messages are persisted for debugging.
- **Provenance:** Reviewers can distinguish seeded demo data from live integration data via the `source_type` and `source_provider` fields.
