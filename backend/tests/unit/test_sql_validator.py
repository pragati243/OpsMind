"""Hard-gated deny-path tests for SQL validation."""

import pytest

from app.sql.schema_catalog import BUSINESS_SCHEMA
from app.sql.validator import validate_sql


@pytest.mark.parametrize(
    "sql_text",
    [
        "DROP TABLE incidents",
        "UPDATE incidents SET status = 'resolved'",
        "DELETE FROM incidents",
        "INSERT INTO incidents (title) VALUES ('malicious')",
        "ALTER TABLE incidents ADD COLUMN secret TEXT",
        "TRUNCATE incidents",
        "CREATE TABLE employees (id INTEGER)",
        "SELECT * FROM employees",
        "SELECT compensation FROM incidents",
        "SELECT incidents.secret FROM incidents",
        "SELECT * FROM incidents; DROP TABLE incidents",
        "SELECT * INTO backup_incidents FROM incidents",
        "WITH data AS (SELECT * FROM incidents) SELECT * FROM data",
        "SELECT * FROM incidents UNION SELECT * FROM incidents",
        "SELECT * FROM (SELECT * FROM incidents) AS nested",
        "SELECT 1",
        "SELECT * FROM incidents LIMIT ALL",
        "",
    ],
)
def test_malicious_or_invalid_sql_is_always_rejected(sql_text: str) -> None:
    """Every prohibited statement, schema escape, and non-bounded form must fail closed."""
    result, safe_sql = validate_sql(sql_text, BUSINESS_SCHEMA, max_row_limit=100)

    assert result.valid is False
    assert result.reason
    assert safe_sql == ""


def test_missing_limit_is_injected_before_execution() -> None:
    """A potentially huge read is bounded deterministically instead of being executed unbounded."""
    result, safe_sql = validate_sql("SELECT id, severity FROM incidents", BUSINESS_SCHEMA, max_row_limit=100)

    assert result.valid is True
    assert safe_sql.endswith("LIMIT 100")


def test_excessive_limit_is_capped_before_execution() -> None:
    """A caller cannot exceed the validator's configured maximum row count."""
    result, safe_sql = validate_sql("SELECT * FROM incidents LIMIT 1000000", BUSINESS_SCHEMA, max_row_limit=100)

    assert result.valid is True
    assert safe_sql.endswith("LIMIT 100")
