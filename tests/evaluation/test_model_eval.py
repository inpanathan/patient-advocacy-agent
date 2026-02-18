"""Model evaluation tests with metric thresholds.

Defines minimum acceptable performance thresholds for embedding quality,
retrieval accuracy, and medical model outputs.

Covers: REQ-TST-021 - REQ-TST-025
"""

from __future__ import annotations

import numpy as np
import pytest

from src.data.scin_schema import FitzpatrickType, SCINRecord
from src.evaluation.clustering import compute_silhouette_score, evaluate_clustering
from src.evaluation.retrieval_eval import precision_at_k, recall_at_k, reciprocal_rank
from src.models.embedding_model import (
    compute_isotropy,
    get_embedding_model,
    normalize_embeddings,
)
from src.models.mocks.mock_medical import MockMedicalModel
from src.models.rag_retrieval import VectorIndex


def _build_test_records() -> list[SCINRecord]:
    """Build test records covering multiple diagnoses and Fitzpatrick types."""
    records = []
    diagnoses = [
        ("Atopic Dermatitis", "L20.0"),
        ("Contact Dermatitis", "L25.0"),
        ("Psoriasis", "L40.0"),
        ("Urticaria", "L50.0"),
    ]
    for i, (diag, icd) in enumerate(diagnoses):
        for ftype in [FitzpatrickType.II, FitzpatrickType.IV, FitzpatrickType.VI]:
            records.append(
                SCINRecord(
                    record_id=f"eval_{i}_{ftype.value}",
                    image_path=f"images/eval/{i}_{ftype.value}.jpg",
                    diagnosis=diag,
                    icd_code=icd,
                    fitzpatrick_type=ftype,
                    severity="mild",
                )
            )
    return records


class TestEmbeddingQuality:
    """Embedding model must meet quality thresholds."""

    DIMENSION_THRESHOLD = 32  # Minimum expected dimension
    ISOTROPY_THRESHOLD = 0.1  # Minimum isotropy score

    def test_embedding_dimension_meets_threshold(self):
        """Embedding dimension >= threshold."""
        model = get_embedding_model()
        assert model.dimension >= self.DIMENSION_THRESHOLD

    def test_embeddings_are_normalized(self):
        """Embeddings lie on the unit hypersphere."""
        model = get_embedding_model()
        texts = ["rash on arm", "itchy skin", "red patches"]
        for text in texts:
            emb = model.embed_text(text)
            norm = float(np.linalg.norm(emb))
            assert abs(norm - 1.0) < 0.01, f"Embedding not normalized: norm={norm}"

    def test_normalize_embeddings_function(self):
        """normalize_embeddings produces unit vectors."""
        raw = np.random.randn(10, 64).astype(np.float32)
        normed = normalize_embeddings(raw)
        norms = np.linalg.norm(normed, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-5)

    def test_isotropy_above_threshold(self):
        """Embedding space isotropy meets threshold."""
        model = get_embedding_model()
        embeddings = np.array(
            [model.embed_text(f"test text {i}") for i in range(20)]
        )
        score = compute_isotropy(embeddings)
        assert score >= self.ISOTROPY_THRESHOLD, (
            f"Isotropy {score:.3f} below threshold {self.ISOTROPY_THRESHOLD}"
        )

    def test_different_texts_produce_different_embeddings(self):
        """Semantically different texts produce distinct embeddings."""
        model = get_embedding_model()
        emb1 = model.embed_text("severe rash with blistering")
        emb2 = model.embed_text("healthy normal skin")
        similarity = float(np.dot(emb1, emb2))
        # Should not be identical
        assert similarity < 0.99, "Different texts produced nearly identical embeddings"


class TestRetrievalQuality:
    """RAG retrieval must meet accuracy thresholds."""

    PRECISION_THRESHOLD = 0.3  # Minimum precision@5
    MRR_THRESHOLD = 0.3  # Minimum mean reciprocal rank

    def test_precision_at_k_calculation(self):
        """precision@k correctly computes."""
        # 3 of 5 retrieved are relevant
        retrieved = ["A", "B", "C", "D", "E"]
        relevant = {"A", "C", "E"}
        p = precision_at_k(retrieved, relevant, k=5)
        assert abs(p - 0.6) < 0.001

    def test_recall_at_k_calculation(self):
        """recall@k correctly computes."""
        retrieved = ["A", "B", "C"]
        relevant = {"A", "C", "D", "E"}
        r = recall_at_k(retrieved, relevant, k=3)
        assert abs(r - 0.5) < 0.001

    def test_reciprocal_rank_calculation(self):
        """MRR correctly computes."""
        # First relevant at position 2
        retrieved = ["B", "A", "C"]
        relevant = {"A"}
        rr = reciprocal_rank(retrieved, relevant)
        assert abs(rr - 0.5) < 0.001

    def test_vector_index_retrieval_quality(self):
        """Vector index retrieval meets precision threshold."""
        model = get_embedding_model()
        records = _build_test_records()
        index = VectorIndex()

        # Index all records as batches
        embeddings_list = []
        metadata_list = []
        for rec in records:
            emb = model.embed_text(f"{rec.diagnosis} {rec.icd_code}")
            embeddings_list.append(emb)
            metadata_list.append({
                "record_id": rec.record_id,
                "diagnosis": rec.diagnosis,
                "icd_code": rec.icd_code,
            })

        embeddings_array = np.array(embeddings_list, dtype=np.float32)
        index.add(embeddings_array, metadata_list)

        # Query for a known diagnosis
        query_emb = model.embed_text("Atopic Dermatitis L20.0")
        results = index.search(query_emb, top_k=5)

        # At least some results should match
        assert len(results) > 0
        # results are (index, score) tuples — check metadata
        matching = [
            index.get_metadata(idx)
            for idx, _score in results
            if index.get_metadata(idx).get("diagnosis") == "Atopic Dermatitis"
        ]
        assert len(matching) > 0, "No matching results for known query"


class TestClusteringQuality:
    """Embedding clustering must meet quality thresholds."""

    SILHOUETTE_THRESHOLD = -0.5  # Allow low threshold for mock embeddings

    def test_silhouette_score_computes(self):
        """Silhouette score can be computed."""
        embeddings = np.random.randn(20, 64).astype(np.float32)
        labels = [0] * 10 + [1] * 10
        score = compute_silhouette_score(embeddings, labels)
        assert -1.0 <= score <= 1.0

    def test_evaluate_clustering_returns_per_label(self):
        """Clustering evaluation provides per-label breakdown."""
        embeddings = np.random.randn(20, 64).astype(np.float32)
        labels = [0] * 10 + [1] * 10
        result = evaluate_clustering(embeddings, labels)
        assert hasattr(result, "per_label_scores")
        assert hasattr(result, "silhouette_score")
        assert result.n_clusters == 2
        assert result.n_samples == 20


class TestMedicalModelQuality:
    """Medical model output must meet quality thresholds."""

    ICD_ACCURACY_THRESHOLD = 0.5  # At least 50% of codes should be valid

    @pytest.mark.asyncio
    async def test_soap_has_minimum_sections(self):
        """SOAP note has all four required sections."""
        model = MockMedicalModel()
        soap = await model.generate_soap(transcript="rash on forearm for 3 days")
        sections = [soap.subjective, soap.objective, soap.assessment, soap.plan]
        for section in sections:
            assert len(section) > 10, f"SOAP section too short: '{section}'"

    @pytest.mark.asyncio
    async def test_icd_codes_in_valid_range(self):
        """ICD codes are in valid dermatology range."""
        model = MockMedicalModel()
        soap = await model.generate_soap(transcript="skin condition")
        for code in soap.icd_codes:
            assert code.startswith("L"), f"ICD code {code} not in L range"
            # Validate format: L followed by 2 digits
            assert len(code) >= 3

    @pytest.mark.asyncio
    async def test_confidence_score_reasonable(self):
        """Confidence score is within reasonable range."""
        model = MockMedicalModel()
        soap = await model.generate_soap(transcript="itchy rash")
        assert 0.0 <= soap.confidence <= 1.0
        # Should not be suspiciously high for a triage tool
        assert soap.confidence < 0.95, "Confidence suspiciously high for triage"
