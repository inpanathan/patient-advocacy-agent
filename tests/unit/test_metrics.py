"""Tests for metrics collection."""

from __future__ import annotations

from src.observability.metrics import (
    MetricsCollector,
    record_infrastructure,
    record_prediction,
    record_retrieval,
)


class TestMetricsCollector:
    """Test the MetricsCollector."""

    def test_record_metric(self):
        """Single metric point is recorded."""
        collector = MetricsCollector()
        collector.record("test_metric", 42.0, {"env": "test"})
        metrics = collector.get_all_metrics()
        assert len(metrics) == 1
        assert metrics[0].name == "test_metric"
        assert metrics[0].value == 42.0

    def test_increment_counter(self):
        """Counter increments correctly."""
        collector = MetricsCollector()
        collector.increment("requests")
        collector.increment("requests")
        collector.increment("requests", 3.0)
        assert collector.get_counter("requests") == 5.0

    def test_histogram_statistics(self):
        """Histogram computes p50, p95, p99, mean."""
        collector = MetricsCollector()
        for i in range(100):
            collector.observe_latency("test_latency", float(i))
        stats = collector.get_histogram("test_latency")
        assert stats["count"] == 100.0
        assert stats["p50"] == 50.0
        assert stats["mean"] == 49.5

    def test_empty_histogram(self):
        """Empty histogram returns zeros."""
        collector = MetricsCollector()
        stats = collector.get_histogram("nonexistent")
        assert stats["count"] == 0.0
        assert stats["mean"] == 0.0

    def test_reset(self):
        """Reset clears all metrics."""
        collector = MetricsCollector()
        collector.record("x", 1.0)
        collector.increment("y")
        collector.observe_latency("z", 10.0)
        collector.reset()
        assert len(collector.get_all_metrics()) == 0
        assert collector.get_counter("y") == 0.0
        assert collector.get_histogram("z")["count"] == 0.0


class TestConvenienceFunctions:
    """Test convenience recording functions."""

    def test_record_prediction(self):
        """Prediction recording works."""
        record_prediction(
            session_id="sess-1",
            icd_codes=["L20.0"],
            confidence=0.78,
            escalated=False,
            latency_ms=150.0,
            fitzpatrick_type="III",
            language="hi",
        )

    def test_record_retrieval(self):
        """Retrieval recording works."""
        record_retrieval(
            query_type="text",
            num_results=5,
            top_score=0.85,
            latency_ms=50.0,
        )

    def test_record_infrastructure(self):
        """Infrastructure recording works."""
        record_infrastructure(
            cpu_percent=45.0,
            memory_mb=2048.0,
            gpu_percent=30.0,
            disk_percent=60.0,
        )
