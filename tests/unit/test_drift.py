"""Tests for data drift detection."""

from __future__ import annotations

from src.data.drift import check_drift
from src.data.scin_schema import SCINDatasetStats


class TestDriftDetection:
    """Test drift detection between baseline and current stats."""

    def test_no_drift_identical_stats(self):
        """Identical stats produce no drift alerts."""
        stats = SCINDatasetStats(
            total_records=100,
            records_per_diagnosis={"Eczema": 50, "Psoriasis": 50},
            records_per_fitzpatrick={"I": 20, "II": 20, "III": 20, "IV": 20, "V": 20},
            records_per_severity={"mild": 40, "moderate": 40, "severe": 20},
        )
        report = check_drift(stats, stats)
        assert not report.has_drift
        assert report.checked_metrics > 0

    def test_count_drift_detected(self):
        """Significant record count change triggers alert."""
        baseline = SCINDatasetStats(total_records=100)
        current = SCINDatasetStats(total_records=50)  # 50% drop

        report = check_drift(baseline, current, count_threshold=0.2)
        assert report.has_drift
        assert any(a.metric_name == "total_records" for a in report.alerts)

    def test_count_drift_within_threshold(self):
        """Small count change within threshold produces no alert."""
        baseline = SCINDatasetStats(total_records=100)
        current = SCINDatasetStats(total_records=95)  # 5% drop

        report = check_drift(baseline, current, count_threshold=0.2)
        count_alerts = [a for a in report.alerts if a.metric_name == "total_records"]
        assert len(count_alerts) == 0

    def test_distribution_drift_detected(self):
        """Shifted diagnosis distribution triggers alert."""
        baseline = SCINDatasetStats(
            total_records=100,
            records_per_diagnosis={"Eczema": 50, "Psoriasis": 50},
        )
        current = SCINDatasetStats(
            total_records=100,
            records_per_diagnosis={"Eczema": 90, "Psoriasis": 10},  # big shift
        )
        report = check_drift(baseline, current, distribution_threshold=0.15)
        assert report.has_drift

    def test_critical_severity_for_large_drift(self):
        """Very large drift produces critical alert."""
        baseline = SCINDatasetStats(total_records=100)
        current = SCINDatasetStats(total_records=10)  # 90% drop

        report = check_drift(baseline, current, count_threshold=0.2)
        assert report.has_critical

    def test_new_category_in_current(self):
        """New category appearing in current data is detected."""
        baseline = SCINDatasetStats(
            total_records=100,
            records_per_diagnosis={"Eczema": 100},
        )
        current = SCINDatasetStats(
            total_records=100,
            records_per_diagnosis={"Eczema": 50, "NewCondition": 50},
        )
        report = check_drift(baseline, current, distribution_threshold=0.15)
        assert report.has_drift
