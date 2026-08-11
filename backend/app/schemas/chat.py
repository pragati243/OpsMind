"""Pydantic contracts for the unified ask endpoint."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.rag import Citation


class AskRequest(BaseModel):
    """Accept a non-empty operations question from an authenticated caller."""

    question: str = Field(min_length=1, max_length=4_000)


class AskResponse(BaseModel):
    """Return route-specific answer data without concealing validation outcomes."""

    question: str
    query_type: Literal["document", "data", "hybrid", "vague", "refused"]
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    generated_sql: str | None = None
    sql_validation: dict[str, Any] | None = None
    result_table: list[dict[str, Any]] = Field(default_factory=list)
    business_insight: str | None = None
    refusal_reason: str | None = None
