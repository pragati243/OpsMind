"""Hard-gated integration test for Qdrant-native retrieval authorization."""

import asyncio

from app.core.llm_client import LLMClient
from app.core.security import ResolvedIdentity
from app.retrieval.chunking import DocumentChunk
from app.schemas.rag import RAGResult
from app.services.rag_service import RAGService


class FixedLLM(LLMClient):
    """Generate a deterministic answer without external LLM access."""

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return a short answer for any permitted retrieved context."""
        return "Retrieved policy information."


class PermissionedAnnStore:
    """Emulate Qdrant's filtered ANN result set and record its received filter."""

    def __init__(self) -> None:
        self.filters = []
        self._public = DocumentChunk("incident_response_policy.md", "Closure", "P1 incidents require a postmortem.", "public")
        self._restricted = DocumentChunk(
            "postmortem_process.md", "Scope", "P1 postmortems contain sensitive incident details.", "restricted"
        )

    async def search(self, query: str, limit: int, query_filter=None):
        """Return only chunks permitted by the Qdrant filter's clearance threshold."""
        self.filters.append(query_filter)
        clearance = query_filter.must[0].range.lte
        chunks = [(self._public, 0.95)]
        if clearance >= 3:
            chunks.insert(0, (self._restricted, 0.99))
        return chunks[:limit]


def test_rbac_filter_prevents_postmortem_citation_for_intern() -> None:
    """The same query must produce a different ANN citation set with no intern leak."""
    store = PermissionedAnnStore()
    service = RAGService(store, FixedLLM(), similarity_threshold=0.5, top_k=5)
    intern = ResolvedIdentity(1, "Iris Intern", "Intern", "Operations", 1)
    manager = ResolvedIdentity(4, "Morgan Manager", "Manager", "Engineering Management", 4)

    intern_result: RAGResult = asyncio.run(service.run_rag("What is the postmortem process?", intern))
    manager_result: RAGResult = asyncio.run(service.run_rag("What is the postmortem process?", manager))

    intern_citations = {citation.doc_name for citation in intern_result.citations}
    manager_citations = {citation.doc_name for citation in manager_result.citations}
    assert intern_citations != manager_citations
    assert "postmortem_process.md" not in intern_citations
    assert "postmortem_process.md" in manager_citations
    assert store.filters[0].must[0].key == "required_clearance_level"
    assert store.filters[0].must[0].range.lte == 1
    assert store.filters[1].must[0].range.lte == 4
