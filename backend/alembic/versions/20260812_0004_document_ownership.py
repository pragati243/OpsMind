"""Add owning department to document access metadata.

Revision ID: 20260812_0004
Revises: 20260811_0003
Create Date: 2026-08-12 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260812_0004"
down_revision = "20260811_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add a non-null ownership label with a conservative Operations default."""
    op.add_column(
        "documents",
        sa.Column("owning_department", sa.String(length=100), nullable=False, server_default="Operations"),
    )
    op.alter_column("documents", "owning_department", server_default=None)


def downgrade() -> None:
    """Remove document ownership metadata."""
    op.drop_column("documents", "owning_department")
