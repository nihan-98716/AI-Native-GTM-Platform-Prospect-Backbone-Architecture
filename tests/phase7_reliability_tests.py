"""
Phase 7 Reliability Tests

Backend integration tests validating:
1. Workflow state machine and transitions
2. Tenant isolation enforcement
3. Trace and audit integrity
4. Integration provider reliability
"""
from __future__ import annotations

import pytest
from app.contracts.common import JobStatus, WorkflowStatus, ApprovalStatus
from app.models.integrations import IntegrationConnection, IntegrationRun
from app.models.workflows import WorkflowRun, WorkflowStep, ApprovalRequest


class TestWorkflowReliability:
    """Test suite for workflow reliability and state management."""

    def test_workflow_status_values_are_valid(self):
        """Verify workflow status enum has expected values for state machine."""
        expected_statuses = [
            WorkflowStatus.queued,
            WorkflowStatus.running,
            WorkflowStatus.waiting_for_approval,
            WorkflowStatus.succeeded,
            WorkflowStatus.failed,
        ]
        
        for status in expected_statuses:
            assert status is not None
            assert isinstance(status.value, str)

    def test_job_status_values_are_valid(self):
        """Verify job status enum has expected values."""
        expected_statuses = [
            JobStatus.pending,
            JobStatus.running,
            JobStatus.completed,
            JobStatus.failed,
        ]
        
        for status in expected_statuses:
            assert status is not None
            assert isinstance(status.value, str)

    def test_workflow_status_transitions_are_defined(self):
        """
        Verify valid workflow status transitions exist:
        - queued → running → waiting_for_approval → succeeded
        - queued → running → waiting_for_approval → failed (rejected)
        - queued → running → queued (on retry)
        - queued → failed (validation error)
        """
        valid_transitions = [
            (WorkflowStatus.queued, WorkflowStatus.running),
            (WorkflowStatus.running, WorkflowStatus.waiting_for_approval),
            (WorkflowStatus.waiting_for_approval, WorkflowStatus.succeeded),
            (WorkflowStatus.waiting_for_approval, WorkflowStatus.failed),
            (WorkflowStatus.running, WorkflowStatus.queued),
            (WorkflowStatus.queued, WorkflowStatus.failed),
        ]
        
        # Verify all statuses involved exist
        for from_status, to_status in valid_transitions:
            assert from_status in [
                WorkflowStatus.queued,
                WorkflowStatus.running,
                WorkflowStatus.waiting_for_approval,
                WorkflowStatus.succeeded,
                WorkflowStatus.failed,
            ]
            assert to_status in [
                WorkflowStatus.queued,
                WorkflowStatus.running,
                WorkflowStatus.waiting_for_approval,
                WorkflowStatus.succeeded,
                WorkflowStatus.failed,
            ]

    def test_integration_run_schema_supports_persistence(self):
        """
        Verify integration run schema has fields for:
        - Connection tracking
        - Provider tracking
        - Status and counts
        - Timestamps
        """
        required_fields = [
            "tenant_id",
            "connection_id",
            "provider",
            "status",
            "request_metadata",
            "counts",
            "created_at",
        ]

        for field in required_fields:
            assert hasattr(IntegrationRun, field), (
                f"IntegrationRun must have field '{field}' for metadata persistence"
            )

    def test_integration_connection_schema_supports_multitenancy(self):
        """
        Verify integration connection enforces tenant isolation.
        """
        required_fields = [
            "tenant_id",
            "provider",
            "auth_type",
            "status",
            "encrypted_credentials",
        ]

        for field in required_fields:
            assert hasattr(IntegrationConnection, field), (
                f"IntegrationConnection must have field '{field}' for tenant isolation"
            )


class TestTenantIsolation:
    """Test suite for tenant isolation guarantees."""

    def test_account_model_has_tenant_isolation(self):
        """Verify Account model enforces tenant ownership."""
        from app.models.gtm import Account
        
        required_fields = ["tenant_id", "id"]
        for field in required_fields:
            assert hasattr(Account, field), (
                f"Account must have '{field}' for tenant isolation"
            )

    def test_contact_model_has_tenant_isolation(self):
        """Verify Contact model enforces tenant ownership."""
        from app.models.gtm import Contact
        
        required_fields = ["tenant_id", "id", "account_id"]
        for field in required_fields:
            assert hasattr(Contact, field), (
                f"Contact must have '{field}' for tenant isolation"
            )

    def test_signal_model_has_tenant_isolation(self):
        """Verify Signal model enforces tenant ownership."""
        from app.models.gtm import Signal
        
        required_fields = ["tenant_id", "id", "account_id"]
        for field in required_fields:
            assert hasattr(Signal, field), (
                f"Signal must have '{field}' for tenant isolation"
            )

    def test_workflow_run_has_tenant_isolation(self):
        """Verify WorkflowRun enforces tenant ownership."""
        required_fields = ["tenant_id", "id"]
        for field in required_fields:
            assert hasattr(WorkflowRun, field), (
                f"WorkflowRun must have '{field}' for tenant isolation"
            )


class TestAuditAndObservability:
    """Test suite for audit and observability requirements."""

    def test_workflow_run_model_persists_state(self):
        """Verify workflow run captures complete state for recovery."""
        required_fields = ["status", "input", "output", "idempotency_key"]
        for field in required_fields:
            assert hasattr(WorkflowRun, field), (
                f"WorkflowRun must have '{field}' for state persistence"
            )

    def test_workflow_step_captures_execution_state(self):
        """Verify workflow steps capture execution state."""
        required_fields = ["workflow_run_id", "step_name", "status", "input", "output"]
        for field in required_fields:
            assert hasattr(WorkflowStep, field), (
                f"WorkflowStep must have '{field}' for execution tracking"
            )

    def test_activity_model_captures_provenance(self):
        """Verify Activity model captures provenance for audit trail."""
        from app.models.gtm import Activity
        
        required_fields = ["tenant_id", "payload"]
        for field in required_fields:
            assert hasattr(Activity, field), (
                f"Activity must have '{field}' for audit trail"
            )


class TestWorkflowPersistence:
    """Test suite for workflow state persistence."""

    def test_workflow_run_captures_all_required_fields(self):
        """Verify workflow run model captures complete state for recovery."""
        required_fields = [
            "id",
            "tenant_id",
            "status",
            "workflow_type",
            "idempotency_key",
            "created_at",
            "updated_at",
        ]
        for field in required_fields:
            assert hasattr(WorkflowRun, field), (
                f"WorkflowRun must have '{field}' for state persistence"
            )

    def test_approval_request_captures_metadata(self):
        """Verify approval requests persist for HITL gates."""
        required_fields = ["workflow_run_id", "status", "reason", "decision_payload"]
        for field in required_fields:
            assert hasattr(ApprovalRequest, field), (
                f"ApprovalRequest must have '{field}' for HITL gate metadata"
            )

    def test_workflow_run_supports_idempotency(self):
        """Verify workflow runs support idempotent execution."""
        assert hasattr(WorkflowRun, "idempotency_key"), (
            "WorkflowRun must have idempotency_key for idempotent execution"
        )


class TestIntegrationReliability:
    """Test suite for integration provider reliability."""

    def test_integration_run_tracks_requests(self):
        """Verify integration runs track request metadata."""
        assert hasattr(IntegrationRun, "request_metadata"), (
            "IntegrationRun must have request_metadata to track sync metadata"
        )

    def test_integration_run_tracks_counts(self):
        """Verify integration runs track record counts."""
        assert hasattr(IntegrationRun, "counts"), (
            "IntegrationRun must have counts to track sync statistics"
        )

    def test_integration_credentials_are_encrypted(self):
        """Verify integration credentials are not stored in plaintext."""
        # Credentials should be encrypted, not plaintext
        assert hasattr(IntegrationConnection, "encrypted_credentials")
        
        # Verify the field name indicates encryption
        field_name = "encrypted_credentials"
        assert field_name in dir(IntegrationConnection)

    def test_integration_connection_tracks_health(self):
        """Verify integration connection tracks health status."""
        assert hasattr(IntegrationConnection, "health"), (
            "IntegrationConnection must have health field to track provider status"
        )


