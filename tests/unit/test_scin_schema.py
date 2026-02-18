"""Tests for SCIN database schema and validation."""

from __future__ import annotations

import pytest

from src.data.scin_schema import FitzpatrickType, SCINDatasetStats, SCINRecord


class TestSCINRecord:
    """Test SCIN record schema validation."""

    def _valid_record(self, **overrides) -> dict:
        defaults = {
            "record_id": "SCIN-001",
            "image_path": "images/001.jpg",
            "diagnosis": "Atopic Dermatitis",
            "icd_code": "L20.0",
            "fitzpatrick_type": "III",
            "severity": "moderate",
        }
        defaults.update(overrides)
        return defaults

    def test_valid_record(self):
        """Valid record passes schema validation."""
        r = SCINRecord(**self._valid_record())
        assert r.record_id == "SCIN-001"
        assert r.fitzpatrick_type == FitzpatrickType.III

    def test_invalid_icd_code_format(self):
        """Non-matching ICD code pattern is rejected."""
        with pytest.raises(ValueError):
            SCINRecord(**self._valid_record(icd_code="INVALID"))

    def test_non_skin_relevant_icd_code(self):
        """Non-skin-relevant ICD codes are rejected."""
        with pytest.raises(ValueError, match="Expected skin-relevant ICD code"):
            SCINRecord(**self._valid_record(icd_code="A01.0"))

    def test_fungal_skin_icd_code_accepted(self):
        """B35.x (fungal skin infection) codes are accepted."""
        record = SCINRecord(**self._valid_record(icd_code="B35.0"))
        assert record.icd_code == "B35.0"

    def test_invalid_severity(self):
        """Invalid severity values are rejected."""
        with pytest.raises(ValueError, match="severity must be one of"):
            SCINRecord(**self._valid_record(severity="extreme"))

    def test_severity_normalized_to_lowercase(self):
        """Severity values are normalized to lowercase."""
        r = SCINRecord(**self._valid_record(severity="Moderate"))
        assert r.severity == "moderate"

    def test_empty_record_id_rejected(self):
        """Empty record_id is rejected."""
        with pytest.raises(ValueError):
            SCINRecord(**self._valid_record(record_id=""))

    def test_optional_fields_default_to_empty(self):
        """Optional fields have sensible defaults."""
        r = SCINRecord(**self._valid_record())
        assert r.body_location == ""
        assert r.age_group == ""
        assert r.tags == []

    def test_all_fitzpatrick_types(self):
        """All six Fitzpatrick types are valid."""
        for ft in FitzpatrickType:
            r = SCINRecord(**self._valid_record(fitzpatrick_type=ft))
            assert r.fitzpatrick_type == ft


class TestSCINDatasetStats:
    """Test dataset statistics model."""

    def test_empty_stats(self):
        """Empty stats have zero counts."""
        stats = SCINDatasetStats()
        assert stats.total_records == 0
        assert stats.image_count == 0
        assert stats.records_per_diagnosis == {}

    def test_stats_with_data(self):
        """Stats can be populated."""
        stats = SCINDatasetStats(
            total_records=100,
            records_per_diagnosis={"Psoriasis": 50, "Eczema": 50},
            records_per_fitzpatrick={"I": 20, "II": 20, "III": 20, "IV": 20, "V": 20},
            image_count=100,
        )
        assert stats.total_records == 100
        assert len(stats.records_per_diagnosis) == 2
