"""Vector store abstraction with numpy and Qdrant backends.

Defines a protocol for vector index operations and provides:
- ``VectorIndex`` (numpy, in-memory) -- fast, no persistence
- ``QdrantVectorIndex`` -- persistent, production-ready

Use ``create_vector_index()`` factory to pick the backend from settings.

Covers: REQ-ERR-002, REQ-OBS-027
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np
import structlog
from numpy.typing import NDArray

from src.utils.config import settings

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class VectorIndexProtocol(Protocol):
    """Minimal interface that both numpy and Qdrant indexes satisfy."""

    @property
    def size(self) -> int: ...

    def add(
        self,
        embeddings: NDArray[np.float32],
        metadata: list[dict[str, Any]],
    ) -> None: ...

    def search(
        self,
        query_embedding: NDArray[np.float32],
        top_k: int = 10,
    ) -> list[tuple[int, float]]: ...

    def get_metadata(self, index: int) -> dict[str, Any]: ...

    # Dashboard backward-compatibility properties
    @property
    def _embeddings(self) -> NDArray[np.float32] | None: ...

    @property
    def _metadata(self) -> list[dict[str, Any]]: ...


# ---------------------------------------------------------------------------
# Qdrant implementation
# ---------------------------------------------------------------------------


class QdrantVectorIndex:
    """Persistent vector index backed by Qdrant.

    Points use sequential integer IDs matching the original numpy-index
    semantics so that ``search()`` returns ``(int_id, score)`` pairs
    compatible with existing callers.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        grpc_port: int = 6334,
        collection_name: str = "scin_embeddings",
        dimension: int = 768,
        api_key: str = "",
    ) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self._collection = collection_name
        self._dimension = dimension

        connect_kwargs: dict[str, Any] = {
            "host": host,
            "port": port,
            "grpc_port": grpc_port,
            "prefer_grpc": True,
        }
        if api_key:
            connect_kwargs["api_key"] = api_key

        self._client = QdrantClient(**connect_kwargs)

        # Create collection if it doesn't exist
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(
                "qdrant_collection_created",
                collection=self._collection,
                dimension=dimension,
            )
        else:
            logger.info(
                "qdrant_collection_exists",
                collection=self._collection,
                count=self._client.count(self._collection).count,
            )

        # Caches for dashboard compatibility -- invalidated on add()
        self.__embeddings_cache: NDArray[np.float32] | None = None
        self.__metadata_cache: list[dict[str, Any]] | None = None

    # ---- size ----

    @property
    def size(self) -> int:
        """Number of points in the collection."""
        count: int = self._client.count(self._collection).count
        return count

    # ---- add ----

    def add(
        self,
        embeddings: NDArray[np.float32],
        metadata: list[dict[str, Any]],
    ) -> None:
        """Upsert embeddings with metadata into Qdrant.

        Point IDs are sequential integers starting from the current
        collection size so they stay compatible with the numpy index.
        """
        from qdrant_client.models import PointStruct

        from src.models.embedding_model import normalize_embeddings

        embeddings = normalize_embeddings(embeddings)
        start_id = self.size

        points = [
            PointStruct(
                id=start_id + i,
                vector=embeddings[i].tolist(),
                payload=meta,
            )
            for i, meta in enumerate(metadata)
        ]

        # Qdrant upsert in batches of 100 (default safe batch)
        batch_size = 100
        for batch_start in range(0, len(points), batch_size):
            batch = points[batch_start : batch_start + batch_size]
            self._client.upsert(
                collection_name=self._collection,
                points=batch,
            )

        # Invalidate caches
        self.__embeddings_cache = None
        self.__metadata_cache = None

        logger.info(
            "qdrant_index_updated",
            new_items=len(metadata),
            total=self.size,
        )

    # ---- search ----

    def search(
        self,
        query_embedding: NDArray[np.float32],
        top_k: int = 10,
    ) -> list[tuple[int, float]]:
        """Nearest-neighbor search by cosine similarity.

        Returns list of ``(point_id, score)`` tuples.
        """
        if self.size == 0:
            return []

        query = query_embedding / max(float(np.linalg.norm(query_embedding)), 1e-8)

        results = self._client.query_points(
            collection_name=self._collection,
            query=query.tolist(),
            limit=top_k,
        )

        return [(int(hit.id), float(hit.score)) for hit in results.points]

    # ---- get_metadata ----

    def get_metadata(self, index: int) -> dict[str, Any]:
        """Retrieve payload for a specific point ID."""
        points = self._client.retrieve(
            collection_name=self._collection,
            ids=[index],
            with_payload=True,
        )
        if points:
            return dict(points[0].payload or {})
        return {}

    # ---- Dashboard backward-compatibility properties ----

    @property
    def _embeddings(self) -> NDArray[np.float32] | None:
        """Fetch all embeddings from Qdrant (cached per add-cycle)."""
        if self.__embeddings_cache is not None:
            return self.__embeddings_cache
        return self._load_all_data()[0]

    @property
    def _metadata(self) -> list[dict[str, Any]]:
        """Fetch all metadata from Qdrant (cached per add-cycle)."""
        if self.__metadata_cache is not None:
            return self.__metadata_cache
        return self._load_all_data()[1]

    def _load_all_data(
        self,
    ) -> tuple[NDArray[np.float32] | None, list[dict[str, Any]]]:
        """Scroll all points from Qdrant and cache them."""
        total = self.size
        if total == 0:
            self.__embeddings_cache = None
            self.__metadata_cache = []
            return None, []

        all_vectors: list[list[float]] = []
        all_meta: list[dict[str, Any]] = []

        offset = None
        while True:
            scroll_result = self._client.scroll(
                collection_name=self._collection,
                limit=256,
                offset=offset,
                with_vectors=True,
                with_payload=True,
            )
            points, next_offset = scroll_result
            for pt in points:
                all_vectors.append(pt.vector)  # type: ignore[arg-type]
                all_meta.append(dict(pt.payload or {}))
            if next_offset is None:
                break
            offset = next_offset

        emb = np.array(all_vectors, dtype=np.float32) if all_vectors else None
        self.__embeddings_cache = emb
        self.__metadata_cache = all_meta
        return emb, all_meta

    # ---- Collection management ----

    def delete_collection(self) -> None:
        """Drop the entire collection (used by --force-reindex)."""
        self._client.delete_collection(self._collection)
        self.__embeddings_cache = None
        self.__metadata_cache = None
        logger.info("qdrant_collection_deleted", collection=self._collection)

    def recreate_collection(self) -> None:
        """Delete and recreate the collection with the same params."""
        from qdrant_client.models import Distance, VectorParams

        self.delete_collection()
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(
                size=self._dimension,
                distance=Distance.COSINE,
            ),
        )
        logger.info(
            "qdrant_collection_recreated",
            collection=self._collection,
            dimension=self._dimension,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_vector_index() -> VectorIndexProtocol:
    """Return the appropriate vector index based on ``settings.vector_store.backend``.

    - ``"numpy"`` -- in-memory ``VectorIndex`` (from rag_retrieval)
    - ``"qdrant"`` -- persistent ``QdrantVectorIndex``
    """
    backend = settings.vector_store.backend

    if backend == "qdrant":
        logger.info(
            "vector_index_backend",
            backend="qdrant",
            host=settings.vector_store.qdrant_host,
            port=settings.vector_store.qdrant_port,
            collection=settings.vector_store.collection_name,
        )
        return QdrantVectorIndex(
            host=settings.vector_store.qdrant_host,
            port=settings.vector_store.qdrant_port,
            grpc_port=settings.vector_store.qdrant_grpc_port,
            collection_name=settings.vector_store.collection_name,
            dimension=settings.embedding.dimension,
            api_key=settings.vector_store.qdrant_api_key,
        )

    # Default: numpy in-memory
    from src.models.rag_retrieval import VectorIndex

    logger.info("vector_index_backend", backend="numpy")
    return VectorIndex()  # type: ignore[return-value]
