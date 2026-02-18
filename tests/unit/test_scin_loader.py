"""Tests for SCIN data loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.data.scin_loader import SCINLoader
from src.utils.errors import AppError, ErrorCode


@pytest.fixture
def sample_scin_dir(tmp_path: Path) -> Path:
    """Create a temporary SCIN data directory with sample data."""
    data_dir = tmp_path / "scin"
    data_dir.mkdir()

    sample_data = {
        "records": [
            {
                "record_id": "SCIN-001",
                "image_path": "images/001.jpg",
                "diagnosis": "Atopic Dermatitis",
                "icd_code": "L20.0",
                "fitzpatrick_type": "III",
                "body_location": "forearm",
                "age_group": "adult",
                "severity": "moderate",
                "description": "Chronic eczematous lesion",
                "tags": ["eczema"],
            },
            {
                "record_id": "SCIN-002",
                "image_path": "images/002.jpg",
                "diagnosis": "Psoriasis",
                "icd_code": "L40.0",
                "fitzpatrick_type": "II",
                "severity": "mild",
            },
            {
                "record_id": "SCIN-003",
                "image_path": "images/003.jpg",
                "diagnosis": "Atopic Dermatitis",
                "icd_code": "L20.0",
                "fitzpatrick_type": "V",
                "severity": "severe",
            },
        ]
    }

    (data_dir / "metadata.json").write_text(json.dumps(sample_data))
    return data_dir


class TestSCINLoader:
    """Test SCIN data loading and validation."""

    def test_load_valid_data(self, sample_scin_dir: Path):
        """Loader parses valid SCIN records."""
        loader = SCINLoader(sample_scin_dir)
        records = loader.load()
        assert len(records) == 3
        assert records[0].record_id == "SCIN-001"
        assert records[1].diagnosis == "Psoriasis"

    def test_load_missing_directory(self, tmp_path: Path):
        """Loader raises error for missing directory."""
        loader = SCINLoader(tmp_path / "nonexistent")
        with pytest.raises(AppError) as exc_info:
            loader.load()
        assert exc_info.value.code == ErrorCode.DATA_LOAD_FAILED

    def test_load_missing_metadata(self, tmp_path: Path):
        """Loader raises error when metadata.json is missing."""
        data_dir = tmp_path / "scin_empty"
        data_dir.mkdir()
        loader = SCINLoader(data_dir)
        with pytest.raises(AppError) as exc_info:
            loader.load()
        assert exc_info.value.code == ErrorCode.DATA_LOAD_FAILED

    def test_load_with_invalid_records(self, tmp_path: Path):
        """Loader skips invalid records and reports errors."""
        data_dir = tmp_path / "scin_mixed"
        data_dir.mkdir()
        data = {
            "records": [
                {
                    "record_id": "SCIN-001",
                    "image_path": "images/001.jpg",
                    "diagnosis": "Eczema",
                    "icd_code": "L20.0",
                    "fitzpatrick_type": "III",
                    "severity": "mild",
                },
                {
                    "record_id": "SCIN-BAD",
                    "image_path": "",
                    "diagnosis": "",
                    "icd_code": "INVALID",
                    "fitzpatrick_type": "X",
                    "severity": "extreme",
                },
            ]
        }
        (data_dir / "metadata.json").write_text(json.dumps(data))

        loader = SCINLoader(data_dir)
        records = loader.load()
        assert len(records) == 1
        assert len(loader.validation_errors) == 1

    def test_compute_stats(self, sample_scin_dir: Path):
        """Stats computation produces correct counts."""
        loader = SCINLoader(sample_scin_dir)
        records = loader.load()
        stats = loader.compute_stats(records)

        assert stats.total_records == 3
        assert stats.records_per_diagnosis["Atopic Dermatitis"] == 2
        assert stats.records_per_diagnosis["Psoriasis"] == 1
        assert stats.image_count == 3
        assert len(stats.records_per_fitzpatrick) == 3
