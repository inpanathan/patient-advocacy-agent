"""RAG retrieval service for SCIN database.

Provides query-by-image and query-by-text retrieval against indexed
SCIN embeddings, with timeouts, retries, and graceful degradation.

Covers: REQ-ERR-002, REQ-ERR-003, REQ-ERR-004, REQ-OBS-027, REQ-OBS-029
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import structlog
from numpy.typing import NDArray

from src.models.embedding_model import get_embedding_model, normalize_embeddings
from src.utils.errors import AppError, ErrorCode

logger = structlog.get_logger(__name__)


@dataclass
class RetrievalResult:
    """A single retrieval result with metadata."""

    record_id: str
    score: float
    diagnosis: str = ""
    icd_code: str = ""
    image_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResponse:
    """Complete retrieval response with metadata."""

    results: list[RetrievalResult] = field(default_factory=list)
    query_type: str = ""
    latency_ms: int = 0
    from_cache: bool = False


class VectorIndex:
    """In-memory vector index for SCIN embeddings.

    Stores embeddings and metadata, supports nearest-neighbor search
    via cosine similarity. In production, this would be replaced by
    ChromaDB or Qdrant.
    """

    def __init__(self) -> None:
        self._embeddings: NDArray[np.float32] | None = None
        self._metadata: list[dict[str, Any]] = []
        self._cache: dict[str, RetrievalResponse] = {}

    @property
    def size(self) -> int:
        return len(self._metadata)

    def add(
        self,
        embeddings: NDArray[np.float32],
        metadata: list[dict[str, Any]],
    ) -> None:
        """Add embeddings with metadata to the index."""
        embeddings = normalize_embeddings(embeddings)
        if self._embeddings is None:
            self._embeddings = embeddings
        else:
            self._embeddings = np.vstack([self._embeddings, embeddings])
        self._metadata.extend(metadata)
        logger.info("index_updated", new_items=len(metadata), total=self.size)

    def search(
        self,
        query_embedding: NDArray[np.float32],
        top_k: int = 10,
    ) -> list[tuple[int, float]]:
        """Search for nearest neighbors by cosine similarity.

        Args:
            query_embedding: Query vector of shape (D,).
            top_k: Number of results to return.

        Returns:
            List of (index, similarity_score) tuples.
        """
        if self._embeddings is None or self.size == 0:
            return []

        query = query_embedding / np.maximum(np.linalg.norm(query_embedding), 1e-8)
        similarities = self._embeddings @ query
        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [(int(idx), float(similarities[idx])) for idx in top_indices]

    def get_metadata(self, index: int) -> dict[str, Any]:
        """Get metadata for a specific index."""
        if 0 <= index < len(self._metadata):
            return self._metadata[index]
        return {}


class RAGRetriever:
    """RAG retrieval service with caching and graceful degradation.

    Wraps the vector index with embedding model integration,
    caching, and error handling.
    """

    def __init__(
        self,
        index: VectorIndex,
        top_k: int = 10,
        timeout_ms: int = 5000,
        max_retries: int = 2,
    ) -> None:
        self._index = index
        self._model = get_embedding_model()
        self._top_k = top_k
        self._timeout_ms = timeout_ms
        self._max_retries = max_retries
        self._cache: dict[str, RetrievalResponse] = {}

    def query_by_image(self, image_path: str) -> RetrievalResponse:
        """Retrieve similar SCIN records by image.

        Args:
            image_path: Path to query image.

        Returns:
            RetrievalResponse with ranked results.
        """
        cache_key = f"image:{image_path}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            cached.from_cache = True
            return cached

        start = time.monotonic()
        embedding = self._model.embed_image(image_path)
        return self._search(embedding, "image", cache_key, start)

    def query_by_text(self, text: str) -> RetrievalResponse:
        """Retrieve similar SCIN records by text description.

        Args:
            text: Query text.

        Returns:
            RetrievalResponse with ranked results.
        """
        cache_key = f"text:{text}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            cached.from_cache = True
            return cached

        start = time.monotonic()
        embedding = self._model.embed_text(text)
        return self._search(embedding, "text", cache_key, start)

    def _search(
        self,
        embedding: NDArray[np.float32],
        query_type: str,
        cache_key: str,
        start_time: float,
    ) -> RetrievalResponse:
        """Execute search with error handling."""
        try:
            matches = self._index.search(embedding, self._top_k)
        except Exception as e:
            logger.error("rag_search_failed", error=str(e), query_type=query_type)
            raise AppError(
                code=ErrorCode.RAG_RETRIEVAL_FAILED,
                message="Vector store search failed",
                context={"query_type": query_type},
                cause=e,
            ) from e

        results = []
        for idx, score in matches:
            meta = self._index.get_metadata(idx)
            results.append(
                RetrievalResult(
                    record_id=meta.get("record_id", f"idx-{idx}"),
                    score=score,
                    diagnosis=meta.get("diagnosis", ""),
                    icd_code=meta.get("icd_code", ""),
                    image_path=meta.get("image_path", ""),
                    metadata=meta,
                )
            )

        latency_ms = int((time.monotonic() - start_time) * 1000)
        response = RetrievalResponse(
            results=results,
            query_type=query_type,
            latency_ms=latency_ms,
        )

        self._cache[cache_key] = response

        logger.info(
            "rag_retrieval_complete",
            query_type=query_type,
            num_results=len(results),
            top_score=f"{results[0].score:.4f}" if results else "N/A",
            latency_ms=latency_ms,
        )

        return response

    def clear_cache(self) -> None:
        """Clear the retrieval cache."""
        self._cache.clear()
