"""Fail-closed SQL allowlist validation and row-limit enforcement."""

from dataclasses import dataclass
import re

import sqlglot
from sqlglot import exp

from app.sql.schema_catalog import SchemaCatalog

DESTRUCTIVE_KEYWORDS = re.compile(
    r"\b(?:DELETE|UPDATE|INSERT|DROP|ALTER|TRUNCATE|CREATE)\b", re.IGNORECASE
)
UNBOUNDED_LIMIT = re.compile(r"\bLIMIT\s+ALL\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class SQLValidationResult:
    """Report whether SQL met Keystone's deterministic read-only constraints."""

    valid: bool
    reason: str | None = None


def validate_sql(sql_text: str, schema: SchemaCatalog, max_row_limit: int) -> tuple[SQLValidationResult, str]:
    """Validate a single allowlisted SELECT and return SQL with a safe LIMIT.

    Rejects malformed, multi-statement, destructive, non-SELECT, and out-of-schema SQL.
    A valid SELECT without LIMIT receives max_row_limit; a larger LIMIT is capped.
    """
    if max_row_limit <= 0:
        raise ValueError("max_row_limit must be positive")
    if not sql_text.strip():
        return _rejected("SQL must not be blank")
    if DESTRUCTIVE_KEYWORDS.search(sql_text):
        return _rejected("destructive SQL keyword detected")
    if UNBOUNDED_LIMIT.search(sql_text):
        return _rejected("unbounded LIMIT is not allowed")
    try:
        statements = sqlglot.parse(sql_text, read="postgres")
    except sqlglot.errors.ParseError:
        return _rejected("SQL could not be parsed")
    if len(statements) != 1:
        return _rejected("exactly one SQL statement is required")

    statement = statements[0]
    if not isinstance(statement, exp.Select):
        return _rejected("only a SELECT statement is allowed")
    if statement.args.get("with_") is not None:
        return _rejected("common table expressions are not allowed")
    if statement.args.get("into") is not None:
        return _rejected("SELECT INTO is not allowed")
    if any(
        next(statement.find_all(expression_type), None) is not None
        for expression_type in (exp.Subquery, exp.Union, exp.Intersect, exp.Except)
    ):
        return _rejected("compound or nested queries are not allowed")

    table_aliases: dict[str, str] = {}
    for table in statement.find_all(exp.Table):
        if table.db or table.catalog:
            return _rejected("qualified database names are not allowed")
        table_name = table.name.lower()
        if not schema.contains_table(table_name):
            return _rejected(f"table '{table_name}' is not allowed")
        table_aliases[table.alias_or_name.lower()] = table_name

    if not table_aliases:
        return _rejected("a known table is required")
    for column in statement.find_all(exp.Column):
        if isinstance(column.this, exp.Star):
            continue
        column_name = column.name.lower()
        qualifier = column.table.lower() if column.table else None
        if qualifier is not None:
            source_table = table_aliases.get(qualifier)
            if source_table is None or not schema.contains_column(column_name, source_table):
                return _rejected(f"column '{column.sql()}' is not allowed")
        elif not schema.contains_column(column_name):
            return _rejected(f"column '{column_name}' is not allowed")

    limit = statement.args.get("limit")
    if limit is None:
        statement.set("limit", exp.Limit(expression=exp.Literal.number(max_row_limit)))
    else:
        limit_value = _literal_limit(limit)
        if limit_value is None:
            return _rejected("LIMIT must be a non-negative integer literal")
        statement.set("limit", exp.Limit(expression=exp.Literal.number(min(limit_value, max_row_limit))))
    return SQLValidationResult(valid=True), statement.sql(dialect="postgres")


def _literal_limit(limit: exp.Limit) -> int | None:
    """Return a non-negative integer LIMIT literal, rejecting expressions and parameters."""
    expression = limit.expression
    if not isinstance(expression, exp.Literal) or expression.is_string:
        return None
    try:
        value = int(expression.this)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _rejected(reason: str) -> tuple[SQLValidationResult, str]:
    """Return a rejection result without any executable SQL."""
    return SQLValidationResult(valid=False, reason=reason), ""
