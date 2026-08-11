"""Allowlisted business schema exposed to Text2SQL."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SchemaCatalog:
    """Describe tables and columns that generated SQL may access."""

    tables: dict[str, frozenset[str]]

    def contains_table(self, table_name: str) -> bool:
        """Return whether a table is available to generated read-only SQL."""
        return table_name.lower() in self.tables

    def contains_column(self, column_name: str, table_name: str | None = None) -> bool:
        """Return whether a column exists globally or on a specified approved table."""
        column_name = column_name.lower()
        if table_name is not None:
            return column_name in self.tables.get(table_name.lower(), frozenset())
        return any(column_name in columns for columns in self.tables.values())

    def describe(self) -> str:
        """Render the approved schema for an LLM prompt."""
        return "\n".join(
            f"{table}({', '.join(sorted(columns))})" for table, columns in self.tables.items()
        )


BUSINESS_SCHEMA = SchemaCatalog(
    tables={
        "incidents": frozenset(
            {"id", "title", "description", "severity", "service_name", "status", "created_at", "resolved_at"}
        ),
        "on_call_schedule": frozenset({"id", "service_name", "engineer_name", "week_start"}),
    }
)
