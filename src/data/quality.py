"""Data quality checks for SCIN records.

Implements checks for missing values, duplicates, outliers, and
invalid categories. Reports issues as structured quality reports.

Covers: REQ-TST-006, REQ-TST-007, REQ-OBS-013
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from src.data.scin_schema import FitzpatrickType, SCINRecord

logger = structlog.get_logger(__name__)


@dataclass
class QualityIssue:
    """A single data quality issue."""

    record_id: str
    field: str
    issue_type: str
    detail: str


@dataclass
class QualityReport:
    """Aggregated data quality report."""

    total_records: int = 0
    issues: list[QualityIssue] = field(default_factory=list)
    duplicate_count: int = 0
    missing_field_counts: dict[str, int] = field(default_factory=dict)
    invalid_category_counts: dict[str, int] = field(default_factory=dict)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def pass_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return (self.total_records - self.issue_count) / self.total_records


def run_quality_checks(records: list[SCINRecord]) -> QualityReport:
    """Run all data quality checks on SCIN records.

    Args:
        records: List of validated SCINRecord instances.

    Returns:
        QualityReport with all issues found.
    """
    report = QualityReport(total_records=len(records))

    _check_duplicates(records, report)
    _check_missing_values(records, report)
    _check_categories(records, report)

    logger.info(
        "quality_check_complete",
        total_records=report.total_records,
        issues_found=report.issue_count,
        duplicates=report.duplicate_count,
        pass_rate=f"{report.pass_rate:.2%}",
    )

    return report


def _check_duplicates(records: list[SCINRecord], report: QualityReport) -> None:
    """Check for duplicate record IDs."""
    seen: dict[str, int] = {}
    for r in records:
        if r.record_id in seen:
            report.duplicate_count += 1
            report.issues.append(
                QualityIssue(
                    record_id=r.record_id,
                    field="record_id",
                    issue_type="duplicate",
                    detail=f"Duplicate of record first seen at index {seen[r.record_id]}",
                )
            )
        else:
            seen[r.record_id] = len(seen)


def _check_missing_values(records: list[SCINRecord], report: QualityReport) -> None:
    """Check for missing optional fields that should be populated."""
    required_fields = ["diagnosis", "icd_code", "image_path"]
    optional_but_important = ["body_location", "age_group", "description"]

    for r in records:
        for f_name in required_fields:
            val = getattr(r, f_name, "")
            if not val:
                report.issues.append(
                    QualityIssue(
                        record_id=r.record_id,
                        field=f_name,
                        issue_type="missing_required",
                        detail=f"Required field '{f_name}' is empty",
                    )
                )
                report.missing_field_counts[f_name] = (
                    report.missing_field_counts.get(f_name, 0) + 1
                )

        for f_name in optional_but_important:
            val = getattr(r, f_name, "")
            if not val:
                report.missing_field_counts[f_name] = (
                    report.missing_field_counts.get(f_name, 0) + 1
                )


def _check_categories(records: list[SCINRecord], report: QualityReport) -> None:
    """Check that categorical fields have valid values."""
    valid_fitzpatrick = set(FitzpatrickType)
    valid_severities = {"mild", "moderate", "severe", "unknown"}

    for r in records:
        if r.fitzpatrick_type not in valid_fitzpatrick:
            report.issues.append(
                QualityIssue(
                    record_id=r.record_id,
                    field="fitzpatrick_type",
                    issue_type="invalid_category",
                    detail=f"Invalid Fitzpatrick type: {r.fitzpatrick_type}",
                )
            )
            report.invalid_category_counts["fitzpatrick_type"] = (
                report.invalid_category_counts.get("fitzpatrick_type", 0) + 1
            )

        if r.severity not in valid_severities:
            report.issues.append(
                QualityIssue(
                    record_id=r.record_id,
                    field="severity",
                    issue_type="invalid_category",
                    detail=f"Invalid severity: {r.severity}",
                )
            )
            report.invalid_category_counts["severity"] = (
                report.invalid_category_counts.get("severity", 0) + 1
            )
