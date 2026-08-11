"""Pydantic contracts for grounded retrieval responses."""

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Identify a source chunk supporting a grounded answer."""

    doc_name: str
    section: str
    chunk_id: str
    score: float


class RAGResult(BaseModel):
    """Represent an answer and the evidence that makes it safe to return."""

    answer: str
    grounded: bool
    citations: list[Citation] = Field(default_factory=list)
