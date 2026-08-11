"""Create initial operational data tables.

Revision ID: 20260811_0001
Revises:
Create Date: 2026-08-11 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260811_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create documents, incidents, and on-call schedule tables."""
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_path", sa.String(length=512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("title"),
        sa.UniqueConstraint("source_path"),
    )
    op.create_index("ix_documents_title", "documents", ["title"])
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=2), nullable=False),
        sa.Column("service_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_incidents_title", "incidents", ["title"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_service_name", "incidents", ["service_name"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_table(
        "on_call_schedule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_name", sa.String(length=100), nullable=False),
        sa.Column("engineer_name", sa.String(length=255), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.UniqueConstraint("service_name", "week_start", name="uq_on_call_service_week"),
    )
    op.create_index("ix_on_call_schedule_service_name", "on_call_schedule", ["service_name"])
    op.create_index("ix_on_call_schedule_week_start", "on_call_schedule", ["week_start"])


def downgrade() -> None:
    """Remove the initial operational data tables."""
    op.drop_index("ix_on_call_schedule_week_start", table_name="on_call_schedule")
    op.drop_index("ix_on_call_schedule_service_name", table_name="on_call_schedule")
    op.drop_table("on_call_schedule")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_index("ix_incidents_service_name", table_name="incidents")
    op.drop_index("ix_incidents_severity", table_name="incidents")
    op.drop_index("ix_incidents_title", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index("ix_documents_title", table_name="documents")
    op.drop_table("documents")
