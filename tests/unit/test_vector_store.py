"""Tests for the vector store abstraction layer.

Tests QdrantVectorIndex with a mocked qdrant client, the factory
function, and backward-compatibility properties.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.models.vector_store import (
    QdrantVectorIndex,
    create_vector_index,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_qdrant_client() -> MagicMock:
    """A mocked QdrantClient."""
    client = MagicMock()
    client.collection_exists.return_value = True
    client.count.return_value = MagicMock(count=0)
    return client


@pytest.fixture()
def qdrant_index(mock_qdrant_client: MagicMock) -> QdrantVectorIndex:
    """QdrantVectorIndex with a mocked client (bypasses __init__)."""
    idx = QdrantVectorIndex.__new__(QdrantVectorIndex)
    idx._collection = "test_collection"
    idx._dimension = 768
    idx._client = mock_qdrant_client
    idx._QdrantVectorIndex__embeddings_cache = None  # type: ignore[attr-defined]
    idx._QdrantVectorIndex__metadata_cache = None  # type: ignore[attr-defined]
    return idx


# ---------------------------------------------------------------------------
# Size
# ---------------------------------------------------------------------------


class TestSize:
    def test_size_returns_count(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        mock_qdrant_client.count.return_value = MagicMock(count=42)
        assert qdrant_index.size == 42
        mock_qdrant_client.count.assert_called_with("test_collection")

    def test_size_zero_when_empty(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        mock_qdrant_client.count.return_value = MagicMock(count=0)
        assert qdrant_index.size == 0


# ---------------------------------------------------------------------------
# Add
# ---------------------------------------------------------------------------


class TestAdd:
    def test_add_upserts_points(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        embeddings = np.random.randn(3, 768).astype(np.float32)
        metadata = [
            {"record_id": "r1", "diagnosis": "eczema"},
            {"record_id": "r2", "diagnosis": "psoriasis"},
            {"record_id": "r3", "diagnosis": "acne"},
        ]

        mock_qdrant_client.count.return_value = MagicMock(count=0)

        with patch("src.models.embedding_model.normalize_embeddings", return_value=embeddings):
            qdrant_index.add(embeddings, metadata)

        mock_qdrant_client.upsert.assert_called_once()
        call_kwargs = mock_qdrant_client.upsert.call_args
        assert call_kwargs.kwargs["collection_name"] == "test_collection"

    def test_add_invalidates_caches(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        qdrant_index._QdrantVectorIndex__embeddings_cache = np.zeros((1, 768), dtype=np.float32)  # type: ignore[attr-defined]
        qdrant_index._QdrantVectorIndex__metadata_cache = [{"test": True}]  # type: ignore[attr-defined]

        embeddings = np.random.randn(1, 768).astype(np.float32)
        mock_qdrant_client.count.return_value = MagicMock(count=0)

        with patch("src.models.embedding_model.normalize_embeddings", return_value=embeddings):
            qdrant_index.add(embeddings, [{"record_id": "r1"}])

        assert qdrant_index._QdrantVectorIndex__embeddings_cache is None  # type: ignore[attr-defined]
        assert qdrant_index._QdrantVectorIndex__metadata_cache is None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_returns_empty_when_no_data(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        mock_qdrant_client.count.return_value = MagicMock(count=0)
        query = np.random.randn(768).astype(np.float32)
        assert qdrant_index.search(query) == []

    def test_search_returns_id_score_tuples(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        mock_qdrant_client.count.return_value = MagicMock(count=10)

        hit1 = MagicMock(id=3, score=0.95)
        hit2 = MagicMock(id=7, score=0.82)
        mock_qdrant_client.query_points.return_value = MagicMock(points=[hit1, hit2])

        query = np.random.randn(768).astype(np.float32)
        results = qdrant_index.search(query, top_k=2)

        assert results == [(3, 0.95), (7, 0.82)]
        mock_qdrant_client.query_points.assert_called_once()


# ---------------------------------------------------------------------------
# get_metadata
# ---------------------------------------------------------------------------


class TestGetMetadata:
    def test_returns_payload(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        point = MagicMock(payload={"record_id": "r42", "diagnosis": "eczema"})
        mock_qdrant_client.retrieve.return_value = [point]

        result = qdrant_index.get_metadata(42)
        assert result == {"record_id": "r42", "diagnosis": "eczema"}

    def test_returns_empty_dict_when_not_found(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        mock_qdrant_client.retrieve.return_value = []
        assert qdrant_index.get_metadata(999) == {}


# ---------------------------------------------------------------------------
# Dashboard compatibility properties
# ---------------------------------------------------------------------------


class TestDashboardProperties:
    def test_embeddings_returns_none_when_empty(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        mock_qdrant_client.count.return_value = MagicMock(count=0)
        assert qdrant_index._embeddings is None

    def test_metadata_returns_empty_list_when_empty(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        mock_qdrant_client.count.return_value = MagicMock(count=0)
        assert qdrant_index._metadata == []

    def test_loads_from_scroll(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        mock_qdrant_client.count.return_value = MagicMock(count=2)

        pt1 = MagicMock(vector=[0.1] * 768, payload={"record_id": "r1"})
        pt2 = MagicMock(vector=[0.2] * 768, payload={"record_id": "r2"})
        mock_qdrant_client.scroll.return_value = ([pt1, pt2], None)

        emb = qdrant_index._embeddings
        meta = qdrant_index._metadata

        assert emb is not None
        assert emb.shape == (2, 768)
        assert len(meta) == 2
        assert meta[0]["record_id"] == "r1"

    def test_uses_cache_on_second_access(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        cached_emb = np.zeros((5, 768), dtype=np.float32)
        cached_meta = [{"record_id": f"r{i}"} for i in range(5)]
        qdrant_index._QdrantVectorIndex__embeddings_cache = cached_emb  # type: ignore[attr-defined]
        qdrant_index._QdrantVectorIndex__metadata_cache = cached_meta  # type: ignore[attr-defined]

        assert qdrant_index._embeddings is cached_emb
        assert qdrant_index._metadata is cached_meta
        # scroll should not have been called
        mock_qdrant_client.scroll.assert_not_called()


# ---------------------------------------------------------------------------
# Collection management
# ---------------------------------------------------------------------------


class TestCollectionManagement:
    def test_delete_collection(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        qdrant_index.delete_collection()
        mock_qdrant_client.delete_collection.assert_called_once_with("test_collection")

    def test_recreate_collection(
        self, qdrant_index: QdrantVectorIndex, mock_qdrant_client: MagicMock
    ) -> None:
        qdrant_index.recreate_collection()
        mock_qdrant_client.delete_collection.assert_called_once()
        mock_qdrant_client.create_collection.assert_called_once()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestFactory:
    @patch("src.models.vector_store.settings")
    def test_numpy_backend(self, mock_settings: MagicMock) -> None:
        mock_settings.vector_store.backend = "numpy"

        with patch("src.models.rag_retrieval.VectorIndex") as mock_vi_cls:
            mock_vi_cls.return_value = MagicMock()
            create_vector_index()

        mock_vi_cls.assert_called_once()

    @patch("src.models.vector_store.settings")
    @patch.object(QdrantVectorIndex, "__init__", return_value=None)
    def test_qdrant_backend(self, mock_init: MagicMock, mock_settings: MagicMock) -> None:
        mock_settings.vector_store.backend = "qdrant"
        mock_settings.vector_store.qdrant_host = "localhost"
        mock_settings.vector_store.qdrant_port = 6333
        mock_settings.vector_store.qdrant_grpc_port = 6334
        mock_settings.vector_store.collection_name = "test"
        mock_settings.embedding.dimension = 768
        mock_settings.vector_store.qdrant_api_key = ""

        result = create_vector_index()

        assert isinstance(result, QdrantVectorIndex)
        mock_init.assert_called_once_with(
            host="localhost",
            port=6333,
            grpc_port=6334,
            collection_name="test",
            dimension=768,
            api_key="",
        )


# ---------------------------------------------------------------------------
# VectorIndex (numpy) still satisfies the protocol
# ---------------------------------------------------------------------------


class TestNumpyBackwardCompat:
    def test_vector_index_has_protocol_methods(self) -> None:
        """The original VectorIndex has all methods the protocol requires."""
        from src.models.rag_retrieval import VectorIndex

        vi = VectorIndex()
        assert hasattr(vi, "size")
        assert hasattr(vi, "add")
        assert hasattr(vi, "search")
        assert hasattr(vi, "get_metadata")
        assert hasattr(vi, "_embeddings")
        assert hasattr(vi, "_metadata")
