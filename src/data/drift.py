"""Data drift detection for SCIN dataset.

Compares current data statistics against stored baselines to detect
distribution shifts that could affect model performance.

Covers: REQ-TST-008, REQ-TST-009, REQ-OBS-015, REQ-OBS-017, REQ-OBS-018
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from src.data.scin_schema import SCINDatasetStats

logger = structlog.get_logger(__name__)


@dataclass
class DriftAlert:
    """A single drift detection alert."""

    metric_name: str
    baseline_value: float
    current_value: float
    threshold: float
    severity: str  # "warning" or "critical"

    @property
    def drift_magnitude(self) -> float:
        if self.baseline_value == 0:
            return float("inf") if self.current_value != 0 else 0.0
        return abs(self.current_value - self.baseline_value) / self.baseline_value


@dataclass
class DriftReport:
    """Aggregated drift detection report."""

    alerts: list[DriftAlert] = field(default_factory=list)
    checked_metrics: int = 0
    has_critical: bool = False

    @property
    def has_drift(self) -> bool:
        return len(self.alerts) > 0


def check_drift(
    baseline: SCINDatasetStats,
    current: SCINDatasetStats,
    *,
    count_threshold: float = 0.2,
    distribution_threshold: float = 0.15,
) -> DriftReport:
    """Compare current stats against baseline for drift.

    Args:
        baseline: Previously stored baseline statistics.
        current: Freshly computed statistics from current data.
        count_threshold: Relative change threshold for record counts.
        distribution_threshold: Relative change threshold for distributions.

    Returns:
        DriftReport with any detected drift alerts.
    """
    report = DriftReport()

    # Check total record count drift
    _check_count_drift(
        report, "total_records",
        baseline.total_records, current.total_records,
        count_threshold,
    )
    report.checked_metrics += 1

    # Check diagnosis distribution drift
    _check_distribution_drift(
        report, "diagnosis",
        baseline.records_per_diagnosis, current.records_per_diagnosis,
        distribution_threshold,
    )
    report.checked_metrics += 1

    # Check Fitzpatrick type distribution drift
    _check_distribution_drift(
        report, "fitzpatrick_type",
        baseline.records_per_fitzpatrick, current.records_per_fitzpatrick,
        distribution_threshold,
    )
    report.checked_metrics += 1

    # Check severity distribution drift
    _check_distribution_drift(
        report, "severity",
        baseline.records_per_severity, current.records_per_severity,
        distribution_threshold,
    )
    report.checked_metrics += 1

    if report.has_drift:
        logger.warning(
            "data_drift_detected",
            alert_count=len(report.alerts),
            has_critical=report.has_critical,
            metrics_checked=report.checked_metrics,
        )
    else:
        logger.info(
            "drift_check_passed",
            metrics_checked=report.checked_metrics,
        )

    return report


def _check_count_drift(
    report: DriftReport,
    metric_name: str,
    baseline_val: int,
    current_val: int,
    threshold: float,
) -> None:
    """Check if a count metric has drifted beyond threshold."""
    if baseline_val == 0:
        return

    relative_change = abs(current_val - baseline_val) / baseline_val
    if relative_change > threshold:
        severity = "critical" if relative_change > threshold * 2 else "warning"
        alert = DriftAlert(
            metric_name=metric_name,
            baseline_value=float(baseline_val),
            current_value=float(current_val),
            threshold=threshold,
            severity=severity,
        )
        report.alerts.append(alert)
        if severity == "critical":
            report.has_critical = True


def _check_distribution_drift(
    report: DriftReport,
    metric_name: str,
    baseline_dist: dict[str, int],
    current_dist: dict[str, int],
    threshold: float,
) -> None:
    """Check if a categorical distribution has drifted."""
    all_keys = set(baseline_dist) | set(current_dist)
    baseline_total = sum(baseline_dist.values()) or 1
    current_total = sum(current_dist.values()) or 1

    for key in all_keys:
        baseline_pct = baseline_dist.get(key, 0) / baseline_total
        current_pct = current_dist.get(key, 0) / current_total
        diff = abs(current_pct - baseline_pct)

        if diff > threshold:
            severity = "critical" if diff > threshold * 2 else "warning"
            alert = DriftAlert(
                metric_name=f"{metric_name}.{key}",
                baseline_value=baseline_pct,
                current_value=current_pct,
                threshold=threshold,
                severity=severity,
            )
            report.alerts.append(alert)
            if severity == "critical":
                report.has_critical = True
