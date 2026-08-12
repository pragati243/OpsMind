"""Add user identities, hashed API keys, and document clearance metadata.

Revision ID: 20260811_0003
Revises: 20260811_0002
Create Date: 2026-08-11 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260811_0003"
down_revision = "20260811_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create identity tables and add conservative document sensitivity defaults."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("clearance_level", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_users_name", "users", ["name"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_department", "users", ["department"])
    op.create_index("ix_users_clearance_level", "users", ["clearance_level"])
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.add_column("documents", sa.Column("sensitivity_tier", sa.String(length=30), nullable=False, server_default="public"))
    op.add_column("documents", sa.Column("min_clearance_level", sa.Integer(), nullable=False, server_default="1"))
    op.execute(
        "UPDATE documents SET sensitivity_tier = 'restricted', min_clearance_level = 3 "
        "WHERE source_path LIKE '%postmortem_process.md'"
    )
    op.alter_column("documents", "sensitivity_tier", server_default=None)
    op.alter_column("documents", "min_clearance_level", server_default=None)


def downgrade() -> None:
    """Remove identity tables and document clearance metadata."""
    op.drop_column("documents", "min_clearance_level")
    op.drop_column("documents", "sensitivity_tier")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index("ix_users_clearance_level", table_name="users")
    op.drop_index("ix_users_department", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_name", table_name="users")
    op.drop_table("users")
