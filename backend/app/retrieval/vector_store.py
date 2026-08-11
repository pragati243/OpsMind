"""Provider-agnostic embedding and Qdrant retrieval infrastructure."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from uuid import uuid5, NAMESPACE_URL

from app.config import get_settings
from app.retrieval.chunking import DocumentChunk, chunk_markdown


class EmbeddingProvider(ABC):
    """Define the embedding boundary used by retrieval providers."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed text inputs into same-sized dense vectors or raise on provider failure."""

    @abstractmethod
    async def dimension(self) -> int:
        """Return the dimension of vectors produced by this provider."""


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Embed with the local all-MiniLM-L6-v2 SentenceTransformers model."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model: Any | None = None

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Encode input texts locally without blocking the async event loop."""
        model = await self._get_model()
        vectors = await asyncio.to_thread(model.encode, texts, normalize_embeddings=True)
        return vectors.tolist()

    async def dimension(self) -> int:
        """Return the local model vector dimension."""
        model = await self._get_model()
        return int(await asyncio.to_thread(model.get_sentence_embedding_dimension))

    async def _get_model(self) -> Any:
        """Load and cache the local model on its first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = await asyncio.to_thread(SentenceTransformer, self._model_name)
        return self._model


class QdrantVectorStore:
    """Store document chunks in Qdrant and retrieve them by semantic similarity."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        client: Any | None = None,
        documents_path: Path | None = None,
    ) -> None:
        settings = get_settings()
        self._collection_name = settings.qdrant_collection_name
        self._embedding_provider = embedding_provider or SentenceTransformerEmbeddingProvider()
        if client is None:
            from qdrant_client import AsyncQdrantClient

            self._client: Any = AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key.get_secret_value(),
            )
        else:
            self._client = client
        self._documents_path = documents_path or Path(__file__).resolve().parents[1] / "data" / "documents"
        self._initialized = False

    async def initialize(self) -> None:
        """Create the collection when needed and upsert all local markdown chunks."""
        if self._initialized:
            return
        exists = await self._client.collection_exists(self._collection_name)
        if not exists:
            from qdrant_client import models

            await self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=models.VectorParams(
                    size=await self._embedding_provider.dimension(),
                    distance=models.Distance.COSINE,
                ),
            )
        chunks = list(self._load_chunks())
        if chunks:
            from qdrant_client import models

            vectors = await self._embedding_provider.embed([chunk.text for chunk in chunks])
            points = [
                models.PointStruct(
                    id=str(uuid5(NAMESPACE_URL, chunk.chunk_id)),
                    vector=vector,
                    payload={
                        "doc_name": chunk.doc_name,
                        "section": chunk.section,
                        "text": chunk.text,
                        "chunk_id": chunk.chunk_id,
                    },
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
            await self._client.upsert(collection_name=self._collection_name, points=points, wait=True)
        self._initialized = True

    async def search(self, query: str, limit: int) -> list[tuple[DocumentChunk, float]]:
        """Return the highest-scoring chunks for a non-empty query.

        Raises:
            ValueError: If query is blank or limit is not positive.
            Exception: If Qdrant or the embedding provider fails.
        """
        if not query.strip():
            raise ValueError("query must not be blank")
        if limit <= 0:
            raise ValueError("limit must be positive")
        await self.initialize()
        vector = (await self._embedding_provider.embed([query]))[0]
        response = await self._client.query_points(
            collection_name=self._collection_name,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        results: list[tuple[DocumentChunk, float]] = []
        for point in response.points:
            payload = point.payload or {}
            results.append(
                (
                    DocumentChunk(
                        doc_name=str(payload["doc_name"]),
                        section=str(payload["section"]),
                        text=str(payload["text"]),
                        chunk_id=str(payload["chunk_id"]),
                    ),
                    float(point.score),
                )
            )
        return results

    def _load_chunks(self) -> Iterable[DocumentChunk]:
        """Read all markdown policy documents and yield section-aware chunks."""
        for path in sorted(self._documents_path.glob("*.md")):
            yield from chunk_markdown(path.name, path.read_text(encoding="utf-8"))
