"""Allow rate-limited integration runs.

Revision ID: 20260518_0002
Revises: 20260517_0001
Create Date: 2026-05-18
"""

from alembic import op


revision = "20260518_0002"
down_revision = "20260517_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_integration_runs_status", "integration_runs", type_="check")
    op.create_check_constraint(
        "ck_integration_runs_status",
        "integration_runs",
        "status in ('pending', 'running', 'completed', 'failed', 'timed_out', 'cancelled', 'rate_limited')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_integration_runs_status", "integration_runs", type_="check")
    op.create_check_constraint(
        "ck_integration_runs_status",
        "integration_runs",
        "status in ('pending', 'running', 'completed', 'failed', 'timed_out', 'cancelled')",
    )

