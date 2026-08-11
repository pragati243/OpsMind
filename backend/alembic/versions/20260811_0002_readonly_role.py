"""Create the constrained database role used for Text2SQL execution.

Revision ID: 20260811_0002
Revises: 20260811_0001
Create Date: 2026-08-11 00:00:00
"""

from alembic import op

revision = "20260811_0002"
down_revision = "20260811_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create a no-login role with select access to the approved business tables only."""
    op.execute(
        """
        DO $$
        BEGIN
            CREATE ROLE keystone_readonly NOLOGIN NOINHERIT;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO keystone_readonly")
    op.execute("GRANT SELECT ON TABLE incidents, on_call_schedule TO keystone_readonly")
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format('GRANT keystone_readonly TO %I', current_user);
        END $$;
        """
    )


def downgrade() -> None:
    """Revoke the role grants and remove the constrained role."""
    op.execute("REVOKE SELECT ON TABLE incidents, on_call_schedule FROM keystone_readonly")
    op.execute("REVOKE USAGE ON SCHEMA public FROM keystone_readonly")
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format('REVOKE keystone_readonly FROM %I', current_user);
            DROP ROLE IF EXISTS keystone_readonly;
        END $$;
        """
    )
