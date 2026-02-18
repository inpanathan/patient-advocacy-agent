"""Metrics collection for model performance, data quality, and infrastructure.

Provides a central MetricsCollector that records structured metrics for
dashboards and alerting. In production, these would feed into Prometheus/Grafana.

Covers: REQ-OBS-019 - REQ-OBS-032, REQ-OBS-039 - REQ-OBS-041
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""

    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """Central metrics collector for all observability data.

    Records metrics in memory. In production, this would push to
    Prometheus, CloudWatch, or a similar metrics backend.
    """

    def __init__(self) -> None:
        self._metrics: list[MetricPoint] = []
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)

    def record(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a metric data point."""
        point = MetricPoint(name=name, value=value, labels=labels or {})
        self._metrics.append(point)
        logger.debug("metric_recorded", name=name, value=value, labels=labels)

    def increment(self, name: str, amount: float = 1.0) -> None:
        """Increment a counter metric."""
        self._counters[name] += amount

    def observe_latency(
        self, name: str, latency_ms: float, labels: dict[str, str] | None = None,
    ) -> None:
        """Record a latency observation for histogram."""
        self._histograms[name].append(latency_ms)
        self.record(f"{name}_ms", latency_ms, labels)

    def get_counter(self, name: str) -> float:
        """Get current counter value."""
        return self._counters.get(name, 0.0)

    def get_histogram(self, name: str) -> dict[str, float]:
        """Get histogram statistics (p50, p95, p99, mean)."""
        values = self._histograms.get(name, [])
        if not values:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0, "count": 0.0}
        sorted_v = sorted(values)
        n = len(sorted_v)
        return {
            "p50": sorted_v[int(n * 0.50)],
            "p95": sorted_v[min(int(n * 0.95), n - 1)],
            "p99": sorted_v[min(int(n * 0.99), n - 1)],
            "mean": sum(sorted_v) / n,
            "count": float(n),
        }

    def get_all_metrics(self) -> list[MetricPoint]:
        """Get all recorded metric points."""
        return list(self._metrics)

    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        self._metrics.clear()
        self._counters.clear()
        self._histograms.clear()


# Singleton
_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    global _collector  # noqa: PLW0603
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


# ---- Convenience recording functions ----


def record_prediction(
    session_id: str,
    icd_codes: list[str],
    confidence: float,
    escalated: bool,
    latency_ms: float,
    fitzpatrick_type: str = "",
    language: str = "",
) -> None:
    """Record a prediction event with all relevant dimensions.

    Covers: REQ-OBS-027 - REQ-OBS-032
    """
    collector = get_metrics_collector()
    labels = {
        "session_id": session_id,
        "escalated": str(escalated),
        "fitzpatrick_type": fitzpatrick_type,
        "language": language,
    }
    collector.record("prediction_confidence", confidence, labels)
    collector.observe_latency("prediction_latency", latency_ms, labels)
    collector.increment("predictions_total")
    if escalated:
        collector.increment("escalations_total")

    for code in icd_codes:
        collector.increment(f"icd_code_{code}")

    logger.info(
        "prediction_recorded",
        session_id=session_id,
        icd_codes=icd_codes,
        confidence=f"{confidence:.2f}",
        escalated=escalated,
        latency_ms=f"{latency_ms:.1f}",
    )


def record_retrieval(
    query_type: str,
    num_results: int,
    top_score: float,
    latency_ms: float,
) -> None:
    """Record a RAG retrieval event.

    Covers: REQ-OBS-029
    """
    collector = get_metrics_collector()
    labels = {"query_type": query_type}
    collector.record("retrieval_top_score", top_score, labels)
    collector.record("retrieval_num_results", float(num_results), labels)
    collector.observe_latency("retrieval_latency", latency_ms, labels)
    collector.increment("retrievals_total")


def record_infrastructure(
    cpu_percent: float,
    memory_mb: float,
    gpu_percent: float = 0.0,
    disk_percent: float = 0.0,
) -> None:
    """Record infrastructure metrics.

    Covers: REQ-OBS-039
    """
    collector = get_metrics_collector()
    collector.record("infra_cpu_percent", cpu_percent)
    collector.record("infra_memory_mb", memory_mb)
    collector.record("infra_gpu_percent", gpu_percent)
    collector.record("infra_disk_percent", disk_percent)
