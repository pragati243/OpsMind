"""Database execution constrained by PostgreSQL's dedicated read-only role."""

from typing import Any

from sqlalchemy import text

async def execute_readonly(sql_text: str) -> list[dict[str, Any]]:
    """Execute already-validated SELECT SQL under the keystone_readonly role.

    The transaction is read-only and SET LOCAL ROLE adds database-enforced protection even if
    application validation is bypassed. Database permission failures are propagated to callers.
    """
    from app.core.database import engine

    async with engine.connect() as connection:
        async with connection.begin():
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            await connection.execute(text("SET LOCAL ROLE keystone_readonly"))
            result = await connection.execute(text(sql_text))
            return [dict(row) for row in result.mappings().all()]
