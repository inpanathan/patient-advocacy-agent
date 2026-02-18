"""Tests for the dashboard aggregator service."""

from __future__ import annotations

import time

from src.observability.alerts import AlertEvaluator
from src.observability.audit import AuditRecord, AuditTrail
from src.observability.dashboard_aggregator import DashboardAggregator, DashboardState
from src.observability.log_buffer import LogBuffer, LogRecord
from src.observability.metrics import MetricsCollector
from src.observability.safety_evaluator import SafetyEvaluator
from src.utils.session import SessionStore


def _make_aggregator(
    collector: MetricsCollector | None = None,
) -> DashboardAggregator:
    """Create a DashboardAggregator with fresh singletons."""
    # Reset global singletons for test isolation
    import src.observability.log_buffer as lb_mod
    import src.observability.metrics as m_mod

    if collector is None:
        collector = MetricsCollector()
    m_mod._collector = collector

    log_buffer = LogBuffer(max_size=100)
    lb_mod._log_buffer = log_buffer

    state = DashboardState(
        start_time=time.monotonic(),
        session_store=SessionStore(),
        alert_evaluator=AlertEvaluator(),
        audit_trail=AuditTrail(),
        safety_evaluator=SafetyEvaluator(),
    )
    return DashboardAggregator(state)


class TestHealthOverview:
    """Tests for get_health_overview."""

    def test_returns_correct_keys(self) -> None:
        agg = _make_aggregator()
        result = agg.get_health_overview()
        assert "status" in result
        assert "uptime_seconds" in result
        assert "active_sessions" in result
        assert "predictions_total" in result
        assert result["status"] == "ok"

    def test_counts_predictions(self) -> None:
        collector = MetricsCollector()
        collector.increment("predictions_total", 5)
        collector.increment("escalations_total", 2)
        agg = _make_aggregator(collector)
        result = agg.get_health_overview()
        assert result["predictions_total"] == 5
        assert result["escalations_total"] == 2


class TestPerformanceMetrics:
    """Tests for get_performance_metrics."""

    def test_includes_latency_and_confidence(self) -> None:
        collector = MetricsCollector()
        collector.observe_latency("prediction_latency", 100.0)
        collector.observe_latency("prediction_latency", 200.0)
        collector.record("prediction_confidence", 0.85, labels={"session_id": "s1"})
        agg = _make_aggregator(collector)
        result = agg.get_performance_metrics()
        assert "prediction_latency" in result
        assert result["prediction_latency"]["count"] == 2.0
        assert len(result["confidence_values"]) == 1

    def test_icd_code_counts(self) -> None:
        collector = MetricsCollector()
        collector.increment("icd_code_L20.0", 3)
        collector.increment("icd_code_L30.9", 1)
        agg = _make_aggregator(collector)
        result = agg.get_performance_metrics()
        assert result["icd_code_counts"]["L20.0"] == 3
        assert result["icd_code_counts"]["L30.9"] == 1


class TestBiasMetrics:
    """Tests for get_bias_metrics."""

    def test_groups_by_fitzpatrick(self) -> None:
        collector = MetricsCollector()
        collector.record(
            "prediction_confidence",
            0.9,
            labels={"fitzpatrick_type": "I", "language": "en"},
        )
        collector.record(
            "prediction_confidence",
            0.7,
            labels={"fitzpatrick_type": "VI", "language": "hi"},
        )
        agg = _make_aggregator(collector)
        result = agg.get_bias_metrics()
        assert "I" in result["by_fitzpatrick"]
        assert "VI" in result["by_fitzpatrick"]
        assert result["by_fitzpatrick"]["I"]["mean_confidence"] == 0.9
        assert "en" in result["by_language"]
        assert "hi" in result["by_language"]


class TestTimeSeries:
    """Tests for get_time_series."""

    def test_bucketing(self) -> None:
        collector = MetricsCollector()
        now = time.time()
        from src.observability.metrics import MetricPoint

        # Add metrics at known timestamps
        collector._metrics.append(MetricPoint("test_metric", 10.0, {}, now))
        collector._metrics.append(MetricPoint("test_metric", 20.0, {}, now + 1))
        collector._metrics.append(MetricPoint("test_metric", 30.0, {}, now + 61))

        agg = _make_aggregator(collector)
        result = agg.get_time_series("test_metric", bucket_seconds=60)
        assert result["metric"] == "test_metric"
        assert len(result["buckets"]) == 2  # Two 60s buckets

    def test_empty_metric(self) -> None:
        agg = _make_aggregator()
        result = agg.get_time_series("nonexistent_metric", bucket_seconds=60)
        assert result["buckets"] == []


class TestRequestStats:
    """Tests for get_request_stats."""

    def test_aggregates_by_path(self) -> None:
        collector = MetricsCollector()
        collector.increment("request_count", 5)
        collector.increment("request_errors", 1)
        collector.observe_latency(
            "request_latency",
            50.0,
            labels={"method": "GET", "path": "/api/v1/sessions", "status": "200"},
        )
        collector.observe_latency(
            "request_latency",
            100.0,
            labels={"method": "GET", "path": "/api/v1/sessions", "status": "200"},
        )
        agg = _make_aggregator(collector)
        result = agg.get_request_stats()
        assert result["total_requests"] == 5
        assert result["total_errors"] == 1


class TestSafetyMetrics:
    """Tests for get_safety_metrics."""

    def test_returns_defaults_when_empty(self) -> None:
        agg = _make_aggregator()
        result = agg.get_safety_metrics()
        assert result["pass_rate"] == 1.0
        assert result["total_checked"] == 0


class TestLogs:
    """Tests for get_logs."""

    def test_returns_filtered_logs(self) -> None:
        import src.observability.log_buffer as lb_mod

        agg = _make_aggregator()

        # Append to the buffer _after_ _make_aggregator sets the global
        buf = lb_mod._log_buffer
        assert buf is not None
        buf.append(
            LogRecord(
                timestamp="2025-01-01T00:00:00+00:00",
                level="ERROR",
                event="test_error",
                logger_name="test",
                fields={"detail": "something broke"},
            )
        )
        buf.append(
            LogRecord(
                timestamp="2025-01-01T00:00:01+00:00",
                level="INFO",
                event="test_info",
                logger_name="test",
                fields={},
            )
        )

        result = agg.get_logs(level="ERROR", limit=10)
        assert len(result) == 1
        assert result[0]["event"] == "test_error"


class TestAuditRecords:
    """Tests for get_audit_records."""

    def test_returns_records(self) -> None:
        collector = MetricsCollector()
        import src.observability.metrics as m_mod

        m_mod._collector = collector

        state = DashboardState(
            start_time=time.monotonic(),
            session_store=SessionStore(),
            alert_evaluator=AlertEvaluator(),
            audit_trail=AuditTrail(),
            safety_evaluator=SafetyEvaluator(),
        )
        assert state.audit_trail is not None
        state.audit_trail.record(
            AuditRecord(
                trace_id="t1",
                session_id="s1",
                icd_codes=["L20.0"],
                confidence=0.9,
            )
        )
        agg = DashboardAggregator(state)
        result = agg.get_audit_records(limit=10)
        assert len(result) == 1
        assert result[0]["trace_id"] == "t1"
