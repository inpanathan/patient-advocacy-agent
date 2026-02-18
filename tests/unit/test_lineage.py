"""Tests for data lineage tracking."""

from __future__ import annotations

from pathlib import Path

from src.data.lineage import DataLineage


class TestDataLineage:
    """Test data lineage chain."""

    def test_create_lineage(self):
        """Create a new lineage instance."""
        lineage = DataLineage(artifact_id="scin-v1")
        assert lineage.artifact_id == "scin-v1"
        assert len(lineage.steps) == 0

    def test_add_step(self):
        """Add a transformation step."""
        lineage = DataLineage(artifact_id="scin-v1")
        lineage.add_step(
            step_name="raw_ingestion",
            input_source="data/raw/scin",
            output_target="data/processed/scin",
            record_count=1000,
        )
        assert len(lineage.steps) == 1
        assert lineage.steps[0].step_name == "raw_ingestion"
        assert lineage.steps[0].record_count == 1000

    def test_save_and_load(self, tmp_path: Path):
        """Lineage can be saved and loaded from JSON."""
        lineage = DataLineage(artifact_id="scin-v1")
        lineage.add_step(
            step_name="validation",
            input_source="raw",
            output_target="validated",
            record_count=500,
        )

        path = tmp_path / "lineage.json"
        lineage.save(path)
        assert path.exists()

        loaded = DataLineage.load(path)
        assert loaded.artifact_id == "scin-v1"
        assert len(loaded.steps) == 1
        assert loaded.steps[0].step_name == "validation"

    def test_multiple_steps(self):
        """Multiple steps form a chain."""
        lineage = DataLineage(artifact_id="pipeline-run-42")
        lineage.add_step("ingest", "raw", "staged", record_count=1000)
        lineage.add_step("validate", "staged", "validated", record_count=950)
        lineage.add_step("embed", "validated", "embeddings", record_count=950)

        assert len(lineage.steps) == 3
        assert lineage.steps[-1].step_name == "embed"
