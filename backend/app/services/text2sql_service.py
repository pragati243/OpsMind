"""Safe Text2SQL orchestration with validation before execution."""

import json

from app.config import get_settings
from app.core.llm_client import GroqLLMClient, LLMClient
from app.schemas.text2sql import Text2SQLResult
from app.sql.executor import execute_readonly
from app.sql.schema_catalog import BUSINESS_SCHEMA
from app.sql.validator import validate_sql

SQL_SYSTEM_PROMPT = """Generate exactly one PostgreSQL SELECT statement and nothing else.
Use only the provided schema. Never use a write statement, DDL, a CTE, or a subquery.
Use explicit columns when possible. The validator will reject anything outside these rules."""
EXPLANATION_SYSTEM_PROMPT = """Explain only the supplied database rows in plain English.
Do not infer facts that are not represented in the rows. If the rows are empty, clearly say so."""


class Text2SQLService:
    """Convert questions to validated, database-enforced read-only SQL results."""

    def __init__(self, llm_client: LLMClient | None = None, max_row_limit: int | None = None) -> None:
        settings = get_settings() if llm_client is None or max_row_limit is None else None
        self._llm_client = llm_client or GroqLLMClient()
        self._max_row_limit = max_row_limit if max_row_limit is not None else settings.sql_max_row_limit

    async def run_text2sql(self, question: str) -> Text2SQLResult:
        """Generate, validate, execute, then explain SQL results for a non-empty question."""
        if not question.strip():
            return Text2SQLResult(valid=False, rejection_reason="question must not be blank")
        generated_sql = _extract_sql(
            await self._llm_client.generate(
                SQL_SYSTEM_PROMPT,
                f"Approved schema:\n{BUSINESS_SCHEMA.describe()}\n\nQuestion: {question}",
            )
        )
        validation, safe_sql = validate_sql(generated_sql, BUSINESS_SCHEMA, self._max_row_limit)
        if not validation.valid:
            return Text2SQLResult(valid=False, rejection_reason=validation.reason)

        rows = await execute_readonly(safe_sql)
        explanation = await self._llm_client.generate(
            EXPLANATION_SYSTEM_PROMPT,
            f"Question: {question}\n\nActual returned rows:\n{json.dumps(rows, default=str)}",
        )
        return Text2SQLResult(valid=True, sql=safe_sql, rows=rows, explanation=explanation)


def _extract_sql(text: str) -> str:
    """Remove an optional markdown SQL fence without altering SQL content."""
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        return "\n".join(lines[1:-1]).strip()
    return stripped


_default_service: Text2SQLService | None = None


async def run_text2sql(question: str) -> Text2SQLResult:
    """Run the default Text2SQL service for a natural-language question."""
    global _default_service
    if _default_service is None:
        _default_service = Text2SQLService()
    return await _default_service.run_text2sql(question)
