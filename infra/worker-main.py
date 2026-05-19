from __future__ import annotations

import logging
import time

from app.api.deps import get_integration_provider_registry
from app.audit.service import SqlAuditService
from app.core.config import get_settings
from app.core.tenancy import TenantContext
from app.integrations.registry import IntegrationProviderRegistry
from app.repositories.audit_repository import SqlAuditEventRepository
from app.repositories.integration_repository import SqlIntegrationRepository
from app.repositories.prospect_workflow_repository import SqlProspectWorkflowRepository
from app.services.integrations import IntegrationService
from app.services.prospect import ProspectWorkflowService
from app.storage.db import session_scope
from app.workers.workflow import ProspectWorkflowWorker


logger = logging.getLogger("gtm.worker")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def build_runtime(session):
    settings = get_settings()
    audit_service = SqlAuditService(SqlAuditEventRepository(session))
    registry: IntegrationProviderRegistry = get_integration_provider_registry(settings)
    integration_service = IntegrationService(
        repository=SqlIntegrationRepository(session),
        registry=registry,
        audit_service=audit_service,
        settings=settings,
    )
    workflow_repository = SqlProspectWorkflowRepository(session)
    service = ProspectWorkflowService(
        repository=workflow_repository,
        audit_service=audit_service,
        integration_service=integration_service,
    )
    worker = ProspectWorkflowWorker(workflow_repository, settings=settings)
    return worker, service


def main() -> None:
    settings = get_settings()
    backend = None
    while True:
        processed = False
        with session_scope() as session:
            worker, service = build_runtime(session)
            backend = backend or worker._backend
            while True:
                job = backend.pop()
                if job is None:
                    break
                processed = True
                try:
                    context = TenantContext(
                        tenant_id=job.tenant_id,
                        actor_user_id="system",
                        roles=(),
                        permissions=(),
                    )
                    worker._process_job(job, context=context, execute=service._workflow_engine().execute, requeue_on_retry=True)
                except Exception as exc:  # pragma: no cover - runtime guard
                    logger.exception("workflow job processing failed; requeuing")
                    backend.enqueue(job)
                    continue
        if not processed:
            time.sleep(2)


if __name__ == "__main__":
    main()
