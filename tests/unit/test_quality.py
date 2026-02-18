"""Tests for data quality checks."""

from __future__ import annotations

from src.data.quality import run_quality_checks
from src.data.scin_schema import SCINRecord


def _make_record(**overrides) -> SCINRecord:
    defaults = {
        "record_id": "SCIN-001",
        "image_path": "images/001.jpg",
        "diagnosis": "Atopic Dermatitis",
        "icd_code": "L20.0",
        "fitzpatrick_type": "III",
        "severity": "moderate",
    }
    defaults.update(overrides)
    return SCINRecord(**defaults)


class TestQualityChecks:
    """Test data quality check suite."""

    def test_clean_data_no_issues(self):
        """Clean data passes quality checks with no issues."""
        records = [
            _make_record(record_id="SCIN-001"),
            _make_record(record_id="SCIN-002", fitzpatrick_type="V"),
        ]
        report = run_quality_checks(records)
        assert report.issue_count == 0
        assert report.pass_rate == 1.0

    def test_duplicate_detection(self):
        """Duplicate record IDs are detected."""
        records = [
            _make_record(record_id="SCIN-001"),
            _make_record(record_id="SCIN-001"),
        ]
        report = run_quality_checks(records)
        assert report.duplicate_count == 1
        assert any(i.issue_type == "duplicate" for i in report.issues)

    def test_missing_optional_fields_tracked(self):
        """Missing optional fields are tracked in counts."""
        records = [
            _make_record(record_id="SCIN-001", body_location="", description=""),
        ]
        report = run_quality_checks(records)
        assert "body_location" in report.missing_field_counts
        assert "description" in report.missing_field_counts

    def test_pass_rate_calculation(self):
        """Pass rate reflects issue count vs total."""
        records = [
            _make_record(record_id="SCIN-001"),
            _make_record(record_id="SCIN-001"),  # duplicate
            _make_record(record_id="SCIN-002"),
        ]
        report = run_quality_checks(records)
        assert report.total_records == 3
        assert report.issue_count == 1
        assert abs(report.pass_rate - 2 / 3) < 0.01

    def test_empty_records_zero_pass_rate(self):
        """Empty record list has zero pass rate."""
        report = run_quality_checks([])
        assert report.pass_rate == 0.0
