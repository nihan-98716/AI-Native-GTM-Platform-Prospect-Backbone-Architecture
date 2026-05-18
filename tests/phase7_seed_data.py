"""
Phase 7 Test Data Generator

Creates realistic multi-tenant test data for end-to-end validation.

Structure:
- 3 test tenants with different profiles
- Accounts, Contacts, Signals with realistic business context
- Workflow runs at various states (completed, running, queued, failed, waiting_for_approval)
- Integration connections (connected, failed, syncing)
- Audit trail for all operations

Constraints:
- Uses "test-" prefixes for professional identification
- Maintains tenant ownership and provenance
- Includes trace_ids, correlation_ids, timestamps
- No repetitive or placeholder content
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.contracts.common import (
    ApprovalStatus,
    IntegrationStatus,
    JobStatus,
    OutreachDraftStatus,
    WorkflowStatus,
)
from app.models.gtm import Account, Contact, ICP, Signal
from app.models.identity import User
from app.models.integrations import IntegrationConnection, IntegrationRun
from app.models.prospect import (
    Hypothesis,
    OutreachDraft,
    WorkflowRun,
    WorkflowStep,
    ApprovalCheckpoint,
)
from app.models.tenant import Tenant


class TestDataGenerator:
    """Generates realistic test data for Phase 7 validation."""

    def __init__(self, session: Session):
        self.session = session
        self.base_time = datetime.now(tz=UTC)

    def create_test_tenants(self) -> list[Tenant]:
        """Create 3 test tenants representing different company profiles."""
        tenants = [
            Tenant(
                name="Test Tenant: Enterprise SaaS",
                slug="test-enterprise-saas",
                status="active",
            ),
            Tenant(
                name="Test Tenant: Mid-Market Tech",
                slug="test-midmarket-tech",
                status="active",
            ),
            Tenant(
                name="Test Tenant: Growth Stage",
                slug="test-growth-stage",
                status="active",
            ),
        ]
        self.session.add_all(tenants)
        self.session.flush()
        return tenants

    def create_test_users(self, tenants: list[Tenant]) -> dict[str, User]:
        """Create test users per tenant."""
        users = {}
        for tenant in tenants:
            user = User(
                tenant_id=tenant.id,
                email=f"test-seller@{tenant.slug}.test",
                full_name=f"Test Sales Rep - {tenant.name}",
                status="active",
                roles=["seller"],
                permissions={"prospect:read": True, "prospect:write": True},
            )
            self.session.add(user)
            users[tenant.id] = user
        self.session.flush()
        return users

    def create_test_accounts(self, tenant: Tenant, count: int = 20) -> list[Account]:
        """Create realistic test accounts for a tenant."""
        accounts = []
        industries = ["Software", "SaaS", "Financial Services", "Healthcare", "Retail"]
        company_types = [
            "Public",
            "Private",
            "Series D",
            "Series C",
            "Series B",
        ]

        for i in range(count):
            industry = industries[i % len(industries)]
            company_type = company_types[i % len(company_types)]

            account = Account(
                tenant_id=tenant.id,
                name=f"Test Corp {i}: {industry} Ltd",
                domain=f"test-corp-{i:03d}.test",
                status="active",
                custom_fields={
                    "industry": industry,
                    "company_type": company_type,
                    "employee_count": 100 + (i * 50),
                    "annual_revenue": f"${(5 + i) * 10}M",
                    "ipo_date": None,
                },
            )
            self.session.add(account)
            accounts.append(account)

        self.session.flush()
        return accounts

    def create_test_contacts(
        self, tenant: Tenant, accounts: list[Account], contacts_per_account: int = 3
    ) -> list[Contact]:
        """Create realistic test contacts for accounts."""
        contacts = []
        titles = [
            "VP of Sales",
            "Sales Director",
            "Enterprise Account Executive",
            "Chief Revenue Officer",
            "Sales Manager",
        ]

        for account_idx, account in enumerate(accounts[:15]):
            for contact_idx in range(contacts_per_account):
                title = titles[
                    (account_idx * contacts_per_account + contact_idx) % len(titles)
                ]
                contact = Contact(
                    tenant_id=tenant.id,
                    account_id=account.id,
                    first_name=f"Test-{account_idx:02d}-Contact-{contact_idx}",
                    last_name=f"Professional",
                    title=title,
                    email=f"test-contact-{account_idx:02d}-{contact_idx}@{account.domain}",
                    phone=f"+1-555-{1000 + account_idx}-{contact_idx:04d}",
                    status="active",
                    custom_fields={
                        "seniority_level": "executive" if contact_idx == 0 else "director",
                        "linkedin_profile": f"https://linkedin.test/in/test-contact-{account_idx:02d}-{contact_idx}",
                        "engagement_score": 65 + (contact_idx * 10),
                    },
                )
                self.session.add(contact)
                contacts.append(contact)

        self.session.flush()
        return contacts

    def create_test_icp(self, tenant: Tenant) -> ICP:
        """Create a test ICP definition."""
        icp = ICP(
            tenant_id=tenant.id,
            name="Test ICP: Enterprise SaaS Target",
            description="Enterprise software companies with 100+ employees targeting European expansion",
            criteria={
                "industry": ["Software", "SaaS", "Financial Services"],
                "min_employees": 100,
                "company_types": ["Public", "Series C+"],
                "geographies": ["EU", "US"],
                "revenue_range": "$10M-$500M",
            },
            status="active",
        )
        self.session.add(icp)
        self.session.flush()
        return icp

    def create_test_signals(
        self, tenant: Tenant, accounts: list[Account], signals_per_account: int = 2
    ) -> list[Signal]:
        """Create realistic intent signals for accounts."""
        signals = []
        signal_types = [
            "job_change",
            "funding_news",
            "product_launch",
            "web_traffic_spike",
            "keyword_search",
        ]
        sources = ["linkedin", "news", "web", "rss", "api"]

        for account_idx, account in enumerate(accounts[:15]):
            for signal_idx in range(signals_per_account):
                signal_type = signal_types[
                    (account_idx * signals_per_account + signal_idx) % len(signal_types)
                ]
                source = sources[
                    (account_idx * signals_per_account + signal_idx) % len(sources)
                ]

                signal = Signal(
                    tenant_id=tenant.id,
                    account_id=account.id,
                    signal_type=signal_type,
                    source=source,
                    strength=50 + (signal_idx * 20),
                    timestamp=self.base_time - timedelta(days=30 + signal_idx),
                    custom_fields={
                        "headline": f"Test Signal: {signal_type} detected on {account.name}",
                        "url": f"https://{source}.test/signals/{uuid.uuid4().hex[:8]}",
                        "confidence_score": 0.75 + (signal_idx * 0.1),
                    },
                )
                self.session.add(signal)
                signals.append(signal)

        self.session.flush()
        return signals

    def create_test_workflow_runs(
        self, tenant: Tenant, icp: ICP, accounts: list[Account]
    ) -> list[WorkflowRun]:
        """Create workflow runs in various states."""
        runs = []

        # Completed workflow
        run_completed = WorkflowRun(
            tenant_id=tenant.id,
            icp_id=icp.id,
            account_id=accounts[0].id,
            status=WorkflowStatus.succeeded,
            workflow_type="prospect_research",
            created_at=self.base_time - timedelta(days=5),
            started_at=self.base_time - timedelta(days=5),
            completed_at=self.base_time - timedelta(days=4, hours=2),
            estimated_cost_usd=0.45,
            estimated_latency_ms=12500,
            output={
                "ranked_accounts": [{"account_id": accounts[0].id, "rank_score": 92}]
            },
        )
        self.session.add(run_completed)
        runs.append(run_completed)

        # Running workflow
        run_running = WorkflowRun(
            tenant_id=tenant.id,
            icp_id=icp.id,
            account_id=accounts[1].id,
            status=WorkflowStatus.running,
            workflow_type="prospect_research",
            created_at=self.base_time - timedelta(hours=2),
            started_at=self.base_time - timedelta(hours=1, minutes=45),
            estimated_cost_usd=0.15,
            estimated_latency_ms=3200,
        )
        self.session.add(run_running)
        runs.append(run_running)

        # Queued for retry
        run_queued = WorkflowRun(
            tenant_id=tenant.id,
            icp_id=icp.id,
            account_id=accounts[2].id,
            status=WorkflowStatus.queued,
            workflow_type="prospect_research",
            created_at=self.base_time - timedelta(minutes=30),
            estimated_cost_usd=0.0,
            estimated_latency_ms=0,
        )
        self.session.add(run_queued)
        runs.append(run_queued)

        # Waiting for approval
        run_approval = WorkflowRun(
            tenant_id=tenant.id,
            icp_id=icp.id,
            account_id=accounts[3].id,
            status=WorkflowStatus.waiting_for_approval,
            workflow_type="prospect_research",
            approval_status=ApprovalStatus.pending,
            created_at=self.base_time - timedelta(days=1),
            started_at=self.base_time - timedelta(days=1),
            estimated_cost_usd=0.42,
            estimated_latency_ms=11800,
            output={
                "hypotheses": [
                    {
                        "account_id": accounts[3].id,
                        "title": "Test Hypothesis: Expansion Opportunity",
                        "confidence_score": 0.87,
                    }
                ]
            },
        )
        self.session.add(run_approval)
        runs.append(run_approval)

        # Failed workflow
        run_failed = WorkflowRun(
            tenant_id=tenant.id,
            icp_id=icp.id,
            account_id=accounts[4].id,
            status=WorkflowStatus.failed,
            workflow_type="prospect_research",
            created_at=self.base_time - timedelta(days=2),
            started_at=self.base_time - timedelta(days=2),
            completed_at=self.base_time - timedelta(days=2, hours=1),
            estimated_cost_usd=0.12,
            estimated_latency_ms=4100,
            output={"error": "Integration connection failed during contact enrichment"},
        )
        self.session.add(run_failed)
        runs.append(run_failed)

        self.session.flush()
        return runs

    def create_test_workflow_steps(
        self, run: WorkflowRun
    ) -> list[WorkflowStep]:
        """Create workflow steps for a completed run."""
        if run.status != WorkflowStatus.succeeded:
            return []

        steps = [
            WorkflowStep(
                tenant_id=run.tenant_id,
                workflow_run_id=run.id,
                step_name="research",
                status=JobStatus.completed,
                trace_id=f"trace-research-{uuid.uuid4().hex[:8]}",
                correlation_id=f"corr-{uuid.uuid4().hex[:8]}",
                input_payload={"icp_id": str(run.icp_id)},
                output_payload={"ranked_accounts": [{"account_id": str(run.account_id), "rank_score": 92}]},
                created_at=run.started_at,
                completed_at=run.started_at + timedelta(seconds=5),
            ),
            WorkflowStep(
                tenant_id=run.tenant_id,
                workflow_run_id=run.id,
                step_name="contact_enrichment",
                status=JobStatus.completed,
                trace_id=f"trace-contact-{uuid.uuid4().hex[:8]}",
                correlation_id=f"corr-{uuid.uuid4().hex[:8]}",
                input_payload={"account_ids": [str(run.account_id)]},
                output_payload={"enriched_contacts": [{"contact_id": "test-contact-1", "completeness_score": 95}]},
                created_at=run.started_at + timedelta(seconds=5),
                completed_at=run.started_at + timedelta(seconds=15),
            ),
        ]
        self.session.add_all(steps)
        self.session.flush()
        return steps

    def create_test_hypotheses(
        self, tenant: Tenant, run: WorkflowRun
    ) -> list[Hypothesis]:
        """Create test hypotheses for a workflow run."""
        if not run.account_id:
            return []

        hypotheses = [
            Hypothesis(
                tenant_id=tenant.id,
                workflow_run_id=run.id,
                account_id=run.account_id,
                contact_id=None,
                title=f"Test Hypothesis: Expansion Opportunity at {run.account_id}",
                hypothesis="This account shows strong buying signals for enterprise expansion in the EU market.",
                supporting_evidence=["job_change:CEO", "funding_news:Series D", "web_traffic_spike"],
                confidence_score=0.87,
                generated_by_agent="ValueHypothesisAgent",
            ),
        ]
        self.session.add_all(hypotheses)
        self.session.flush()
        return hypotheses

    def create_test_outreach_drafts(
        self, tenant: Tenant, run: WorkflowRun
    ) -> list[OutreachDraft]:
        """Create test outreach drafts for a workflow run."""
        if run.status != WorkflowStatus.succeeded:
            return []

        drafts = [
            OutreachDraft(
                tenant_id=tenant.id,
                workflow_run_id=run.id,
                account_id=run.account_id,
                contact_id=None,
                subject="Test Outreach: European Expansion Opportunity",
                body="We've identified a significant opportunity for your organization based on recent market signals and your expansion strategy...",
                status=OutreachDraftStatus.draft,
                generated_by_agent="OutreachAgent",
                confidence_score=0.85,
            ),
        ]
        self.session.add_all(drafts)
        self.session.flush()
        return drafts

    def create_test_approval_checkpoints(
        self, tenant: Tenant, run: WorkflowRun
    ) -> list[ApprovalCheckpoint]:
        """Create approval checkpoints for runs waiting approval."""
        if run.status != WorkflowStatus.waiting_for_approval:
            return []

        checkpoint = ApprovalCheckpoint(
            tenant_id=tenant.id,
            workflow_run_id=run.id,
            approval_request_id=str(uuid.uuid4()),
            reason="Human review required: Evaluate hypotheses before outreach to this account",
            status=ApprovalStatus.pending,
            created_at=self.base_time - timedelta(hours=4),
            expires_at=self.base_time + timedelta(days=7),
        )
        self.session.add(checkpoint)
        self.session.flush()
        return [checkpoint]

    def create_test_integration_connections(
        self, tenant: Tenant
    ) -> list[IntegrationConnection]:
        """Create test integration connections in various states."""
        connections = [
            IntegrationConnection(
                tenant_id=tenant.id,
                provider_name="apollo",
                status=IntegrationStatus.live,
                auth_type="api_key",
                config={
                    "api_key_encrypted": "test-encrypted-key-1",
                    "workspace_id": "test-workspace-123",
                },
                health_check_at=self.base_time - timedelta(minutes=5),
                health_status="healthy",
                last_sync_at=self.base_time - timedelta(minutes=15),
                sync_status="idle",
            ),
            IntegrationConnection(
                tenant_id=tenant.id,
                provider_name="hubspot",
                status=IntegrationStatus.failed,
                auth_type="oauth",
                config={"oauth_token_encrypted": "test-encrypted-token"},
                health_check_at=self.base_time - timedelta(hours=2),
                health_status="unhealthy",
                health_error="Authentication token expired",
                last_sync_at=self.base_time - timedelta(days=3),
                sync_status="failed",
            ),
        ]
        self.session.add_all(connections)
        self.session.flush()
        return connections

    def create_test_integration_runs(
        self, tenant: Tenant, connection: IntegrationConnection, account_count: int = 5
    ) -> list[IntegrationRun]:
        """Create test integration runs."""
        if connection.status != IntegrationStatus.live:
            return []

        runs = [
            IntegrationRun(
                tenant_id=tenant.id,
                integration_connection_id=connection.id,
                provider_name=connection.provider_name,
                status=JobStatus.completed,
                sync_type="accounts_list",
                records_fetched=account_count,
                records_normalized=account_count,
                records_written=account_count - 1,
                error_count=0,
                started_at=self.base_time - timedelta(minutes=30),
                completed_at=self.base_time - timedelta(minutes=25),
                metadata={
                    "request_id": str(uuid.uuid4()),
                    "trace_id": f"trace-sync-{uuid.uuid4().hex[:8]}",
                },
            ),
        ]
        self.session.add_all(runs)
        self.session.flush()
        return runs

    def generate_all(self) -> dict[str, Any]:
        """Generate complete test data suite."""
        results = {
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
            "approval_checkpoints": {},
            "integration_connections": {},
            "integration_runs": {},
        }

        # Create tenants and users
        tenants = self.create_test_tenants()
        results["tenants"] = tenants
        users = self.create_test_users(tenants)
        results["users"] = users

        # Create GTM entities per tenant
        for tenant in tenants:
            accounts = self.create_test_accounts(tenant, count=25)
            results["accounts"][tenant.id] = accounts

            contacts = self.create_test_contacts(tenant, accounts)
            results["contacts"][tenant.id] = contacts

            icp = self.create_test_icp(tenant)
            results["icps"][tenant.id] = icp

            signals = self.create_test_signals(tenant, accounts)
            results["signals"][tenant.id] = signals

            # Create workflow runs
            runs = self.create_test_workflow_runs(tenant, icp, accounts)
            results["workflow_runs"][tenant.id] = runs

            # Create supporting data for runs
            for run in runs:
                steps = self.create_test_workflow_steps(run)
                if steps:
                    results["workflow_steps"].setdefault(tenant.id, []).extend(steps)

                hypotheses = self.create_test_hypotheses(tenant, run)
                if hypotheses:
                    results["hypotheses"].setdefault(tenant.id, []).extend(hypotheses)

                drafts = self.create_test_outreach_drafts(tenant, run)
                if drafts:
                    results["outreach_drafts"].setdefault(tenant.id, []).extend(drafts)

                checkpoints = self.create_test_approval_checkpoints(tenant, run)
                if checkpoints:
                    results["approval_checkpoints"].setdefault(tenant.id, []).extend(
                        checkpoints
                    )

            # Create integration connections and runs
            connections = self.create_test_integration_connections(tenant)
            results["integration_connections"][tenant.id] = connections

            for connection in connections:
                runs = self.create_test_integration_runs(
                    tenant, connection, len(accounts)
                )
                if runs:
                    results["integration_runs"].setdefault(tenant.id, []).extend(runs)

        self.session.commit()
        return results


def generate_test_data(session: Session) -> dict[str, Any]:
    """Generate complete Phase 7 test data."""
    generator = TestDataGenerator(session)
    return generator.generate_all()
