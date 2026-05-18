from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.contracts.common import ApprovalStatus, JobStatus, OutreachDraftStatus, WorkflowStatus
from app.contracts.integrations import IntegrationAuthType, IntegrationConnectionStatus, IntegrationExecutionStatus
from app.models.artifacts import OutreachDraft, ValueHypothesis
from app.models.gtm import Account, Contact, Signal
from app.models.identity import AuditEvent, User
from app.models.integrations import IntegrationConnection, IntegrationRun
from app.models.prospect import ICPDefinition
from app.models.tenant import Tenant
from app.models.workflows import ApprovalRequest, WorkflowRun, WorkflowStep


class TestDataGenerator:
    """Generate realistic multi-tenant test data aligned to current models."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.base_time = datetime.now(tz=UTC)

    def _trace_pair(self, prefix: str) -> tuple[str, str]:
        return (f"trace-{prefix}-{uuid.uuid4().hex[:10]}", f"corr-{prefix}-{uuid.uuid4().hex[:10]}")

    def create_test_tenants(self) -> list[Tenant]:
        tenants = [
            Tenant(name="Test Tenant: Enterprise SaaS", slug="test-enterprise-saas"),
            Tenant(name="Test Tenant: Mid-Market Technology", slug="test-midmarket-technology"),
            Tenant(name="Test Tenant: Growth Stage Platform", slug="test-growth-stage-platform"),
        ]
        self.session.add_all(tenants)
        self.session.flush()
        return tenants

    def create_test_users(self, tenants: list[Tenant]) -> dict[str, User]:
        users: dict[str, User] = {}
        for tenant in tenants:
            user = User(
                tenant_id=tenant.id,
                email=f"test-seller@{tenant.slug}.test",
                full_name=f"Test Seller ({tenant.slug})",
                status="active",
                roles=["seller"],
                permissions={"prospect:read": True, "prospect:write": True},
            )
            self.session.add(user)
            users[tenant.id] = user
        self.session.flush()
        return users

    def create_test_accounts(self, tenant: Tenant, *, count: int = 25) -> list[Account]:
        industries = ["Software", "SaaS", "Financial Services", "Healthcare", "Retail"]
        stages = ["prospect", "qualified", "engaged", "proposal", "customer"]
        accounts: list[Account] = []
        for idx in range(count):
            industry = industries[idx % len(industries)]
            created_at = self.base_time - timedelta(days=120 - idx)
            account = Account(
                tenant_id=tenant.id,
                name=f"Test Account {idx + 1} - {industry}",
                domain=f"test-account-{idx + 1:03d}.{tenant.slug}.test",
                lifecycle_stage=stages[idx % len(stages)],
                firmographics={
                    "industry": industry,
                    "employee_count": 75 + idx * 18,
                    "annual_revenue_usd": 4_000_000 + idx * 420_000,
                    "hq_region": "EU" if idx % 2 == 0 else "US",
                },
                custom_fields={"priority_tier": "A" if idx < 5 else "B", "segment": "enterprise" if idx % 3 == 0 else "mid-market"},
                source_type="seeded",
                source_provider="phase7_seed_generator",
                source_record_id=f"{tenant.slug}-acct-{idx + 1:03d}",
                ingestion_timestamp=created_at,
                created_at=created_at,
                updated_at=created_at + timedelta(hours=4),
            )
            self.session.add(account)
            accounts.append(account)
        self.session.flush()
        return accounts

    def create_test_contacts(self, tenant: Tenant, accounts: list[Account], *, contacts_per_account: int = 3) -> list[Contact]:
        titles = [
            "VP Sales",
            "Director of Revenue Operations",
            "Chief Revenue Officer",
            "Account Executive",
            "Head of Partnerships",
        ]
        contacts: list[Contact] = []
        for account_idx, account in enumerate(accounts[:20]):
            for contact_idx in range(contacts_per_account):
                created_at = self.base_time - timedelta(days=90 - account_idx, hours=contact_idx * 3)
                contact = Contact(
                    tenant_id=tenant.id,
                    account_id=account.id,
                    full_name=f"Test Contact {account_idx + 1}-{contact_idx + 1}",
                    email=f"test-contact-{account_idx + 1:02d}-{contact_idx + 1}@{account.domain}",
                    title=titles[(account_idx + contact_idx) % len(titles)],
                    custom_fields={
                        "seniority": "executive" if contact_idx == 0 else "manager",
                        "engagement_score": 62 + contact_idx * 12 + (account_idx % 7),
                    },
                    source_type="seeded",
                    source_provider="phase7_seed_generator",
                    source_record_id=f"{tenant.slug}-contact-{account_idx + 1:02d}-{contact_idx + 1}",
                    ingestion_timestamp=created_at,
                    created_at=created_at,
                    updated_at=created_at + timedelta(hours=2),
                )
                self.session.add(contact)
                contacts.append(contact)
        self.session.flush()
        return contacts

    def create_test_signals(self, tenant: Tenant, accounts: list[Account], *, signals_per_account: int = 2) -> list[Signal]:
        signal_types = ["job_change", "funding_news", "product_launch", "keyword_spike", "web_traffic_spike"]
        sources = ["linkedin", "news", "rss", "web", "intent-api"]
        signals: list[Signal] = []
        for account_idx, account in enumerate(accounts[:20]):
            for signal_idx in range(signals_per_account):
                observed_at = self.base_time - timedelta(days=(account_idx % 25), hours=signal_idx * 5)
                signal_type = signal_types[(account_idx + signal_idx) % len(signal_types)]
                source = sources[(account_idx + signal_idx) % len(sources)]
                signal = Signal(
                    tenant_id=tenant.id,
                    account_id=account.id,
                    source=source,
                    signal_type=signal_type,
                    strength=55 + (signal_idx * 15) + (account_idx % 20),
                    payload={
                        "headline": f"Test Signal: {signal_type} observed for {account.name}",
                        "url": f"https://signals.{source}.test/{uuid.uuid4().hex[:12]}",
                        "confidence": round(0.71 + signal_idx * 0.09, 2),
                    },
                    observed_at=observed_at,
                    source_type="seeded",
                    source_provider="phase7_seed_generator",
                    source_record_id=f"{tenant.slug}-signal-{account_idx + 1:02d}-{signal_idx + 1}",
                    ingestion_timestamp=observed_at,
                    created_at=observed_at,
                    updated_at=observed_at + timedelta(minutes=30),
                )
                self.session.add(signal)
                signals.append(signal)
        self.session.flush()
        return signals

    def create_test_icp(self, tenant: Tenant) -> ICPDefinition:
        icp = ICPDefinition(
            tenant_id=tenant.id,
            name="Test ICP: High-Intent Enterprise Expansion",
            description="Enterprise and upper mid-market companies showing expansion intent in EU or US.",
            status="active",
            criteria={
                "industries": ["Software", "SaaS", "Financial Services"],
                "min_employee_count": 100,
                "revenue_floor_usd": 10_000_000,
                "regions": ["EU", "US"],
            },
            target_personas={
                "primary": ["Chief Revenue Officer", "VP Sales"],
                "secondary": ["Director Revenue Operations", "Head of Partnerships"],
            },
            created_at=self.base_time - timedelta(days=150),
            updated_at=self.base_time - timedelta(days=30),
        )
        self.session.add(icp)
        self.session.flush()
        return icp

    def create_test_workflow_runs(self, tenant: Tenant, icp: ICPDefinition, accounts: list[Account]) -> list[WorkflowRun]:
        statuses = [
            WorkflowStatus.succeeded.value,
            WorkflowStatus.running.value,
            WorkflowStatus.queued.value,
            WorkflowStatus.waiting_for_approval.value,
            WorkflowStatus.failed.value,
        ]
        runs: list[WorkflowRun] = []
        for idx, status in enumerate(statuses):
            trace_id, correlation_id = self._trace_pair(f"workflow-{tenant.slug}-{idx + 1}")
            created_at = self.base_time - timedelta(days=idx + 1, hours=idx)
            output_payload: dict[str, Any] = {
                "trace_id": trace_id,
                "correlation_id": correlation_id,
                "summary": f"Test workflow {idx + 1} for {tenant.slug}",
                "state": status,
            }
            if status == WorkflowStatus.failed.value:
                output_payload["error"] = "Transient integration failure while enriching contacts."
            if status == WorkflowStatus.waiting_for_approval.value:
                output_payload["approval_gate"] = {"reason": "Human review required before external outreach."}

            run = WorkflowRun(
                tenant_id=tenant.id,
                workflow_type="prospect_research",
                status=status,
                icp_id=icp.id,
                account_id=accounts[idx].id,
                idempotency_key=f"phase7-{tenant.slug}-run-{idx + 1}",
                input={
                    "icp_id": icp.id,
                    "account_id": accounts[idx].id,
                    "trace_id": trace_id,
                    "correlation_id": correlation_id,
                    "requested_by": f"test-seller@{tenant.slug}.test",
                },
                output=output_payload,
                last_heartbeat_at=self.base_time - timedelta(minutes=idx * 3),
                created_at=created_at,
                updated_at=created_at + timedelta(minutes=8),
            )
            self.session.add(run)
            runs.append(run)
        self.session.flush()
        return runs

    def create_test_workflow_steps(self, run: WorkflowRun) -> list[WorkflowStep]:
        trace_id = str(run.output.get("trace_id", "trace-unavailable"))
        correlation_id = str(run.output.get("correlation_id", "corr-unavailable"))

        step_templates: list[tuple[str, str]] = [("research", JobStatus.completed.value), ("contact_enrichment", JobStatus.completed.value)]
        if run.status == WorkflowStatus.running.value:
            step_templates = [("research", JobStatus.completed.value), ("contact_enrichment", JobStatus.running.value)]
        elif run.status == WorkflowStatus.queued.value:
            step_templates = [("research", JobStatus.pending.value)]
        elif run.status == WorkflowStatus.waiting_for_approval.value:
            step_templates = [("research", JobStatus.completed.value), ("hypothesis_generation", JobStatus.completed.value)]
        elif run.status == WorkflowStatus.failed.value:
            step_templates = [("research", JobStatus.completed.value), ("contact_enrichment", JobStatus.failed.value)]

        steps: list[WorkflowStep] = []
        for idx, (step_name, step_status) in enumerate(step_templates):
            step = WorkflowStep(
                tenant_id=run.tenant_id,
                workflow_run_id=run.id,
                step_name=step_name,
                status=step_status,
                input={"trace_id": trace_id, "correlation_id": correlation_id, "step_index": idx},
                output={
                    "trace_id": trace_id,
                    "correlation_id": correlation_id,
                    "status": step_status,
                    "decision_summary": f"{step_name} completed for workflow {run.id}",
                },
                error_message="LLM timeout while contacting provider." if step_status == JobStatus.failed.value else None,
                created_at=run.created_at + timedelta(minutes=idx),
                updated_at=run.created_at + timedelta(minutes=idx + 1),
            )
            self.session.add(step)
            steps.append(step)
        self.session.flush()
        return steps

    def create_test_hypotheses(self, run: WorkflowRun) -> list[ValueHypothesis]:
        if run.status not in (WorkflowStatus.succeeded.value, WorkflowStatus.waiting_for_approval.value):
            return []
        hypothesis = ValueHypothesis(
            tenant_id=run.tenant_id,
            workflow_run_id=run.id,
            account_id=run.account_id,
            contact_id=None,
            generated_by_agent="value_hypothesis_agent",
            generated_at=self.base_time - timedelta(hours=6),
            confidence_score=84,
            title="Test Hypothesis: Expansion readiness for enterprise segment",
            hypothesis="Signals indicate readiness to adopt expanded outbound motion in priority regions.",
            metadata_={"trace_id": run.output.get("trace_id"), "correlation_id": run.output.get("correlation_id"), "evidence_count": 3},
            created_at=self.base_time - timedelta(hours=6),
            updated_at=self.base_time - timedelta(hours=5, minutes=30),
        )
        self.session.add(hypothesis)
        self.session.flush()
        return [hypothesis]

    def create_test_outreach_drafts(self, run: WorkflowRun) -> list[OutreachDraft]:
        if run.status not in (WorkflowStatus.succeeded.value, WorkflowStatus.waiting_for_approval.value):
            return []
        status = OutreachDraftStatus.pending_approval.value if run.status == WorkflowStatus.waiting_for_approval.value else OutreachDraftStatus.draft.value
        draft = OutreachDraft(
            tenant_id=run.tenant_id,
            workflow_run_id=run.id,
            account_id=run.account_id,
            contact_id=None,
            generated_by_agent="outreach_agent",
            generated_at=self.base_time - timedelta(hours=4),
            confidence_score=82,
            subject="Test Outreach: Revenue expansion priorities for this quarter",
            body="Your current hiring and product momentum suggest a strong fit for a focused expansion initiative.",
            status=status,
            metadata_={"trace_id": run.output.get("trace_id"), "correlation_id": run.output.get("correlation_id"), "channel": "email"},
            created_at=self.base_time - timedelta(hours=4),
            updated_at=self.base_time - timedelta(hours=3, minutes=45),
        )
        self.session.add(draft)
        self.session.flush()
        return [draft]

    def create_test_approval_requests(self, run: WorkflowRun, reviewer_user_id: str | None) -> list[ApprovalRequest]:
        if run.status != WorkflowStatus.waiting_for_approval.value:
            return []
        approval = ApprovalRequest(
            tenant_id=run.tenant_id,
            workflow_run_id=run.id,
            workflow_step_id=None,
            status=ApprovalStatus.pending.value,
            reviewer_user_id=reviewer_user_id,
            reviewed_at=None,
            reason="Human approval required before sending outreach to this account.",
            decision_payload={
                "trace_id": run.output.get("trace_id"),
                "correlation_id": run.output.get("correlation_id"),
                "risk_level": "medium",
                "requested_at": (self.base_time - timedelta(hours=2)).isoformat(),
            },
            created_at=self.base_time - timedelta(hours=2),
            updated_at=self.base_time - timedelta(hours=2),
        )
        self.session.add(approval)
        self.session.flush()
        return [approval]

    def create_test_integration_connections(self, tenant: Tenant) -> list[IntegrationConnection]:
        live_connection = IntegrationConnection(
            tenant_id=tenant.id,
            provider="apollo",
            connection_name="default",
            is_default=True,
            auth_type=IntegrationAuthType.api_key.value,
            status=IntegrationConnectionStatus.live.value,
            scopes=["accounts.read", "contacts.read"],
            encrypted_credentials=b"phase7-seeded-encrypted-key",
            expires_at=None,
            health={"status": "healthy", "last_check_at": (self.base_time - timedelta(minutes=10)).isoformat()},
            created_at=self.base_time - timedelta(days=15),
            updated_at=self.base_time - timedelta(minutes=10),
        )
        failed_connection = IntegrationConnection(
            tenant_id=tenant.id,
            provider="hubspot",
            connection_name="secondary",
            is_default=False,
            auth_type=IntegrationAuthType.oauth2.value,
            status=IntegrationConnectionStatus.failed.value,
            scopes=["crm.objects.contacts.read"],
            encrypted_credentials=b"phase7-seeded-oauth-token",
            expires_at=self.base_time - timedelta(days=2),
            health={"status": "unhealthy", "error": "OAuth token expired", "last_check_at": (self.base_time - timedelta(hours=3)).isoformat()},
            created_at=self.base_time - timedelta(days=12),
            updated_at=self.base_time - timedelta(hours=3),
        )
        self.session.add_all([live_connection, failed_connection])
        self.session.flush()
        return [live_connection, failed_connection]

    def create_test_integration_runs(self, connection: IntegrationConnection) -> list[IntegrationRun]:
        trace_id, correlation_id = self._trace_pair(f"integration-{connection.provider}")
        status = IntegrationExecutionStatus.completed.value if connection.status == IntegrationConnectionStatus.live.value else IntegrationExecutionStatus.failed.value
        error_message = None if status == IntegrationExecutionStatus.completed.value else "Authentication expired during provider call."
        started_at = self.base_time - timedelta(minutes=35)
        finished_at = self.base_time - timedelta(minutes=31)

        run = IntegrationRun(
            tenant_id=connection.tenant_id,
            connection_id=connection.id,
            provider=connection.provider,
            status=status,
            request_metadata={
                "operation": "sync",
                "trace_id": trace_id,
                "correlation_id": correlation_id,
                "source_type": "accounts",
            },
            error_message=error_message,
            counts={
                "counts": {"records_fetched": 18, "records_normalized": 18, "records_written": 17, "error_count": 0 if error_message is None else 1},
                "response_metadata": {"provider_request_id": uuid.uuid4().hex[:14]},
                "timing": {
                    "started_at": started_at.isoformat(),
                    "finished_at": finished_at.isoformat(),
                    "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
                },
            },
            created_at=started_at,
            updated_at=finished_at,
        )
        self.session.add(run)
        self.session.flush()
        return [run]

    def create_test_audit_events(self, tenant_id: str, actor_user_id: str, workflow_runs: list[WorkflowRun]) -> list[AuditEvent]:
        events: list[AuditEvent] = []
        for run in workflow_runs:
            event = AuditEvent(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                action="workflow_seeded",
                resource_type="workflow_run",
                resource_id=run.id,
                metadata_={
                    "status": run.status,
                    "trace_id": run.output.get("trace_id"),
                    "correlation_id": run.output.get("correlation_id"),
                    "workflow_type": run.workflow_type,
                },
                created_at=run.created_at + timedelta(minutes=1),
            )
            self.session.add(event)
            events.append(event)
        self.session.flush()
        return events

    def generate_all(self) -> dict[str, Any]:
        results: dict[str, Any] = {
            "tenants": [],
            "users": {},
            "accounts": {},
            "contacts": {},
            "signals": {},
            "icps": {},
            "workflow_runs": {},
            "workflow_steps": {},
            "hypotheses": {},
            "outreach_drafts": {},
            "approval_requests": {},
            "integration_connections": {},
            "integration_runs": {},
            "audit_events": {},
        }

        tenants = self.create_test_tenants()
        users = self.create_test_users(tenants)
        results["tenants"] = tenants
        results["users"] = users

        for tenant in tenants:
            accounts = self.create_test_accounts(tenant, count=25)
            contacts = self.create_test_contacts(tenant, accounts, contacts_per_account=3)
            signals = self.create_test_signals(tenant, accounts, signals_per_account=2)
            icp = self.create_test_icp(tenant)
            workflow_runs = self.create_test_workflow_runs(tenant, icp, accounts)
            integration_connections = self.create_test_integration_connections(tenant)

            workflow_steps: list[WorkflowStep] = []
            hypotheses: list[ValueHypothesis] = []
            outreach_drafts: list[OutreachDraft] = []
            approval_requests: list[ApprovalRequest] = []
            for run in workflow_runs:
                workflow_steps.extend(self.create_test_workflow_steps(run))
                hypotheses.extend(self.create_test_hypotheses(run))
                outreach_drafts.extend(self.create_test_outreach_drafts(run))
                approval_requests.extend(self.create_test_approval_requests(run, users[tenant.id].id))

            integration_runs: list[IntegrationRun] = []
            for connection in integration_connections:
                integration_runs.extend(self.create_test_integration_runs(connection))

            audit_events = self.create_test_audit_events(tenant.id, users[tenant.id].id, workflow_runs)

            results["accounts"][tenant.id] = accounts
            results["contacts"][tenant.id] = contacts
            results["signals"][tenant.id] = signals
            results["icps"][tenant.id] = icp
            results["workflow_runs"][tenant.id] = workflow_runs
            results["workflow_steps"][tenant.id] = workflow_steps
            results["hypotheses"][tenant.id] = hypotheses
            results["outreach_drafts"][tenant.id] = outreach_drafts
            results["approval_requests"][tenant.id] = approval_requests
            results["integration_connections"][tenant.id] = integration_connections
            results["integration_runs"][tenant.id] = integration_runs
            results["audit_events"][tenant.id] = audit_events

        self.session.commit()
        return results


def generate_test_data(session: Session) -> dict[str, Any]:
    generator = TestDataGenerator(session)
    return generator.generate_all()
