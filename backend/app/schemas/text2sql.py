"""Pydantic contracts for Text2SQL responses."""

from typing import Any

from pydantic import BaseModel, Field


class Text2SQLResult(BaseModel):
    """Contain validated SQL, executed rows, and a result-grounded explanation."""

    valid: bool
    sql: str = ""
    rows: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str = ""
    rejection_reason: str | None = None
    sql_validation: dict[str, str | bool | None] = Field(default_factory=dict)
