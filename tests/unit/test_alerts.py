"""Tests for alert rules and evaluation."""

from __future__ import annotations

from src.observability.alerts import (
    AlertCategory,
    AlertEvaluator,
    AlertRule,
    AlertSeverity,
    _compare,
)
from src.observability.metrics import get_metrics_collector


class TestAlertComparison:
    """Test comparison logic."""

    def test_gt(self):
        assert _compare(10.0, 5.0, "gt") is True
        assert _compare(5.0, 10.0, "gt") is False

    def test_lt(self):
        assert _compare(5.0, 10.0, "lt") is True
        assert _compare(10.0, 5.0, "lt") is False

    def test_gte(self):
        assert _compare(10.0, 10.0, "gte") is True

    def test_lte(self):
        assert _compare(10.0, 10.0, "lte") is True


class TestAlertEvaluator:
    """Test alert rule evaluation."""

    def test_no_alerts_when_within_thresholds(self):
        """No alerts when metrics are within limits."""
        rules = [
            AlertRule(
                name="test_high",
                category=AlertCategory.LATENCY,
                severity=AlertSeverity.WARNING,
                metric_name="test_latency",
                threshold=1000.0,
                comparison="gt",
            ),
        ]
        # Record metrics below threshold
        collector = get_metrics_collector()
        collector.reset()
        collector.observe_latency("test_latency", 500.0)

        evaluator = AlertEvaluator(rules=rules)
        alerts = evaluator.evaluate_all()
        assert len(alerts) == 0

    def test_alert_fires_when_threshold_exceeded(self):
        """Alert fires when metric exceeds threshold."""
        rules = [
            AlertRule(
                name="test_high",
                category=AlertCategory.LATENCY,
                severity=AlertSeverity.WARNING,
                metric_name="test_latency",
                threshold=100.0,
                comparison="gt",
            ),
        ]
        collector = get_metrics_collector()
        collector.reset()
        collector.observe_latency("test_latency", 500.0)

        evaluator = AlertEvaluator(rules=rules)
        alerts = evaluator.evaluate_all()
        assert len(alerts) == 1
        assert alerts[0].rule.name == "test_high"
        assert alerts[0].actual_value == 500.0

    def test_alert_includes_message(self):
        """Fired alert includes descriptive message."""
        rules = [
            AlertRule(
                name="high_cpu",
                category=AlertCategory.INFRASTRUCTURE,
                severity=AlertSeverity.CRITICAL,
                metric_name="infra_cpu_percent",
                threshold=90.0,
                comparison="gt",
                description="CPU usage too high",
            ),
        ]
        collector = get_metrics_collector()
        collector.reset()
        collector.record("infra_cpu_percent", 95.0)

        evaluator = AlertEvaluator(rules=rules)
        alerts = evaluator.evaluate_all()
        assert len(alerts) == 1
        assert "CPU usage too high" in alerts[0].message

    def test_fired_alerts_history(self):
        """Evaluator tracks history of fired alerts."""
        rules = [
            AlertRule(
                name="test",
                category=AlertCategory.SAFETY,
                severity=AlertSeverity.CRITICAL,
                metric_name="test_metric",
                threshold=0.0,
                comparison="gt",
            ),
        ]
        collector = get_metrics_collector()
        collector.reset()
        collector.record("test_metric", 1.0)

        evaluator = AlertEvaluator(rules=rules)
        evaluator.evaluate_all()
        assert len(evaluator.fired_alerts) == 1
        evaluator.clear()
        assert len(evaluator.fired_alerts) == 0
