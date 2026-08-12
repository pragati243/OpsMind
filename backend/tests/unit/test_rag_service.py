"""Unit tests for RAG grounding behavior."""

import asyncio

from app.core.llm_client import LLMClient
from app.retrieval.chunking import DocumentChunk
from app.schemas.rag import RAGResult
from app.services.rag_service import RAGService


class TestUser:
    """Provide an authorized principal for isolated RAG tests."""

    clearance_level = 4
    department = "Platform Engineering"


class FakeVectorStore:
    """Return deterministic retrieval results without Qdrant."""

    def __init__(self, results: list[tuple[DocumentChunk, float]]) -> None:
        self.results = results

    async def search(self, query: str, limit: int, query_filter=None) -> list[tuple[DocumentChunk, float]]:
        """Return configured results for any test query."""
        return self.results[:limit]


class FakeLLMClient(LLMClient):
    """Return a stable answer and record whether generation was requested."""

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return a deterministic answer for a grounded test path."""
        self.calls += 1
        return "P1 incidents must be acknowledged within 10 minutes."


def test_answerable_query_returns_citations() -> None:
    """A result above threshold should generate an answer with source citations."""
    chunk = DocumentChunk("sla_definitions.md", "Incident targets", "P1 acknowledgement is due within 10 minutes.", "chunk-1")
    llm = FakeLLMClient()
    service = RAGService(FakeVectorStore([(chunk, 0.91)]), llm, similarity_threshold=0.55)

    result: RAGResult = asyncio.run(service.run_rag("What is the P1 acknowledgement target?", TestUser()))

    assert result.grounded is True
    assert result.citations[0].doc_name == "sla_definitions.md"
    assert llm.calls == 1


def test_unanswerable_query_refuses_without_citations() -> None:
    """A result below threshold must be refused without invoking the LLM."""
    chunk = DocumentChunk("sla_definitions.md", "Incident targets", "P1 acknowledgement is due within 10 minutes.", "chunk-1")
    llm = FakeLLMClient()
    service = RAGService(FakeVectorStore([(chunk, 0.12)]), llm, similarity_threshold=0.55)

    result = asyncio.run(service.run_rag("What is the company holiday party menu?", TestUser()))

    assert result.grounded is False
    assert result.citations == []
    assert llm.calls == 0
