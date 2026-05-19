"""Demo data generator for Docker startup."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.gtm import Account, Contact, Persona, Signal
from app.models.identity import User
from app.models.tenant import Tenant
from app.models.workflows import ToolCall, WorkflowRun, WorkflowStep


class DemoDataGenerator:
    """Generates realistic demo data for local development and Docker startup."""

    def __init__(self, session: Session):
        self.session = session

    def generate_all(self) -> dict[str, int]:
        """Generate all demo data and return counts."""
        # Create tenant and users
        tenant_count = self._create_tenants()
        user_count = self._create_users()
        
        # Fetch the demo tenant
        demo_tenant = self.session.query(Tenant).filter_by(slug="acme-corp").first()
        if not demo_tenant:
            return {
                "tenants": tenant_count,
                "users": user_count,
                "accounts": 0,
                "contacts": 0,
                "signals": 0,
                "personas": 0,
                "workflow_runs": 0,
            }

        # Create personas
        persona_count = self._create_personas(demo_tenant.id)
        
        # Create accounts
        account_count = self._create_accounts(demo_tenant.id)
        
        # Create contacts
        contact_count = self._create_contacts(demo_tenant.id)
        
        # Create signals
        signal_count = self._create_signals(demo_tenant.id)
        
        # Create workflow runs
        workflow_count = self._create_workflow_runs(demo_tenant.id)
        
        return {
            "tenants": tenant_count,
            "users": user_count,
            "personas": persona_count,
            "accounts": account_count,
            "contacts": contact_count,
            "signals": signal_count,
            "workflow_runs": workflow_count,
        }

    def _create_tenants(self) -> int:
        """Create demo tenant if not exists."""
        existing = self.session.query(Tenant).filter_by(slug="acme-corp").first()
        if existing:
            return 0
        
        tenant = Tenant(
            id="00000000-0000-0000-0000-000000000001",
            name="Acme Corp",
            slug="acme-corp",
        )
        self.session.add(tenant)
        self.session.flush()
        return 1

    def _create_users(self) -> int:
        """Create demo users if not exist."""
        demo_tenant = self.session.query(Tenant).filter_by(slug="acme-corp").first()
        if not demo_tenant:
            return 0
        
        existing = self.session.query(User).filter_by(
            tenant_id=demo_tenant.id,
            email="user@acme.com"
        ).first()
        if existing:
            return 0
        
        user = User(
            id="00000000-0000-0000-0000-000000000002",
            tenant_id=demo_tenant.id,
            email="user@acme.com",
            full_name="Avery Morgan",
            status="active",
            roles=["seller"],
            permissions={"prospect:read": True, "accounts:read": True},
        )
        self.session.add(user)
        self.session.flush()
        return 1

    def _create_personas(self, tenant_id: str) -> int:
        """Create demo personas."""
        existing_count = self.session.query(Persona).filter_by(tenant_id=tenant_id).count()
        if existing_count > 0:
            return 0
        
        personas_data = [
            {"name": "VP of Sales", "description": "Sales leadership", "buying_committee_role": "champion"},
            {"name": "VP of Marketing", "description": "Marketing leadership", "buying_committee_role": "influencer"},
            {"name": "Director of IT", "description": "IT operations", "buying_committee_role": "technical_evaluator"},
        ]
        
        for data in personas_data:
            persona = Persona(
                tenant_id=tenant_id,
                name=data["name"],
                description=data["description"],
                buying_committee_role=data["buying_committee_role"],
            )
            self.session.add(persona)
        
        self.session.flush()
        return len(personas_data)

    def _create_accounts(self, tenant_id: str) -> int:
        """Create demo accounts."""
        existing_count = self.session.query(Account).filter_by(tenant_id=tenant_id).count()
        if existing_count > 0:
            return 0
        
        account_names = [
            ("Techflow Inc", "techflow.com"),
            ("DataCore Systems", "datacore.io"),
            ("CloudScale Labs", "cloudscale.dev"),
            ("SecureNet Corp", "securenet.com"),
            ("InnovateLabs", "innovatelabs.io"),
            ("MobileFirst Co", "mobilefirst.tech"),
            ("APIFirst Systems", "apifirst.dev"),
            ("AnalyticsHub", "analyticshub.io"),
            ("DevOps Plus", "devopsplus.com"),
            ("InfoSec Pro", "infosecpro.net"),
            ("ConsultX", "consultx.io"),
            ("VentureTech", "venturetech.io"),
            ("E-Commerce Pro", "ecommercepro.com"),
            ("Financial Tech", "fintech.io"),
            ("HealthTech Inc", "healthtech.io"),
            ("RealEstate AI", "realestate-ai.com"),
            ("EdTech Plus", "edtech.io"),
            ("LogisticFlow", "logisticflow.io"),
            ("RetailAI Corp", "retailai.com"),
            ("SaaS Startup", "saasstartup.io"),
            ("Platform X", "platformx.dev"),
            ("Infrastructure Co", "infrastructure.io"),
            ("Quality AI", "qualityai.io"),
            ("DevTools Pro", "devtoolspro.io"),
            ("TestAuto Inc", "testauto.io"),
            ("SecOps Hub", "secops.io"),
            ("MonitorPro", "monitorpro.io"),
            ("AlertSystem", "alertsystem.io"),
            ("DataLake Corp", "datalake.io"),
            ("Analytics Pro", "analyticspro.io"),
            ("Dashboard AI", "dashboardai.io"),
            ("ReportGen", "reportgen.io"),
            ("BiData Corp", "bidata.io"),
            ("ComplianceBot", "compliancebot.io"),
            ("RiskMgmt Pro", "riskmgmt.io"),
            ("AuditFlow", "auditflow.io"),
            ("LegalTech Inc", "legaltech.io"),
            ("Contract AI", "contractai.io"),
            ("Document Pro", "documentpro.io"),
            ("Workflow Plus", "workflowplus.io"),
            ("Automation Hub", "automationhub.io"),
            ("TaskFlow", "taskflow.io"),
            ("CollabTool", "collabtool.io"),
            ("Sync Pro", "syncpro.io"),
            ("TeamWork Inc", "teamwork.io"),
            ("CommHub", "commhub.io"),
            ("MessagePro", "messagepro.io"),
            ("NotifyHub", "notifyhub.io"),
            ("AlertPro", "alertpro.io"),
            ("MonitorAI", "monitorai.io"),
            ("ObserveHub", "observehub.io"),
            ("TelemetryPro", "telemetrypro.io"),
            ("MetricsHub", "metricshub.io"),
            ("CloudCore", "cloudcore.io"),
            ("CyberGuard", "cyberguard.com"),
            ("EdgeSystems", "edgesystems.io"),
            ("FlowState", "flowstate.tech"),
            ("GreenGrid", "greengrid.dev"),
            ("HyperScale", "hyperscale.ai"),
            ("InfiniteData", "infinitedata.io"),
            ("JumpStart", "jumpstart.io"),
            ("KeyScale", "keyscale.dev"),
            ("LayerZero", "layerzero.tech"),
        ]
        
        now = datetime.now(tz=UTC)
        accounts = []
        for name, domain in account_names:
            account = Account(
                tenant_id=tenant_id,
                name=name,
                domain=domain,
                lifecycle_stage="prospect",
                firmographics={
                    "industry": "Software",
                    "annual_revenue": f"${(50 + hash(name) % 900)}M",
                    "employee_count": 50 + (hash(name) % 500),
                },
                custom_fields={},
                source_type="seeded",
                created_at=now - timedelta(days=hash(name) % 30),
                updated_at=now,
            )
            accounts.append(account)
            self.session.add(account)
        
        self.session.flush()
        return len(accounts)

    def _create_contacts(self, tenant_id: str) -> int:
        """Create demo contacts."""
        existing_count = self.session.query(Contact).filter_by(tenant_id=tenant_id).count()
        if existing_count > 0:
            return 0
        
        accounts = self.session.query(Account).filter_by(tenant_id=tenant_id).all()
        personas = self.session.query(Persona).filter_by(tenant_id=tenant_id).all()
        
        if not accounts or not personas:
            return 0
        
        titles = ["VP", "Director", "Manager", "Lead", "Head of"]
        first_names = ["John", "Jane", "Mike", "Sarah", "David", "Emily", "Alex", "Lisa"]
        last_names = ["Smith", "Johnson", "Brown", "Williams", "Jones", "Garcia", "Miller", "Davis"]
        
        contacts_created = 0
        now = datetime.now(tz=UTC)
        
        for account in accounts:
            # Create 2 contacts per account
            for i in range(2):
                first_name = first_names[(hash(account.id) + i) % len(first_names)]
                last_name = last_names[(hash(account.id) + i) % len(last_names)]
                title = titles[(hash(account.id) + i) % len(titles)]
                persona = personas[(hash(account.id) + i) % len(personas)]
                
                contact = Contact(
                    tenant_id=tenant_id,
                    account_id=account.id,
                    persona_id=persona.id,
                    email=f"{first_name.lower()}.{last_name.lower()}@{account.domain}",
                    full_name=f"{first_name} {last_name}",
                    title=title,
                    source_type="seeded",
                    created_at=now - timedelta(days=hash(account.id) % 30),
                    updated_at=now,
                )
                self.session.add(contact)
                contacts_created += 1
        
        self.session.flush()
        return contacts_created

    def _create_signals(self, tenant_id: str) -> int:
        """Create demo signals."""
        existing_count = self.session.query(Signal).filter_by(tenant_id=tenant_id).count()
        if existing_count > 0:
            return 0
        
        accounts = self.session.query(Account).filter_by(tenant_id=tenant_id).all()
        if not accounts:
            return 0
        
        signal_types = [
            "job_change",
            "funding_announcement",
            "website_update",
            "new_product_launch",
            "executive_change",
            "partnership_announcement",
        ]
        
        signals_created = 0
        now = datetime.now(tz=UTC)
        
        for account in accounts:
            # Create 2-3 signals per account
            num_signals = 2 + (hash(account.id) % 2)
            for i in range(num_signals):
                signal_type = signal_types[(hash(account.id) + i) % len(signal_types)]
                strength = 95.0 if i == 0 else 75.0
                signal = Signal(
                    tenant_id=tenant_id,
                    account_id=account.id,
                    signal_type=signal_type,
                    strength=strength,
                    source="crunchbase",
                    payload={
                        "headline": f"{account.name}: {signal_type}",
                        "description": f"Signal detected for {account.name}",
                    },
                    observed_at=now - timedelta(days=(5 - i)),
                    created_at=now - timedelta(days=(5 - i)),
                    updated_at=now,
                )
                self.session.add(signal)
                signals_created += 1
        
        self.session.flush()
        return signals_created

    def _create_workflow_runs(self, tenant_id: str) -> int:
        """Create demo workflow runs."""
        existing_count = self.session.query(WorkflowRun).filter_by(tenant_id=tenant_id).count()
        if existing_count > 0:
            return 0
        
        accounts = self.session.query(Account).filter_by(tenant_id=tenant_id).all()
        if not len(accounts) > 20:
            return 0
        
        workflow_runs_created = 0
        now = datetime.now(tz=UTC)
        
        # Create workflow runs for first 100 accounts
        for account in accounts[:100]:
            workflow_run = WorkflowRun(
                tenant_id=tenant_id,
                workflow_type="prospect_research",
                status="succeeded",
                idempotency_key=str(uuid4()),
                input={
                    "account_id": str(account.id),
                    "account_name": account.name,
                },
                output={
                    "value_hypotheses": 3,
                    "outreach_drafts": 2,
                    "traces": [
                        {
                            "trace_id": f"trace-{workflow_runs_created}-1",
                            "status": "succeeded",
                            "step": "research",
                        }
                    ],
                },
                created_at=now - timedelta(days=hash(account.id) % 7),
                updated_at=now - timedelta(days=hash(account.id) % 7),
            )
            self.session.add(workflow_run)
            self.session.flush()
            
            # Add workflow steps
            step = WorkflowStep(
                tenant_id=tenant_id,
                workflow_run_id=workflow_run.id,
                step_name="research",
                status="completed",
                input={"account_id": str(account.id)},
                output={"findings": "account context and market signals"},
            )
            self.session.add(step)
            
            # Add tool call
            tool_call = ToolCall(
                tenant_id=tenant_id,
                workflow_run_id=workflow_run.id,
                tool_name="account_research",
                status="completed",
                input={"account_id": str(account.id)},
                output={"context": "retrieved"},
            )

            self.session.add(tool_call)
            
            workflow_runs_created += 1
        
        self.session.flush()
        return workflow_runs_created
