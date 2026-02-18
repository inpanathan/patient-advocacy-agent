"""Alert rule definitions and evaluation.

Defines thresholds for data drift, model performance drops,
latency spikes, and safety incidents. Evaluates conditions
and triggers alerts.

Covers: REQ-OBS-049 - REQ-OBS-052
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import structlog

from src.observability.metrics import get_metrics_collector

logger = structlog.get_logger(__name__)


class AlertSeverity(StrEnum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCategory(StrEnum):
    """Alert categories."""

    DATA_DRIFT = "data_drift"
    MODEL_PERFORMANCE = "model_performance"
    LATENCY = "latency"
    SAFETY = "safety"
    INFRASTRUCTURE = "infrastructure"
    ESCALATION = "escalation"


@dataclass
class AlertRule:
    """A single alert rule definition."""

    name: str
    category: AlertCategory
    severity: AlertSeverity
    metric_name: str
    threshold: float
    comparison: str = "gt"  # gt, lt, gte, lte
    description: str = ""
    runbook_url: str = ""


@dataclass
class AlertEvent:
    """A triggered alert event."""

    rule: AlertRule
    actual_value: float
    message: str
    labels: dict[str, str] = field(default_factory=dict)


# ---- Default Alert Rules ----

DEFAULT_RULES: list[AlertRule] = [
    AlertRule(
        name="high_prediction_latency",
        category=AlertCategory.LATENCY,
        severity=AlertSeverity.WARNING,
        metric_name="prediction_latency",
        threshold=2000.0,
        comparison="gt",
        description="Prediction latency exceeds 2 seconds (p95)",
        runbook_url="docs/runbook/high_latency.md",
    ),
    AlertRule(
        name="low_prediction_confidence",
        category=AlertCategory.MODEL_PERFORMANCE,
        severity=AlertSeverity.WARNING,
        metric_name="prediction_confidence",
        threshold=0.3,
        comparison="lt",
        description="Average prediction confidence below 0.3",
        runbook_url="docs/runbook/low_confidence.md",
    ),
    AlertRule(
        name="high_escalation_rate",
        category=AlertCategory.SAFETY,
        severity=AlertSeverity.CRITICAL,
        metric_name="escalation_rate",
        threshold=0.5,
        comparison="gt",
        description="Escalation rate exceeds 50%",
        runbook_url="docs/runbook/high_escalation.md",
    ),
    AlertRule(
        name="high_cpu_usage",
        category=AlertCategory.INFRASTRUCTURE,
        severity=AlertSeverity.WARNING,
        metric_name="infra_cpu_percent",
        threshold=90.0,
        comparison="gt",
        description="CPU usage exceeds 90%",
        runbook_url="docs/runbook/high_cpu.md",
    ),
    AlertRule(
        name="high_memory_usage",
        category=AlertCategory.INFRASTRUCTURE,
        severity=AlertSeverity.WARNING,
        metric_name="infra_memory_mb",
        threshold=8192.0,
        comparison="gt",
        description="Memory usage exceeds 8GB",
        runbook_url="docs/runbook/high_memory.md",
    ),
    AlertRule(
        name="retrieval_latency_spike",
        category=AlertCategory.LATENCY,
        severity=AlertSeverity.WARNING,
        metric_name="retrieval_latency",
        threshold=1000.0,
        comparison="gt",
        description="RAG retrieval latency exceeds 1 second (p95)",
        runbook_url="docs/runbook/retrieval_latency.md",
    ),
]


_COMPARATORS: dict[str, object] = {
    "gt": lambda a, t: a > t,
    "lt": lambda a, t: a < t,
    "gte": lambda a, t: a >= t,
    "lte": lambda a, t: a <= t,
}


def _compare(actual: float, threshold: float, comparison: str) -> bool:
    """Compare actual value against threshold."""
    fn = _COMPARATORS.get(comparison)
    if fn is None:
        return False
    return bool(fn(actual, threshold))  # type: ignore[operator]


class AlertEvaluator:
    """Evaluates alert rules against current metrics."""

    def __init__(self, rules: list[AlertRule] | None = None) -> None:
        self._rules = rules or DEFAULT_RULES
        self._fired_alerts: list[AlertEvent] = []

    def evaluate_all(self) -> list[AlertEvent]:
        """Evaluate all rules and return triggered alerts."""
        collector = get_metrics_collector()
        alerts = []

        for rule in self._rules:
            histogram = collector.get_histogram(rule.metric_name)
            if histogram["count"] > 0:
                # Use p95 for latency metrics, mean for others
                actual = histogram["p95"] if "latency" in rule.metric_name else histogram["mean"]
            else:
                # Check latest metric point
                all_metrics = collector.get_all_metrics()
                matching = [m for m in all_metrics if m.name == rule.metric_name]
                if not matching:
                    continue
                actual = matching[-1].value

            if _compare(actual, rule.threshold, rule.comparison):
                event = AlertEvent(
                    rule=rule,
                    actual_value=actual,
                    message=f"[{rule.severity.upper()}] {rule.description}: "
                    f"actual={actual:.2f}, threshold={rule.threshold:.2f}",
                )
                alerts.append(event)
                logger.warning(
                    "alert_triggered",
                    alert=rule.name,
                    severity=rule.severity,
                    actual=f"{actual:.2f}",
                    threshold=f"{rule.threshold:.2f}",
                )

        self._fired_alerts.extend(alerts)
        return alerts

    @property
    def fired_alerts(self) -> list[AlertEvent]:
        """Get all previously fired alerts."""
        return list(self._fired_alerts)

    def clear(self) -> None:
        """Clear fired alerts."""
        self._fired_alerts.clear()
