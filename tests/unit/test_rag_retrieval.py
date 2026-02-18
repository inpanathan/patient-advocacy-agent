"""Tests for RAG retrieval service."""

from __future__ import annotations

import numpy as np

from src.models.mocks.mock_embedding import MockEmbeddingModel
from src.models.rag_retrieval import RAGRetriever, VectorIndex


class TestVectorIndex:
    """Test in-memory vector index."""

    def test_empty_index(self):
        """Empty index returns no results."""
        index = VectorIndex()
        assert index.size == 0
        query = np.random.randn(768).astype(np.float32)
        assert index.search(query) == []

    def test_add_and_search(self):
        """Adding vectors enables search."""
        index = VectorIndex()
        rng = np.random.default_rng(42)
        emb = rng.standard_normal((5, 768)).astype(np.float32)
        meta = [{"record_id": f"r{i}"} for i in range(5)]
        index.add(emb, meta)

        assert index.size == 5
        results = index.search(emb[0], top_k=3)
        assert len(results) == 3
        # First result should be the query itself (highest similarity)
        assert results[0][0] == 0
        assert results[0][1] > 0.9

    def test_metadata_retrieval(self):
        """Metadata is retrievable by index."""
        index = VectorIndex()
        emb = np.random.randn(2, 64).astype(np.float32)
        meta = [{"record_id": "r1", "diagnosis": "Eczema"}, {"record_id": "r2"}]
        index.add(emb, meta)

        assert index.get_metadata(0)["diagnosis"] == "Eczema"
        assert index.get_metadata(99) == {}


class TestRAGRetriever:
    """Test RAG retrieval service."""

    def _setup_retriever(self):
        """Create a retriever with indexed mock data."""
        index = VectorIndex()
        model = MockEmbeddingModel(dimension=768)

        # Index some records
        items = [{"image_path": f"img_{i}.jpg"} for i in range(10)]
        embeddings = model.embed_batch(items)
        metadata = [
            {
                "record_id": f"SCIN-{i:03d}",
                "diagnosis": "Eczema" if i < 5 else "Psoriasis",
                "icd_code": "L20.0" if i < 5 else "L40.0",
                "image_path": f"img_{i}.jpg",
            }
            for i in range(10)
        ]
        index.add(embeddings, metadata)
        return RAGRetriever(index, top_k=5)

    def test_query_by_image(self):
        """Image query returns results."""
        retriever = self._setup_retriever()
        response = retriever.query_by_image("img_0.jpg")
        assert len(response.results) == 5
        assert response.query_type == "image"
        assert response.latency_ms >= 0

    def test_query_by_text(self):
        """Text query returns results."""
        retriever = self._setup_retriever()
        response = retriever.query_by_text("itchy rash on arm")
        assert len(response.results) > 0
        assert response.query_type == "text"

    def test_results_have_metadata(self):
        """Results include SCIN metadata."""
        retriever = self._setup_retriever()
        response = retriever.query_by_image("img_0.jpg")
        first = response.results[0]
        assert first.record_id.startswith("SCIN-")
        assert first.diagnosis in ("Eczema", "Psoriasis")

    def test_caching(self):
        """Second query for same input uses cache."""
        retriever = self._setup_retriever()
        retriever.query_by_image("img_0.jpg")  # prime the cache
        response2 = retriever.query_by_image("img_0.jpg")
        assert response2.from_cache is True

    def test_clear_cache(self):
        """Cache can be cleared."""
        retriever = self._setup_retriever()
        retriever.query_by_image("img_0.jpg")
        retriever.clear_cache()
        response = retriever.query_by_image("img_0.jpg")
        assert response.from_cache is False
